#!/usr/bin/env python3
"""Phase 2 of the Pi smoke test: find the Pi on the LAN and SSH into it.

Run after the flashed card is in the Pi and the Pi has had a couple of
minutes to boot and join Wi-Fi (first boot applies custom.toml and reboots).

    python pi_smoke_test_ssh_check.py [--host HOST] [--key PATH] [--wait SECONDS]
                                      [--sweep]

Discovery, in order, stopping at the first hit (nothing needs installing):
  1. --host, if given (an address or name you already know).
  2. mDNS names: pi-host.local, then raspberrypi.local.
  3. The ARP/neighbour table, filtered to Raspberry Pi Foundation MAC prefixes.
  4. With --sweep: probe port 22 across this machine's /24, then re-read ARP.

Then SSH in with the task-local key and run harmless read-only commands
(hostname, uname, os-release, disk space) as evidence.

Rules kept: bounded runtime everywhere (a --wait cap, per-call timeouts,
stdin closed, ssh BatchMode so it can never wait on a prompt); never touches
~/.ssh (a task-local known_hosts file, and -F /dev/null so no user ssh config
is read); no credential is printed. Works on Windows and Linux; Windows
specifics (the key's ACL, `arp -a` output) are UNTESTED against a real Pi.
"""

import argparse
import concurrent.futures
import getpass
import ipaddress
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

TASK_DIR = Path(__file__).parent
DEFAULT_KEY = TASK_DIR.parent / ".secrets" / "id_ed25519"  # gitignored
KNOWN_HOSTS = TASK_DIR / "pi_smoke_test_known_hosts"  # task-local, not ~/.ssh
HOSTNAME = "pi-host"
USERNAME = "htm"
MDNS_NAMES = [f"{HOSTNAME}.local", "raspberrypi.local"]

# Raspberry Pi Foundation / Trading OUIs (Pi 4 uses dc:a6:32 and e4:5f:01;
# older boards b8:27:eb; newer boards d8:3a:dd, 2c:cf:67, 28:cd:c1).
PI_MAC_PREFIXES = ("b8:27:eb", "dc:a6:32", "e4:5f:01", "d8:3a:dd", "2c:cf:67", "28:cd:c1")

RESOLVE_TIMEOUT = 5
SSH_CONNECT_TIMEOUT = 10
SSH_RUN_TIMEOUT = 40
RETRY_INTERVAL = 5

REMOTE_COMMAND = (
    'echo "hostname: $(hostname)"; '
    'echo "kernel:   $(uname -a)"; '
    '. /etc/os-release && echo "os:       $PRETTY_NAME"; '
    'echo "disk (/): $(df -h / | tail -1)"'
)


def log(msg: str) -> None:
    print(msg, flush=True)


# --- discovery -----------------------------------------------------------

def resolve(name: str) -> str | None:
    """getaddrinfo has no timeout of its own, so run it in a thread."""
    result: list[str] = []

    def work():
        # AF_UNSPEC: a Pi cabled straight to this machine (no DHCP server)
        # may only be reachable on an IPv6 link-local address.
        try:
            infos = socket.getaddrinfo(name, 22, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except OSError:
            return
        infos.sort(key=lambda i: i[0] != socket.AF_INET)  # prefer IPv4
        sockaddr = infos[0][4]
        addr = sockaddr[0]
        if infos[0][0] == socket.AF_INET6 and "%" not in addr and sockaddr[3]:
            addr = f"{addr}%{sockaddr[3]}"  # ssh needs the scope id for fe80::
        result.append(addr)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(RESOLVE_TIMEOUT)
    return result[0] if result else None


def parse_neighbours(text: str) -> list[tuple[str, str]]:
    """(ip, mac) pairs from `arp -a` (Windows/mac), `arp -n` or `ip neigh` output."""
    pairs = []
    for line in text.splitlines():
        ip = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
        mac = re.search(r"\b([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\b", line)
        if ip and mac:
            pairs.append((ip.group(1), mac.group(1).lower().replace("-", ":")))
    return pairs


def read_neighbour_table() -> str:
    cmds = [["arp", "-a"]] if IS_WINDOWS else [["ip", "neigh"], ["arp", "-n"]]
    for cmd in cmds:
        try:
            res = subprocess.run(
                cmd, text=True, capture_output=True, timeout=15,
                stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
    return ""


def find_in_arp() -> list[str]:
    return [
        ip for ip, mac in parse_neighbours(read_neighbour_table())
        if mac.startswith(PI_MAC_PREFIXES)
    ]


def local_ipv4() -> str | None:
    """This machine's LAN address. A UDP connect sends no packet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # TEST-NET-1, never routed
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def sweep_port_22() -> None:
    """Touch every address in this /24 on port 22 so the ARP table fills."""
    me = local_ipv4()
    if not me:
        log("  sweep: could not determine this machine's LAN address, skipped")
        return
    net = ipaddress.ip_network(f"{me}/24", strict=False)  # assumes a /24
    log(f"  sweep: probing port 22 on {net} (about {RESOLVE_TIMEOUT}s)")

    def probe(ip):
        try:
            with socket.create_connection((str(ip), 22), timeout=1.0):
                pass
        except OSError:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        list(pool.map(probe, net.hosts()))


def discover(host: str | None, wait: int, sweep: bool) -> str | None:
    deadline = time.monotonic() + wait
    attempt = 0
    while True:
        attempt += 1
        log(f"[discovery attempt {attempt}]")
        if host:
            log(f"  using --host {host}")
            return host
        for name in MDNS_NAMES:
            ip = resolve(name)
            log(f"  {name}: {ip or 'no answer'}")
            if ip:
                return ip
        hits = find_in_arp()
        log(f"  ARP table, Pi MAC prefixes: {hits or 'none'}")
        if hits:
            if len(hits) > 1:
                log(f"  more than one Pi-vendor device ({hits}); taking the first, "
                    "pass --host to choose")
            return hits[0]
        if sweep:
            sweep_port_22()
            hits = find_in_arp()
            log(f"  ARP table after sweep: {hits or 'none'}")
            if hits:
                return hits[0]
        if time.monotonic() + RETRY_INTERVAL > deadline:
            return None
        time.sleep(RETRY_INTERVAL)


# --- ssh -----------------------------------------------------------------

def restrict_key_permissions(key: Path) -> None:
    """ssh refuses a private key other users can read. Windows needs icacls."""
    if IS_WINDOWS:
        user = getpass.getuser()
        subprocess.run(
            ["icacls", str(key), "/inheritance:r", "/grant:r", f"{user}:R"],
            check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30,
        )
        log(f"Restricted {key.name} to {user} (read) with icacls.")
    else:
        key.chmod(0o600)


def ssh_check(host: str, key: Path, wait: int) -> int:
    cmd = [
        "ssh",
        "-F", os.devnull,                       # read no user ssh config
        "-i", str(key), "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",                  # never prompt
        "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        f"{USERNAME}@{host}", REMOTE_COMMAND,
    ]
    deadline = time.monotonic() + wait
    attempt = 0
    denied = False
    while True:
        attempt += 1
        log(f"[ssh attempt {attempt}] {USERNAME}@{host}")
        try:
            res = subprocess.run(
                cmd, text=True, capture_output=True, timeout=SSH_RUN_TIMEOUT,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            res = None
            log("  timed out")
        if res is not None:
            if res.returncode == 0:
                print(res.stdout)
                if f"hostname: {HOSTNAME}" in res.stdout:
                    log(f"OK: landed on {HOSTNAME} as {USERNAME}, key-only login worked.")
                    return 0
                log(f"Connected, but the hostname is not {HOSTNAME!r}: wrong machine?")
                return 2
            reason = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else f"exit {res.returncode}"
            log(f"  failed: {reason}")
            if "Permission denied" in res.stderr:
                # Not final: sshd can be up (enabled by the boot-partition
                # `ssh` file) before cloud-init has installed the key, so keep
                # retrying until the time limit.
                denied = True
        if time.monotonic() + RETRY_INTERVAL > deadline:
            if denied:
                log(f"\nThe Pi answered on port 22 but rejected the key for the whole "
                    f"{wait}s: cloud-init may not have installed it, or the card was "
                    "configured with a different public key than --key's.")
                return 3
            return 1
        time.sleep(RETRY_INTERVAL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", help="skip discovery: an IP or name you already know")
    ap.add_argument("--key", type=Path, default=DEFAULT_KEY,
                    help="private key to use (default: setups/.secrets/id_ed25519)")
    ap.add_argument("--wait", type=int, default=180,
                    help="seconds to keep retrying discovery and SSH (default 180)")
    ap.add_argument("--sweep", action="store_true",
                    help="also probe port 22 across this machine's /24 to fill the ARP table")
    args = ap.parse_args()

    if not args.key.is_file():
        print(f"Key not found: {args.key}", file=sys.stderr)
        return 1
    try:
        restrict_key_permissions(args.key)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Could not restrict key permissions: {e}", file=sys.stderr)
        return 1

    host = discover(args.host, args.wait, args.sweep)
    if not host:
        log(f"\nNo Pi found within {args.wait}s. Check it is powered, on the same "
            "network as this machine, and has had a few minutes to boot; try --sweep, "
            "or pass --host with its address from your router's client list.")
        return 1
    log(f"\nFound candidate at {host}.\n")
    code = ssh_check(host, args.key, args.wait)
    if code == 1:
        log(f"\nSSH to {host} never succeeded within {args.wait}s "
            "(sshd may not be up yet, or this is not the Pi).")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
