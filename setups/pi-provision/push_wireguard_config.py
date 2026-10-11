"""Install the Proton WireGuard config on the Pi, root-only, over SSH.

Run this once after flashing a fresh card (the first-boot script installs
wireguard-tools but deliberately carries no VPN config: the card's boot
partition is readable by anyone who holds the card). The config is read from
setups/.secrets/ (gitignored), the `DNS` line is dropped (the Pi has no
resolvconf, and wg-quick fails on a DNS line without it) and replaced by
PostUp/PostDown hooks that point NetworkManager at the tunnel's resolver while
the tunnel is up, and the file is written to /etc/wireguard/ with mode 600, owner root. The tunnel is NOT
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
    removed = len(lines) - len(kept)
    dns = [ln.split("=", 1)[1].strip() for ln in lines
           if ln.strip().lower().startswith("dns") and "=" in ln]
    if dns and not any(ln.strip().lower().startswith("postup") for ln in kept):
        # The Pi has no resolvconf (wg-quick's own DNS handling), so while the
        # tunnel is up NetworkManager is pointed at the tunnel's resolver for
        # every connected wired or Wi-Fi device (runtime only), and `reapply`
        # restores each device's profile settings when the tunnel goes down. IPv6
        # resolvers learned from the local network are ignored while it is up
        # (the tunnel's own IPv6 resolver address is not known, so none is set).
        devs = "$(nmcli -t -f DEVICE,STATE device | sed -n 's/:connected$//p' | grep -E '^(eth|wlan)')"
        # The resolver is also written to /run/pi-wg-dns/<interface>, which the
        # NetworkManager dispatcher script (installed by pi-firstboot.sh) reads,
        # so a device that connects or reconnects after the tunnel is up gets the
        # same override. PostDown removes the file first, so the dispatcher stays
        # idle while the devices are reapplied.
        resolver = dns[0].split(',')[0].strip()
        up = (f"PostUp = mkdir -p /run/pi-wg-dns; echo {resolver} > /run/pi-wg-dns/%i; "
              f"for d in {devs}; do nmcli device modify $d "
              f"ipv4.dns {resolver} ipv4.ignore-auto-dns yes "
              f"ipv6.ignore-auto-dns yes; done")
        down = (f"PostDown = rm -f /run/pi-wg-dns/%i; "
                f"for d in {devs}; do nmcli device reapply $d; done")
        at = next((i for i, ln in enumerate(kept) if ln.strip().lower() == "[peer]"), len(kept))
        kept[at:at] = [up, down, ""]
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
    print(f"Removed {removed} DNS line(s), added DNS hooks; tunnel not started.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
