#!/usr/bin/env python3
"""Laptop-side client for the Pi's keyholder (setups/pi-rationale.md, item 20).

    python setups/pi-provision/pi_keyholder.py --host ADDRESS add NAME [--consumer USER]
    python setups/pi-provision/pi_keyholder.py --host ADDRESS unlock
    python setups/pi-provision/pi_keyholder.py --host ADDRESS lock
    python setups/pi-provision/pi_keyholder.py --host ADDRESS status
    ... unlock --as-pikeys --key PATH     # the forced-command key, as a phone does it

`add` encrypts a secret onto the Pi's credential stick (the Pi does the encrypting,
so the laptop needs no gpg). `unlock` decrypts every listed secret into the Pi's RAM
(/run/pi-secrets); `lock` wipes them; `status` lists names only. By default the calls
go over SSH as the admin user (`htm`, the project key, sudo). With --as-pikeys they go
as the `pikeys` user with its own key: that user can run nothing but the unlock helper,
which is the path a phone or any other device uses.

The passphrase and the secret value are read with hidden prompts, sent to the Pi on
SSH's stdin, and never put in an argument, a file or the output. Only names, sizes and
the Pi's own status lines are printed. ADDRESS is the Pi's LAN or tailnet address.
"""

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parents[1] / ".secrets"
KNOWN_HOSTS = Path(__file__).resolve().parents[1] / "pi-smoke-test" / "pi_smoke_test_known_hosts"
ADMIN_USER = "htm"
KEYHOLDER_USER = "pikeys"
UNLOCK = "/usr/local/sbin/pi-unlock"
ADD = "/usr/local/sbin/pi-secret-add"


def ssh(host: str, user: str, key: Path, remote: str | None, stdin: str) -> int:
    cmd = [
        "ssh", "-F", os.devnull,
        "-i", str(key), "-o", "IdentitiesOnly=yes",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        f"{user}@{host}",
    ]
    if remote:
        cmd.append(remote)
    # Bytes, not text mode: on Windows text mode turns every "\n" into "\r\n", and the
    # Pi's helpers read their lines with plain `read -r`, which would keep the "\r"
    # (a passphrase or a secret value ending in it, a verb "unlock\r" they do not know).
    try:
        r = subprocess.run(cmd, input=stdin.encode("utf-8"), capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        print("The Pi did not answer in time.", file=sys.stderr)
        return 1
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    if out.strip():
        print(out.rstrip())
    if r.returncode != 0 and err.strip():
        print(err.rstrip(), file=sys.stderr)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", required=True, help="the Pi's address (LAN or tailnet)")
    ap.add_argument("--key", help="private key (default: setups/.secrets/id_ed25519)")
    ap.add_argument("--as-pikeys", action="store_true",
                    help="connect as the forced-command user instead of the admin (needs --key)")
    sub = ap.add_subparsers(dest="verb", required=True)
    add = sub.add_parser("add", help="encrypt a secret onto the stick")
    add.add_argument("name", help="a-z, 0-9 and _ (at most 40)")
    add.add_argument("--consumer", default="root", help="the user that will read it (default root)")
    for v in ("unlock", "lock", "status"):
        sub.add_parser(v)
    args = ap.parse_args()

    if args.as_pikeys and not args.key:
        print("--as-pikeys needs --key (the key authorised in unlock/authorized_keys).", file=sys.stderr)
        return 2
    if args.verb == "add" and args.as_pikeys:
        print("`add` is admin-only; run it without --as-pikeys.", file=sys.stderr)
        return 2
    key = Path(args.key) if args.key else SECRETS / "id_ed25519"
    if not key.is_file():
        print(f"Missing key {key}", file=sys.stderr)
        return 1

    if args.verb == "add":
        pw = getpass.getpass("Passphrase for the store (hidden): ")
        if pw != getpass.getpass("Repeat the passphrase: "):
            print("The passphrases differ; nothing sent.", file=sys.stderr)
            return 2
        value = getpass.getpass(f"Value of {args.name} (hidden, one line): ")
        if not pw or not value or "\n" in value or "\r" in value:
            print("Empty passphrase or value, or the value has a line break; nothing sent.", file=sys.stderr)
            return 2
        return ssh(args.host, ADMIN_USER, key, f"sudo {ADD} {args.name} {args.consumer}", f"{pw}\n{value}\n")

    stdin = args.verb + "\n"
    if args.verb == "unlock":
        stdin += getpass.getpass("Passphrase (hidden): ") + "\n"
    if args.as_pikeys:
        # The forced command ignores any command given here; none is sent.
        return ssh(args.host, KEYHOLDER_USER, key, None, stdin)
    return ssh(args.host, ADMIN_USER, key, f"sudo {UNLOCK}", stdin)


if __name__ == "__main__":
    sys.exit(main())
