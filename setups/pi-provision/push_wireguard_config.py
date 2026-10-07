"""Install the Proton WireGuard config on the Pi, root-only, over SSH.

Run this once after flashing a fresh card (the first-boot script installs
wireguard-tools but deliberately carries no VPN config: the card's boot
partition is readable by anyone who holds the card). The config is read from
setups/.secrets/ (gitignored), the `DNS` line is dropped (the Pi has no
resolvconf, and wg-quick fails on a DNS line without it), and the file is
written to /etc/wireguard/ with mode 600, owner root. The tunnel is NOT
brought up and nothing is enabled at boot. Only names, sizes and the mode are
printed, never a key.

    python setups/pi-provision/push_wireguard_config.py --host 192.168.137.215
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parents[1] / ".secrets"
KNOWN_HOSTS = Path(__file__).resolve().parents[1] / "pi-smoke-test" / "pi_smoke_test_known_hosts"
USER = "htm"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", required=True, help="the Pi's address, e.g. 192.168.137.x")
    ap.add_argument("--config", default="wg-JP-154.conf",
                    help="file name inside setups/.secrets/ (also the name on the Pi)")
    args = ap.parse_args()

    src = SECRETS / args.config
    if not src.is_file():
        print(f"Missing {src}", file=sys.stderr)
        return 1
    lines = src.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    kept = [ln for ln in lines if not ln.strip().lower().startswith("dns")]
    body = "\n".join(kept) + "\n"
    dest = f"/etc/wireguard/{args.config}"

    remote = (
        "set -e; umask 077; sudo install -d -m 700 /etc/wireguard; "
        f"sudo tee {dest} > /dev/null; "
        f"sudo chown root:root {dest}; sudo chmod 600 {dest}; "
        f"sudo stat -c '%n %s bytes mode %a owner %U' {dest}"
    )
    cmd = [
        "ssh", "-F", os.devnull,
        "-i", str(SECRETS / "id_ed25519"), "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{USER}@{args.host}", remote,
    ]
    r = subprocess.run(cmd, input=body.encode(), capture_output=True)
    print(r.stdout.decode(errors="replace").strip())
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace").strip(), file=sys.stderr)
        return r.returncode
    print(f"Removed {len(lines) - len(kept)} DNS line(s); tunnel not started.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
