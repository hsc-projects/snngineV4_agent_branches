#!/usr/bin/env python3
"""Phase 1 of the Pi smoke test: flash the SD card with a customized image.

Scope per task.md: hostname pi-host, account htm (key-only, no password),
Wi-Fi (SSID/country prompted at runtime, never hardcoded — see below),
task-local SSH keypair (not ~/.ssh).

custom.toml / cmdline.txt mechanism verified against RPi-Distro/
raspberrypi-sys-mods' actual firstboot and init_config source (not guessed):
https://github.com/RPi-Distro/raspberrypi-sys-mods

Run this yourself, not through the assistant's Bash tool: it needs an
interactive sudo password (for dd + mount), a Wi-Fi password prompt, and a
real terminal.

Linux-only (dd, lsblk, udisksctl, xzcat, sudo) — this repo's own
host-machine-portability principle (setups/README.md) flags this as a
known limitation, not yet addressed: won't run on the maintainer's
Windows laptop if that's ever the machine in hand instead.
"""

import argparse
import getpass
import shlex
import subprocess
import sys
import time
from pathlib import Path

TASK_DIR = Path(__file__).parent
# Lives beside this script, not a session-specific temp path — otherwise
# this script only works on the one machine/session that downloaded the
# image, and re-downloading ~540MB isn't something to depend on being
# possible (e.g. away from home on a limited mobile hotspot). Gitignored
# (.gitignore: setups/pi-smoke-test/*.img.xz) — never committed.
DEFAULT_IMAGE_XZ = TASK_DIR / "raspios_lite_arm64_latest.img.xz"
KEY_PATH = TASK_DIR / "pi_smoke_test_key"
HOSTNAME = "pi-host"
USERNAME = "htm"

# No SSID default: it would identify the maintainer's device in this
# committed script (privacy — never bake personal/location-identifying
# details into version control, same standing rule as never hardcoding a
# password). Always prompted, no default shown.
# Country: a generic starting default only, always confirmed/overridable
# at runtime — not meant to imply anything about where this actually runs.
DEFAULT_WLAN_COUNTRY = "US"

SIZE_MIN_BYTES = 100 * 1024**3
SIZE_MAX_BYTES = 140 * 1024**3


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kw)


def find_sd_card() -> str:
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


def print_device_info(device: str) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default=None,
        help="Skip auto-detection and use this device instead (e.g. /dev/sdX). "
             "Only needed if auto-detection found zero or more than one "
             "candidate. You're still asked to confirm it by typing it back.",
    )
    parser.add_argument(
        "--image", type=Path, default=DEFAULT_IMAGE_XZ,
        help=f"Path to the downloaded .img.xz (default: {DEFAULT_IMAGE_XZ}).",
    )
    args = parser.parse_args()
    image_xz = args.image

    if not image_xz.is_file():
        print(f"Missing downloaded image: {image_xz}", file=sys.stderr)
        return 1

    device = args.device or find_sd_card()
    print(f"{'Using explicitly given' if args.device else 'Detected'} SD card: {device}")
    print_device_info(device)
    confirm = input(f"Confirm target device [{device}], Enter to accept, or type a different path to abort: ")
    if confirm.strip() not in ("", device):
        print("Confirmation didn't match, aborting.", file=sys.stderr)
        return 1

    # Generate the task-local keypair if it doesn't exist yet.
    if not KEY_PATH.exists():
        run(["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(KEY_PATH),
             "-C", "pi-smoke-test (throwaway, not the Pi's real credential)"])
    pubkey = (TASK_DIR / f"{KEY_PATH.name}.pub").read_text().strip()

    # SSID/country always asked, never hardcoded or defaulted from a
    # specific past run — may be a different network/region each time,
    # and baking in a specific SSID or region would put personal/
    # location-identifying detail into this committed script. Password
    # is prompted too, never hardcoded, for the same reason (a plaintext
    # secret baked into source would land in version control). Asked up
    # front so you're not left waiting mid-flash.
    wlan_ssid = input("Wi-Fi SSID: ").strip()
    while not wlan_ssid:
        wlan_ssid = input("Wi-Fi SSID (required): ").strip()
    wlan_country = (
        input(f"Wi-Fi country/regulatory code, 2-letter [{DEFAULT_WLAN_COUNTRY}]: ").strip()
        or DEFAULT_WLAN_COUNTRY
    ).upper()
    wlan_password = getpass.getpass(
        f"Wi-Fi password for {wlan_ssid!r} (hidden, not stored anywhere): "
    )

    # Unmount any mounted partitions of the target device first.
    lsblk_parts = subprocess.run(
        ["lsblk", "-n", "-o", "NAME", device], text=True, capture_output=True,
    ).stdout.split()
    for part in lsblk_parts[1:]:
        subprocess.run(["udisksctl", "unmount", "-b", f"/dev/{part}"],
                        capture_output=True)

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
        print("dd failed.", file=sys.stderr)
        return 1

    run(["sync"])
    subprocess.run(["sudo", "partprobe", device])
    time.sleep(2)

    boot_part = f"{device}1"
    mount_point = Path("/mnt/pi_smoke_test_boot")
    subprocess.run(["sudo", "mkdir", "-p", str(mount_point)], check=True)
    run(["sudo", "mount", boot_part, str(mount_point)])

    try:
        cmdline_path = mount_point / "cmdline.txt"
        cmdline = cmdline_path.read_text().strip()
        marker = "init=/usr/lib/raspberrypi-sys-mods/firstboot"
        if marker not in cmdline:
            cmdline = f"{cmdline} {marker}"
        run(["sudo", "tee", str(cmdline_path)], input=(cmdline + "\n").encode())

        def toml_str(s: str) -> str:
            return s.replace("\\", "\\\\").replace('"', '\\"')

        custom_toml = f"""\
config_version = 1

[system]
hostname = "{HOSTNAME}"

[user]
name = "{USERNAME}"

[ssh]
enabled = true
password_authentication = false
authorized_keys = ["{pubkey}"]

[wlan]
ssid = "{toml_str(wlan_ssid)}"
password = "{toml_str(wlan_password)}"
password_encrypted = false
country = "{wlan_country}"
"""
        run(["sudo", "tee", str(mount_point / "custom.toml")],
            input=custom_toml.encode())
    finally:
        run(["sudo", "umount", str(mount_point)])
        subprocess.run(["sudo", "rmdir", str(mount_point)])

    subprocess.run(["udisksctl", "power-off", "-b", device], capture_output=True)

    print("\nDone. custom.toml + cmdline.txt written, card safely powered off.")
    print(f"Task-local SSH key: {KEY_PATH} / {KEY_PATH}.pub")
    print("Safe to physically move the card to the Pi now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
