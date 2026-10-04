# Pi host — technical

Current configuration for the dedicated always-on host (a PoE Raspberry
Pi): a general-purpose Docker-capable machine, running small always-on
services — the egress proxy the RunPod agent pod reaches over Tailscale,
and potentially other MCP servers/services alongside it. Rationale,
alternatives, and open items: `pi-rationale.md`. Why this machine exists
at all (the RunPod-side egress problem that triggered it):
`runpod-rationale.md`.

## Hardware

Already owned, capable enough that hardware is not expected to be a
limiting factor — not a purchase decision.

- **Model:** Raspberry Pi 4 Model B, 8GB RAM.
- **CPU:** 1.5GHz 64-bit quad-core.
- **Storage:** a 119.4 GiB (128 GB-class) SD card; the root partition
  is 117 GB, grown to fill the card on first boot (smoke test,
  2026-10-04). No other storage confirmed.
- **Model/CPU as seen by the OS:** aarch64, kernel `6.18.50+rpt-rpi-v8`;
  the Ethernet address has a Raspberry Pi vendor prefix (`d8:3a:dd`).
- **PoE hat/injector:** not yet recorded (maintainer, 2026-09-28).

## Network

- Not yet joined to a Tailscale network.
- Not yet has a fixed address reachable from a RunPod pod.
- No router is planned for this host/Pi combination. Tested (smoke test,
  2026-10-04), details in `pi-smoke-test/pi-smoke-test-report.md`:
  1. **Plain cable straight to the laptop (no DHCP server): not usable.**
     The Pi has only an IPv6 link-local address and answers by mDNS
     (`pi-host.local`), but NetworkManager's DHCP on `eth0` fails every
     45 s and about 3 minutes after boot the Pi goes silent (measured on
     two cards). IPv6 must also be enabled on the laptop; it was seen off on
     the physical adapters, including while ProtonVPN was connected (cause
     not established).
  2. **Cable plus Windows Internet Connection Sharing on the laptop's
     Ethernet adapter: works.** The laptop becomes `192.168.137.1/24` and
     answers DHCP/DNS; the Pi gets `192.168.137.x`, reaches the internet
     through the laptop's Wi-Fi, and stayed connected for 8 minutes with no
     dropout. With a VPN connected on the laptop the Pi's traffic bypasses
     the VPN. Sharing can reset after a laptop reboot, sleep or Wi-Fi
     change (not seen here).
  3. **Wi-Fi to a phone hotspot (`wlan0`): works.** It joined, reached the
     internet through `wlan0` alone (the phone's carrier address), and
     with `eth0` also up both stayed connected for 6 minutes. The default
     route preferred `eth0` (metric 100) over `wlan0` (600) on the card
     tested. The flash script now gives `wlan0` a route metric of 50
     (netplan `dhcp4-overrides: route-metric`) so Wi-Fi is preferred when it
     is configured, and the cable becomes the backup; **not yet tested on
     the Pi** (it takes a flash or a `--boot-dir` rewrite with
     `--wifi-from-env`; to check it, read `ip route` once both links are up,
     because the metrics only show when both have a default route; the
     hotspot does not have to be on at boot). With the hotspot
     turned off and on again, `wlan0` reconnected by itself (short absence
     only). **Cold boot with the hotspot off and only the shared cable
     (tested 2026-10-04): works.** Reachable about 40 s after power-on,
     internet over `eth0` alone, `wlan0` stayed down without interfering,
     cloud-init `done`, and `eth0` stayed connected for 72 consecutive 5 s
     heartbeats (about 6 minutes). A plain cable with no sharing at all still
     drops after about 3 minutes (item 1 above).
  Behind a router/DHCP network: not tested.
- `eth0` is configured through cloud-init's `network-config`: `dhcp4: true`,
  `optional: true`. Netplan's `link-local: [ipv4, ipv6]` was tried and has no
  effect on the generated NetworkManager profile (`ipv6.method ignore`), so
  it is not used.
- The Pi's clock is wrong for a few seconds after boot until network time
  syncs, so HTTPS fails in that window. Its journal is volatile
  (`Storage=volatile`): the previous boot's log is lost on reboot. `iw` is
  not installed.

## Software

- OS: **not finally chosen.** Currently Raspberry Pi OS Lite 64-bit
  (Debian 13 "trixie", release 2026-09-15), installed only as the
  smoke test's OS (`pi-smoke-test/`). Hostname `pi-host`; account `htm`
  (key-only, passwordless `sudo`). First boot is configured by cloud-init
  (`user-data`, `network-config`, `meta-data` on the boot partition) plus
  an empty `ssh` file (the Pi deletes it once used); the older
  `custom.toml` is not read by this release. `user-data` can also carry
  `packages:`, `write_files:` and `runcmd:` for installs on first boot
  (needs internet at that moment; not used yet).
- Docker: not yet installed. Real Docker (not the RunPod pod's
  restricted environment) is expected to work normally here — a Pi is a
  real machine with normal `CAP_NET_ADMIN`/nftables access, unlike a
  RunPod pod (see `runpod-rationale.md`'s Docker-in-Docker evidence).
- Services planned to run here: not finalized overall, but two are
  named:
  1. An egress-proxy (own instance vs. sharing this repo's existing
     `egress-proxy` config is undecided).
  2. An expanded `bridge-relay`/bridge server, giving phone-triggered
     RunPod pod spin-up an always-on trigger point independent of the
     maintainer's dev machine. Not yet designed — see
     `runpod-rationale.md`.
  Other small always-on services may follow — not yet scoped.
- WireGuard / Proton VPN: `wireguard-tools` 1.0.20210914-3 is installed
  (kernel module `wireguard` is available as `CONFIG_WIREGUARD=m`).
  `/etc/wireguard/wg-JP-154.conf` (root-only, mode 600) holds a Proton
  config for a Japan server with the `DNS` line removed. Tested by hand
  2026-10-04: handshake, a Japanese public IP, IPv4 and IPv6 through the
  tunnel. It is **not enabled at boot** and is currently down; DNS through
  the tunnel is untested. Proton's own Linux app/CLI does not support headless
  setups. `iptables` and `resolvconf` are not installed; `nft` is. Note:
  `htm`'s PATH lacks `/usr/sbin`, so admin tools only show up with `sudo`.
- Tailscale client: not yet installed.

## Credentials

- SSH: login as `htm` with the key pair kept (gitignored) in
  `setups/.secrets/`. `user-data` locks the account's password and sets
  `ssh_pwauth: false`; checked 2026-10-04 on the running Pi: a
  password-only attempt is refused with `Permission denied (publickey)`,
  so only key login is offered. The public key is baked into `user-data`
  by `pi-smoke-test/pi_smoke_test_flash.py`.
- Wi-Fi (phone hotspot): the name and password live in
  `setups/.secrets/.env` (`HOTSPOT_NAME`, `HOTSPOT_PASSWORD`, optional
  `HOTSPOT_COUNTRY`; gitignored) and are written to the card's
  `network-config` by `--wifi-from-env`. They end up **in plain text on the
  card**.
- Proton WireGuard config (contains a private key): kept in
  `setups/.secrets/wg-JP-154.conf` (gitignored, restricted to the maintainer's
  account) and, root-only, in `/etc/wireguard/` on the Pi. Never printed or
  committed.
- Tailscale auth key: not yet provisioned. Plan (from
  `runpod-rationale.md`): supplied to the RunPod pod via RunPod's
  `create-secret`, not hardcoded.
