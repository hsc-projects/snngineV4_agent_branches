#!/usr/bin/env python3
"""Phase 1 of the Pi smoke test: flash the SD card with a customized image.

Scope per task.md: hostname pi-host, account htm (key-only, no password),
Wi-Fi (from setups/.secrets/.env with --wifi-from-env, otherwise prompted at
runtime; never hardcoded), SSH public key from setups/.secrets/id_ed25519.pub
(gitignored, not ~/.ssh).

First-boot configuration is cloud-init (user-data, network-config, meta-data on
the boot partition); the older custom.toml mechanism is not read by this OS
release, and any leftover one is removed. The optional --provision-script is
carried in user-data (setups/pi-technical.md, "First-boot provisioning").

It wipes the card: check the card's exact size, and what is on it, first. It
needs elevated rights (an interactive sudo password on Linux, an Administrator
PowerShell on Windows). With --device, --confirm-device and --wifi-from-env it
asks nothing, so it can run from an elevated, non-interactive PowerShell with
its output logged (setups/pi-handoff.md, "Flash a card").

Platforms: Linux (dd, lsblk, udisksctl, xzcat, sudo) and Windows (built-in
PowerShell storage cmdlets, raw \\\\.\\PhysicalDriveN writes, Python's own
lzma module, so no extra tools beyond Python and the OpenSSH client that
ships with Windows 10+). The Windows path has been run repeatedly (2026-10-07
to 2026-10-11); the Linux path was not re-run after the cloud-init rework and
the Windows port.
"""

import argparse
import contextlib
import ctypes
import getpass
import json
import lzma
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

TASK_DIR = Path(__file__).parent
# Lives beside this script, not a session-specific temp path — otherwise
# this script only works on the one machine/session that downloaded the
# image, and re-downloading ~540MB isn't something to depend on being
# possible (e.g. away from home on a limited mobile hotspot). Gitignored
# (.gitignore: setups/pi-smoke-test/*.img.xz) — never committed.
DEFAULT_IMAGE_XZ = TASK_DIR / "raspios_lite_arm64_latest.img.xz"
# The maintainer's key, kept (gitignored) in setups/.secrets. Never generated
# here: a missing key is an error, so the card can't silently get a key nobody
# holds.
KEY_PATH = TASK_DIR.parent / ".secrets" / "id_ed25519"
WIFI_ENV_PATH = TASK_DIR.parent / ".secrets" / ".env"  # gitignored with the key
HOSTNAME = "pi-host"
USERNAME = "htm"

# No SSID default: it would identify the maintainer's device in this
# committed script (privacy — never bake personal/location-identifying
# details into version control, same standing rule as never hardcoding a
# password). Always prompted, no default shown.
# Country: a generic starting default only, always confirmed/overridable
# at runtime — not meant to imply anything about where this actually runs.
DEFAULT_WLAN_COUNTRY = "US"

# When Wi-Fi is configured, prefer it over the cable: the lowest default-route
# metric wins, and NetworkManager's own defaults are eth0 100 and wlan0 600
# (seen on the Pi). Set through netplan's dhcp4-overrides, documented for the
# NetworkManager renderer: https://netplan.readthedocs.io/en/stable/netplan-yaml/
WLAN_ROUTE_METRIC = 50

SIZE_MIN_BYTES = 100 * 1024**3
SIZE_MAX_BYTES = 140 * 1024**3

# Windows only: bus types an SD card can show up under (USB card reader,
# or a built-in slot reported as SD/MMC).
WIN_ALLOWED_BUS = {"USB", "SD", "MMC"}
WIN_WRITE_CHUNK = 4 * 1024**2
WIN_ALIGN = 4096  # raw-disk writes must be sector-aligned (512 or 4096)
WIN_HEAD_BYTES = 1024**2  # written last, see win_write_image
WIN_PS_TIMEOUT = 60  # seconds; every PowerShell call is bounded


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kw)


# --------------------------------------------------------------------------
# Windows backend
# --------------------------------------------------------------------------

def win_is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def win_ps(script: str, timeout: int = WIN_PS_TIMEOUT, check: bool = True) -> str:
    """Run a PowerShell snippet, return stdout. Stdin closed, runtime bounded."""
    res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        text=True, capture_output=True, timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    if check and res.returncode != 0:
        raise RuntimeError(
            f"PowerShell failed (exit {res.returncode}): {res.stderr.strip() or res.stdout.strip()}"
        )
    return res.stdout


def win_json(script: str, **kw):
    """Run a snippet that ends in ConvertTo-Json; always return a list."""
    out = win_ps(script, **kw).strip()
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def win_disk_number(device: str) -> int:
    """Accept '2', 'Disk 2', 'PhysicalDrive2' or '\\\\.\\PhysicalDrive2'."""
    m = re.search(r"(\d+)\s*$", device.strip())
    if not m:
        raise ValueError(f"Can't read a disk number out of {device!r}")
    return int(m.group(1))


def win_device_path(number: int) -> str:
    return rf"\\.\PhysicalDrive{number}"


def win_get_disks() -> list[dict]:
    rows = win_json(
        "Get-Disk | Select-Object Number,FriendlyName,SerialNumber,BusType,"
        "Size,IsSystem,IsBoot,PartitionStyle | ConvertTo-Json -Compress"
    )
    return [
        {
            "number": int(r["Number"]),
            "name": (r.get("FriendlyName") or "").strip(),
            "serial": (r.get("SerialNumber") or "").strip(),
            "bus": str(r.get("BusType") or ""),
            "size": int(r["Size"]),
            "is_system": bool(r.get("IsSystem")),
            "is_boot": bool(r.get("IsBoot")),
        }
        for r in rows
    ]


def win_get_disk(number: int) -> dict:
    for d in win_get_disks():
        if d["number"] == number:
            return d
    raise RuntimeError(f"Disk {number} not found (re-plugged? renumbered?)")


def win_check_safe_target(d: dict) -> None:
    """Hard refusals, re-checked right before anything destructive."""
    if d["is_system"] or d["is_boot"]:
        raise RuntimeError(f"Disk {d['number']} is a system/boot disk. Refusing.")
    if d["bus"].upper() not in WIN_ALLOWED_BUS:
        raise RuntimeError(
            f"Disk {d['number']} is on bus {d['bus']!r}, not USB/SD/MMC. Refusing."
        )
    if not (SIZE_MIN_BYTES <= d["size"] <= SIZE_MAX_BYTES):
        raise RuntimeError(
            f"Disk {d['number']} is {d['size'] / 1024**3:.1f} GiB, outside the "
            "expected SD-card size window. Refusing."
        )


def win_find_sd_card() -> str:
    candidates = []
    for d in win_get_disks():
        try:
            win_check_safe_target(d)
        except RuntimeError:
            continue
        candidates.append(d)
    paths = [win_device_path(d["number"]) for d in candidates]
    return _pick_single(paths)


def win_print_device_info(device: str) -> None:
    d = win_get_disk(win_disk_number(device))
    used_pct = "n/a"
    try:
        vols = win_json(
            f"Get-Partition -DiskNumber {d['number']} -ErrorAction SilentlyContinue | "
            "Get-Volume -ErrorAction SilentlyContinue | "
            "Select-Object Size,SizeRemaining | ConvertTo-Json -Compress",
            check=False,
        )
        for v in vols:
            if v.get("Size"):
                used_pct = f"{100 * (v['Size'] - v['SizeRemaining']) // v['Size']}%"
                break
    except Exception:
        pass
    size = f"{d['size'] / 1024**3:.1f}G"
    print(f"{'DEVICE':<24}{'SIZE':<9}{'USED%':<7}{'MODEL':<26}{'SERIAL':<26}BUS")
    print(f"{device:<24}{size:<9}{used_pct:<7}{d['name']:<26}{d['serial']:<26}{d['bus']}")


def win_prepare(device: str) -> None:
    """Drop the card's partition table so Windows holds no volume on it.

    A raw write to a physical drive fails with access denied while a mounted
    volume exists on it. The card is about to be overwritten anyway, and the
    caller has already asked for confirmation of this exact disk.
    """
    if not win_is_admin():
        raise RuntimeError(
            "Not running as Administrator. Open an elevated terminal "
            "(right-click > Run as administrator) and run this again."
        )
    n = win_disk_number(device)
    win_check_safe_target(win_get_disk(n))
    print(f"Clearing the partition table of disk {n}...")
    win_ps(
        f"Clear-Disk -Number {n} -RemoveData -RemoveOEM -Confirm:$false",
        timeout=120,
    )


def _read_full(src, n: int) -> bytes:
    """Read exactly n bytes unless EOF comes first."""
    parts, got = [], 0
    while got < n:
        b = src.read(n - got)
        if not b:
            break
        parts.append(b)
        got += len(b)
    return b"".join(parts)


def win_write_image(device: str, image_xz: Path) -> None:
    n = win_disk_number(device)
    win_check_safe_target(win_get_disk(n))  # same disk, still safe
    path = win_device_path(n)
    total, t_last = 0, time.monotonic()
    try:
        with lzma.open(image_xz, "rb") as src, open(path, "r+b", buffering=0) as dst:
            # Windows refuses writes through a physical-disk handle into the
            # sectors of any mounted volume unless that volume is locked
            # (https://learn.microsoft.com/previous-versions/windows/hardware/design/dn653576).
            # Writing the partition table first makes Windows mount the new
            # boot partition mid-write, and the next write fails with
            # "Bad file descriptor". So hold back the first 1 MiB (partition
            # table, MBR or GPT) and write it last: until then Windows sees
            # no volume to mount.
            head = b""
            while True:
                buf = _read_full(src, WIN_WRITE_CHUNK)
                if not buf:
                    break
                offset = total
                body = buf
                if offset == 0:
                    head, body, offset = buf[:WIN_HEAD_BYTES], buf[WIN_HEAD_BYTES:], WIN_HEAD_BYTES
                total += len(buf)
                if body:
                    if len(body) % WIN_ALIGN:  # only ever the final chunk
                        body += b"\0" * (-len(body) % WIN_ALIGN)
                    dst.seek(offset)
                    dst.write(body)
                if time.monotonic() - t_last >= 1.0:
                    print(f"\r  {total / 1024**2:,.0f} MiB written", end="", flush=True)
                    t_last = time.monotonic()
            if len(head) % WIN_ALIGN:
                head += b"\0" * (-len(head) % WIN_ALIGN)
            dst.seek(0)
            dst.write(head)  # the partition table, last
            dst.flush()
            try:
                os.fsync(dst.fileno())
            except OSError:
                pass
    except PermissionError as e:
        raise RuntimeError(
            f"Access denied opening {path}: needs an Administrator terminal, "
            f"and nothing (Explorer, an antivirus scan) may hold the disk. ({e})"
        )
    print(f"\r  {total / 1024**2:,.0f} MiB written, done.        ")


@contextlib.contextmanager
def win_boot_partition(device: str):
    """Yield the FAT32 boot partition's drive root; hand the letter back after."""
    n = win_disk_number(device)
    win_ps(f"Update-Disk -Number {n}", check=False)

    def letter() -> str | None:
        rows = win_json(
            f"Get-Partition -DiskNumber {n} -PartitionNumber 1 "
            "-ErrorAction SilentlyContinue | Select-Object DriveLetter | "
            "ConvertTo-Json -Compress",
            check=False,
        )
        for r in rows:
            dl = r.get("DriveLetter")
            # DriveLetter serializes as a char code (int) or a string.
            if isinstance(dl, int) and dl:
                return chr(dl)
            if isinstance(dl, str) and dl.strip("\0 "):
                return dl.strip("\0 ")
        return None

    drive = None
    assigned_by_us = False
    for attempt in range(20):  # bounded: ~20 s for Windows to see the new table
        drive = letter()
        if drive:
            break
        if attempt == 5:  # Windows didn't auto-mount; ask for a letter
            win_ps(
                f"Add-PartitionAccessPath -DiskNumber {n} -PartitionNumber 1 "
                "-AssignDriveLetter",
                check=False,
            )
            assigned_by_us = True
        time.sleep(1)
    if not drive:
        raise RuntimeError(
            "Windows never exposed the boot partition (partition 1) with a "
            "drive letter. Unplug and re-plug the card, then use "
            "Disk Management to check partition 1 is FAT32."
        )
    root = Path(f"{drive}:\\")
    if not (root / "cmdline.txt").is_file():
        raise RuntimeError(f"{root} has no cmdline.txt, so it's not the Pi boot partition.")
    print(
        f"Boot partition mounted at {root}. If Windows offers to format any "
        "disk, click Cancel — the Linux root partition is unreadable to it by design."
    )
    try:
        yield root
    finally:
        if assigned_by_us:
            win_ps(
                f"Remove-PartitionAccessPath -DiskNumber {n} -PartitionNumber 1 "
                f"-AccessPath '{drive}:\\'",
                check=False,
            )


def win_eject(device: str) -> None:
    n = win_disk_number(device)
    # Set offline flushes and detaches Windows' hold; the card is then safe to
    # pull. (Windows remembers the offline flag only for this card's signature
    # on this machine.)
    win_ps(f"Set-Disk -Number {n} -IsOffline $true", check=False)


# --------------------------------------------------------------------------
# Linux backend
# --------------------------------------------------------------------------

def linux_find_sd_card() -> str:
    out = subprocess.run(
        ["lsblk", "-b", "-n", "-o", "NAME,SIZE,TYPE,TRAN,RM,MOUNTPOINT"],
        check=True, text=True, capture_output=True,
    ).stdout
    candidates = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        name, size, dtype, tran, rm = parts[:5]
        if dtype != "disk" or tran != "usb" or rm != "1":
            continue
        size = int(size)
        if not (SIZE_MIN_BYTES <= size <= SIZE_MAX_BYTES):
            continue
        candidates.append(f"/dev/{name}")
    return _pick_single(candidates)


def linux_print_device_info(device: str) -> None:
    # -P (key="value" pairs) instead of plain columns: robust against
    # multi-word fields like MODEL ("Storage Device"), unlike a plain
    # whitespace .split() on lsblk's default table output.
    out = subprocess.run(
        ["lsblk", "-P", "-o", "NAME,SIZE,MODEL,SERIAL,TRAN,FSUSE%", device],
        text=True, capture_output=True,
    ).stdout
    rows = [{k: v for k, v in (kv.split("=", 1) for kv in shlex.split(line))}
            for line in out.splitlines() if line.strip()]

    bare_name = device.removeprefix("/dev/")
    disk = next(r for r in rows if r["NAME"] == bare_name)
    size, model, serial, tran = disk["SIZE"], disk["MODEL"], disk["SERIAL"], disk["TRAN"]
    used_pct = next(
        (r["FSUSE%"] for r in rows if r["NAME"] != bare_name and r.get("FSUSE%")),
        "n/a",
    )

    print(f"{'DEVICE':<10}{'SIZE':<9}{'USED%':<7}{'MODEL':<18}{'SERIAL':<16}BUS")
    print(f"{device:<10}{size:<9}{used_pct:<7}{model:<18}{serial:<16}{tran}")


def linux_prepare(device: str) -> None:
    # Unmount any mounted partitions of the target device first.
    lsblk_parts = subprocess.run(
        ["lsblk", "-n", "-o", "NAME", device], text=True, capture_output=True,
    ).stdout.split()
    for part in lsblk_parts[1:]:
        subprocess.run(["udisksctl", "unmount", "-b", f"/dev/{part}"],
                        capture_output=True)


def linux_write_image(device: str, image_xz: Path) -> None:
    # Write the image: decompress on the fly into dd, sudo prompts on the tty.
    print("Writing image (this needs your sudo password, and takes a while)...")
    xzcat = subprocess.Popen(["xzcat", str(image_xz)], stdout=subprocess.PIPE)
    dd = subprocess.Popen(
        ["sudo", "dd", f"of={device}", "bs=4M", "status=progress", "conv=fsync"],
        stdin=xzcat.stdout,
    )
    xzcat.stdout.close()
    dd.communicate()
    if dd.returncode != 0:
        raise RuntimeError("dd failed.")

    run(["sync"])
    subprocess.run(["sudo", "partprobe", device])
    time.sleep(2)


@contextlib.contextmanager
def linux_boot_partition(device: str):
    boot_part = f"{device}1"
    mount_point = Path("/mnt/pi_smoke_test_boot")
    subprocess.run(["sudo", "mkdir", "-p", str(mount_point)], check=True)
    run(["sudo", "mount", boot_part, str(mount_point)])
    try:
        yield mount_point
    finally:
        run(["sudo", "umount", str(mount_point)])
        subprocess.run(["sudo", "rmdir", str(mount_point)])


def linux_eject(device: str) -> None:
    subprocess.run(["udisksctl", "power-off", "-b", device], capture_output=True)


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------

def print_device_info(device: str) -> None:
    (win_print_device_info if IS_WINDOWS else linux_print_device_info)(device)


def _pick_single(candidates: list[str]) -> str:
    if len(candidates) == 1:
        return candidates[0]

    if not candidates:
        print(
            "No matching USB/removable ~120G disk found. Is the card reader "
            "plugged in? Refusing to guess — aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Found {len(candidates)} matching USB/removable ~120G disks, not "
        f"just one. Refusing to guess — pick the right one below.",
        file=sys.stderr,
    )
    for i, c in enumerate(candidates):
        print(f"\n[{i}]", end="")
        print_device_info(c)
    while True:
        choice = input(
            f"\nWhich one is the SD card? Type its number (0-{len(candidates) - 1}) "
            "or 'abort': "
        ).strip()
        if choice == "abort":
            sys.exit(1)
        if choice.isdigit() and 0 <= int(choice) < len(candidates):
            return candidates[int(choice)]
        print("Not a valid choice, try again.")


def write_boot_file(mount: Path, name: str, data: bytes) -> None:
    target = mount / name
    if IS_WINDOWS:
        target.write_bytes(data)
    else:
        run(["sudo", "tee", str(target)], input=data)


def load_env_file(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE reader (comments, optional quotes). Values stay private."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        values[key.strip()] = val
    return values


def delete_boot_file(mount: Path, name: str) -> None:
    target = mount / name
    if not target.exists():
        return
    if IS_WINDOWS:
        target.unlink()
    else:
        run(["sudo", "rm", str(target)])


def yaml_str(s: str) -> str:
    return json.dumps(s)  # a JSON string is a valid double-quoted YAML scalar


PROVISION_PATH_ON_PI = "/usr/local/sbin/pi-provision-firstboot.sh"
PROVISION_UNIT_PATH_ON_PI = "/etc/systemd/system/pi-provision.service"
PROVISION_MARKER_ON_PI = "/var/lib/pi-provision.done"
# Type=simple, not oneshot: a oneshot unit in multi-user.target would hold boot
# until the script ends. Restart=on-failure with a start limit retries a failed
# run every 5 minutes (6 starts per hour at most), and each later boot tries
# again until the script has written its marker file.
PROVISION_UNIT = f"""[Unit]
Description=Pi first-boot provisioning (retried until it succeeds)
ConditionPathExists=!{PROVISION_MARKER_ON_PI}
StartLimitIntervalSec=3600
StartLimitBurst=6

[Service]
Type=simple
ExecStart={PROVISION_PATH_ON_PI}
Restart=on-failure
RestartSec=300

[Install]
WantedBy=multi-user.target
"""


def build_user_data(
    pubkey: str, enable_ssh: bool = True, provision: str | None = None,
) -> str:
    # Raspberry Pi OS Trixie configures first boot with cloud-init, not the
    # older custom.toml/firstrun.sh. Syntax from the official example:
    # https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/
    # enable_ssh=False exists only to test whether the line is needed.
    # provision: text of a shell script to run on first boot. It is written
    # with write_files and run by a systemd unit (see PROVISION_UNIT) that
    # retries it until it succeeds, so a slow or failing install cannot hold up
    # cloud-init or boot.
    text = f"""#cloud-config

hostname: {HOSTNAME}
manage_etc_hosts: true

users:
  - name: {USERNAME}
    groups: users,adm,dialout,audio,netdev,video,plugdev,cdrom,games,input,gpio,spi,i2c,render,sudo
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - {pubkey}
    sudo: ALL=(ALL) NOPASSWD:ALL

ssh_pwauth: false
"""
    if enable_ssh:
        text += "enable_ssh: true\n"
    if provision:
        if "\t" in provision:
            raise ValueError("provision script contains a tab; YAML block text needs spaces")
        body = "\n".join(
            ("      " + line) if line.strip() else "" for line in provision.splitlines()
        )
        unit_body = "\n".join(
            ("      " + line) if line.strip() else "" for line in PROVISION_UNIT.splitlines()
        )
        text += (
            "\nwrite_files:\n"
            f"  - path: {PROVISION_PATH_ON_PI}\n"
            "    owner: root:root\n"
            "    permissions: '0755'\n"
            "    content: |\n"
            f"{body}\n"
            f"  - path: {PROVISION_UNIT_PATH_ON_PI}\n"
            "    owner: root:root\n"
            "    permissions: '0644'\n"
            "    content: |\n"
            f"{unit_body}\n"
            "\nruncmd:\n"
            "  - [systemctl, daemon-reload]\n"
            "  - [systemctl, enable, pi-provision.service]\n"
            "  - [systemctl, start, --no-block, pi-provision.service]\n"
        )
    return text


def build_network_config(ssid: str, country: str, password: str) -> str:
    # Plain DHCP on eth0. A Pi cabled straight to a laptop needs something to
    # answer DHCP, or NetworkManager fails the activation every 45 s and
    # eventually leaves eth0 down (measured). Windows Internet Connection
    # Sharing on the laptop's Ethernet adapter provides that. Netplan's
    # `link-local: [ipv4, ipv6]` was tried and does not change the generated
    # NetworkManager profile, so it is deliberately not used.
    cfg = """network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      optional: true
"""
    if ssid:
        cfg += f"""  wifis:
    renderer: NetworkManager
    wlan0:
      dhcp4: true
      dhcp4-overrides:
        route-metric: {WLAN_ROUTE_METRIC}
      optional: true
      regulatory-domain: {yaml_str(country)}
      access-points:
        {yaml_str(ssid)}:
          password: {yaml_str(password)}
"""
    return cfg


def write_cloud_init(
    mount: Path, pubkey: str, ssid: str, country: str, password: str,
    new_instance_id: str | None = None,
    ssh_file: bool = True, enable_ssh: bool = True,
    provision: str | None = None,
) -> None:
    """Write the cloud-init files into a Pi OS boot partition.

    new_instance_id: only for a card that has already booted once. cloud-init
    skips its per-instance setup when the instance id is unchanged, so an
    already-booted card needs a new id to pick up edited files.
    ssh_file / enable_ssh: both default on (the known-working config);
    turning one off is for testing whether that setting is needed.
    On an already-booted card such a test is unreliable (sshd stays enabled
    once started), so run it on a fresh flash.
    """
    # Drop the legacy first-boot hook and its config, if present: the old
    # init= parameter and custom.toml (which may hold a Wi-Fi password).
    cmdline = (mount / "cmdline.txt").read_text().strip()
    kept = [t for t in cmdline.split()
            if not t.startswith("init=/usr/lib/raspberrypi-sys-mods/firstboot")]
    write_boot_file(mount, "cmdline.txt", (" ".join(kept) + "\n").encode())
    delete_boot_file(mount, "custom.toml")

    # An empty file named "ssh" is the documented headless switch: the Pi
    # enables sshd at boot and deletes it. Belt and braces next to
    # enable_ssh in user-data, which on its own did not start sshd here.
    if ssh_file:
        write_boot_file(mount, "ssh", b"")
    else:
        delete_boot_file(mount, "ssh")
    write_boot_file(mount, "user-data",
                    build_user_data(pubkey, enable_ssh=enable_ssh,
                                    provision=provision).encode())
    write_boot_file(mount, "network-config",
                    build_network_config(ssid, country, password).encode())
    if new_instance_id:
        meta = (mount / "meta-data").read_text()
        meta = re.sub(r"(?m)^instance_id:.*$", f"instance_id: {new_instance_id}", meta)
        write_boot_file(mount, "meta-data", meta.encode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default=None,
        help="Skip auto-detection and use this device instead (Linux: /dev/sdX; "
             "Windows: a disk number such as 2, or \\\\.\\PhysicalDrive2). "
             "Only needed if auto-detection found zero or more than one "
             "candidate. You're still asked to confirm it by typing it back.",
    )
    parser.add_argument(
        "--image", type=Path, default=DEFAULT_IMAGE_XZ,
        help=f"Path to the downloaded .img.xz (default: {DEFAULT_IMAGE_XZ}).",
    )
    for flag, what in (
        ("--no-ssh-file", "the empty `ssh` file"),
        ("--no-enable-ssh", "`enable_ssh: true` in user-data"),
    ):
        parser.add_argument(
            flag, action="store_true",
            help=f"Experiment only: leave out {what}, to test whether it is needed.",
        )
    parser.add_argument(
        "--confirm-device", default=None,
        help="Non-interactive confirmation: the exact device path shown in the "
             "identity table (e.g. \\\\.\\PhysicalDrive3). Must equal the target "
             "device exactly, or the script aborts; an empty value is not accepted.",
    )
    parser.add_argument(
        "--no-wifi", action="store_true",
        help="Answer the Wi-Fi question with 'n' (Ethernet only) without asking.",
    )
    parser.add_argument(
        "--wifi-from-env", action="store_true",
        help="Configure Wi-Fi from HOTSPOT_NAME and HOTSPOT_PASSWORD (optional "
             "HOTSPOT_COUNTRY, default US) in setups/.secrets/.env, without asking. "
             "The password still ends up in plain text in network-config on the card.",
    )
    parser.add_argument(
        "--provision-script", type=Path, default=None,
        help="A shell script to run in the background from the Pi's first "
             "boot (installed through cloud-init write_files and run by a "
             "retrying systemd unit until it exits 0 and writes its own marker "
             "file; its log is /var/log/pi-provision.log if it logs there). Must not contain secrets: it ends up in plain text on the card.",
    )
    parser.add_argument(
        "--boot-dir", type=Path, default=None,
        help="Don't flash: write the cloud-init files into this already-flashed "
             "card's boot partition (e.g. F:\\) and exit. Ethernet only unless "
             "--wifi-from-env is also given. Gives the card a new cloud-init "
             "instance id so a card that has booted once re-applies it.",
    )
    args = parser.parse_args()
    image_xz = args.image

    pub_path = KEY_PATH.with_name(f"{KEY_PATH.name}.pub")
    if not pub_path.is_file():
        print(f"Missing public key: {pub_path}", file=sys.stderr)
        return 1

    provision_text = None
    if args.provision_script:
        if not args.provision_script.is_file():
            print(f"Missing provision script: {args.provision_script}", file=sys.stderr)
            return 1
        provision_text = args.provision_script.read_text(encoding="utf-8").replace("\r\n", "\n")
        print(f"Provision script: {args.provision_script.name} "
              f"({len(provision_text.splitlines())} lines), retried by a systemd unit until it succeeds.")

    if args.boot_dir:
        boot = args.boot_dir
        if not (boot / "cmdline.txt").is_file() or not (boot / "meta-data").is_file():
            print(f"{boot} doesn't look like a Pi OS boot partition "
                  "(needs cmdline.txt and meta-data).", file=sys.stderr)
            return 1
        b_ssid = b_country = b_password = ""
        if args.wifi_from_env:
            env = load_env_file(WIFI_ENV_PATH)
            missing = [k for k in ("HOTSPOT_NAME", "HOTSPOT_PASSWORD") if not env.get(k)]
            if missing:
                print(f"{WIFI_ENV_PATH} lacks {', '.join(missing)}.", file=sys.stderr)
                return 1
            b_ssid, b_password = env["HOTSPOT_NAME"], env["HOTSPOT_PASSWORD"]
            b_country = (env.get("HOTSPOT_COUNTRY") or DEFAULT_WLAN_COUNTRY).upper()
            print(f"Wi-Fi settings loaded from {WIFI_ENV_PATH} (values not shown); "
                  f"regulatory code {b_country}.")
        write_cloud_init(boot, pub_path.read_text().strip(), b_ssid, b_country, b_password,
                         new_instance_id=f"{HOSTNAME}-{int(time.time())}",
                         ssh_file=not args.no_ssh_file,
                         enable_ssh=not args.no_enable_ssh,
                         provision=provision_text)
        print(f"cloud-init files written to {boot} (user-data, network-config, "
              "meta-data instance id), legacy custom.toml and init= removed.")
        return 0

    if not image_xz.is_file():
        print(f"Missing downloaded image: {image_xz}", file=sys.stderr)
        return 1

    if args.device:
        device = win_device_path(win_disk_number(args.device)) if IS_WINDOWS else args.device
    else:
        device = win_find_sd_card() if IS_WINDOWS else linux_find_sd_card()
    print(f"{'Using explicitly given' if args.device else 'Detected'} SD card: {device}")
    print_device_info(device)
    if args.confirm_device is not None:
        # Non-interactive: only an exact match of the device path counts.
        if args.confirm_device.strip().lower() != device.lower():
            print(f"--confirm-device {args.confirm_device!r} doesn't match the "
                  f"target {device!r}, aborting.", file=sys.stderr)
            return 1
        print(f"Target confirmed by --confirm-device: {device}")
    else:
        confirm = input(
            f"Confirm target device [{device}]: Enter, 'y' or the device path "
            "accepts; anything else aborts: "
        )
        if confirm.strip().lower() not in ("", "y", "yes", device.lower()):
            print("Confirmation didn't match, aborting.", file=sys.stderr)
            return 1

    pubkey = pub_path.read_text().strip()

    # SSID/country always asked, never hardcoded or defaulted from a
    # specific past run — may be a different network/region each time,
    # and baking in a specific SSID or region would put personal/
    # location-identifying detail into this committed script. Password
    # is prompted too, never hardcoded, for the same reason (a plaintext
    # secret baked into source would land in version control). Asked up
    # front so you're not left waiting mid-flash.
    # Wi-Fi is optional, decided by an explicit y/n answer (no default, so a
    # bare Enter can't silently pick one).
    wlan_ssid = wlan_country = wlan_password = ""
    if args.wifi_from_env:
        # Non-interactive: the values come from the gitignored env file and are
        # never printed.
        env = load_env_file(WIFI_ENV_PATH)
        missing = [k for k in ("HOTSPOT_NAME", "HOTSPOT_PASSWORD") if not env.get(k)]
        if missing:
            print(f"{WIFI_ENV_PATH} lacks {', '.join(missing)}.", file=sys.stderr)
            return 1
        wlan_ssid = env["HOTSPOT_NAME"]
        wlan_password = env["HOTSPOT_PASSWORD"]
        wlan_country = (env.get("HOTSPOT_COUNTRY") or DEFAULT_WLAN_COUNTRY).upper()
        use_wlan = "env"
        print(f"Wi-Fi settings loaded from {WIFI_ENV_PATH} (values not shown); "
              f"regulatory code {wlan_country}.")
    else:
        use_wlan = "n" if args.no_wifi else ""
    while use_wlan not in ("y", "n", "env"):
        use_wlan = input("Configure Wi-Fi on this card? Type y or n: ").strip().lower()
    if use_wlan == "y":
        wlan_ssid = input("Wi-Fi SSID: ").strip()
        while not wlan_ssid:
            wlan_ssid = input("Wi-Fi SSID (required): ").strip()
        wlan_country = (
            input(f"Wi-Fi country/regulatory code, 2-letter [{DEFAULT_WLAN_COUNTRY}]: ").strip()
            or DEFAULT_WLAN_COUNTRY
        ).upper()
        wlan_password = getpass.getpass(
            f"Wi-Fi password for {wlan_ssid!r} (hidden; not saved by this script, "
            "but written in plain text to network-config on the card for the Pi's first boot): "
        )

    try:
        if IS_WINDOWS:
            win_prepare(device)
            win_write_image(device, image_xz)
            boot_partition = win_boot_partition
        else:
            linux_prepare(device)
            linux_write_image(device, image_xz)
            boot_partition = linux_boot_partition

        with boot_partition(device) as mount_point:
            write_cloud_init(mount_point, pubkey, wlan_ssid, wlan_country, wlan_password,
                             ssh_file=not args.no_ssh_file,
                             enable_ssh=not args.no_enable_ssh,
                             provision=provision_text)
    except (RuntimeError, subprocess.SubprocessError, OSError) as e:
        print(f"\nFailed: {e}", file=sys.stderr)
        return 1

    (win_eject if IS_WINDOWS else linux_eject)(device)

    print("\nDone. cloud-init user-data + network-config written, card ejected.")
    print(f"Authorized SSH key baked in: {pub_path}")
    print("Phase 2 (pi_smoke_test_ssh_check.py) uses the matching private key "
          "and fixes its permissions on Windows.")
    print("Safe to physically move the card to the Pi now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
