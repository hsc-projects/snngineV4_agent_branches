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

- On a Tailscale network since 2026-10-11 (node `pi-host`, see Software). No
  RunPod pod reaches it yet; the pod's own Tailscale join is not set up.
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
     change (seen 2026-10-11; item 19 in the rationale, last follow-up of the report: with
     Wi-Fi as the internet side enabling sharing failed with `0x80040201`, with phone USB
     tethering it worked).
  3. **Wi-Fi to a phone hotspot (`wlan0`): works.** It joined, reached the
     internet through `wlan0` alone (the phone's carrier address), and
     with `eth0` also up both stayed connected for 6 minutes. The default
     route preferred `eth0` (metric 100) over `wlan0` (600) on the card
     tested. The flash script now gives `wlan0` a route metric of 50
     (netplan `dhcp4-overrides: route-metric`) so Wi-Fi is preferred when it
     is configured, and the cable becomes the backup (verified on the Pi
     2026-10-07 to 2026-10-11: `wlan0` default at 50, `eth0` at 100; the
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
- Docker (installed by hand 2026-10-11, now also `module_docker` in the
  first-boot script): Docker Engine 29.9.0, `containerd.io` 2.4.1, buildx 0.38.0
  and Compose 5.6.0 (`docker compose`) from Docker's own apt repository
  (`/etc/apt/sources.list.d/docker.sources`, key `/etc/apt/keyrings/docker.asc`,
  checked against the published fingerprint before use), arm64, trixie. Not
  Debian's older `docker.io`. `iptables` came in as a dependency and uses the
  `iptables-nft` backend (one of the two Docker supports). Cgroup v2, systemd cgroup
  driver, overlayfs. No user is in the `docker` group; use `sudo docker`.
  Tested beside the Proton tunnel: the tunnel kept its handshake, DNS stayed
  10.2.0.1, SSH was never interrupted, and containers leave through the tunnel
  (a container's public address equals the host's) with DNS through the tunnel
  resolver. Only `hello-world` and `busybox` were pulled (both still on the card).
  The script's own install path (key check, repo, packages) was run on a fresh
  flash of card 2 on 2026-10-11 and passed (module ok at 07:59:15 in the log; the
  whole first boot took about 3 minutes), and again on card 1 the same day.
- Tailscale (`module_tailscale` in the first-boot script; installed and joined
  2026-10-11): 1.104.1 from Tailscale's own apt repository (key
  `/usr/share/keyrings/tailscale-archive-keyring.gpg`; its primary fingerprint is
  pinned in the script, but Tailscale publishes none, so this is trust on first
  use). Joined interactively, never with an auth key on the card:
  `sudo tailscale up --accept-dns=false --hostname=pi-host --advertise-tags=tag:pi`,
  approved in the browser. Current node: `pi-host`, 100.119.40.123 (card 2, joined after a fresh flash on
  2026-10-11), account `hsc-projects@`, tagged `tag:pi` from the join, key expiry None
  (a join with a tag disables expiry; tagging an already-joined node does not: an
  earlier node, `pi-host-test`, 100.121.120.13, still expires 2027-04-09 and may still
  be listed in the console). `CorpDNS` and `RouteAll`
  are off, Tailscale SSH is off, shields-up is off (the normal sshd is the only SSH).
  The node state is in `/var/lib/tailscale` on the card, so a re-flash needs a new
  join (delete the old node first, or the name gets a number).
  Beside the Proton tunnel (checked on three joins, two cards): the tunnel's handshake, DNS
  (10.2.0.1) and public address were unchanged; Tailscale's own traffic carries a
  mark and leaves by the main routing table (rule 5210), directly rather than
  through Proton (its netcheck showed the home connection's address, nearest relay
  Tokyo).
  Access policy (saved 2026-10-11; text in `pi-provision/tailscale-policy.hujson`):
  the maintainer's own devices may open tcp 22 on `tag:pi` and nothing else; nothing
  else is allowed, including the Pi starting connections to other devices (checked:
  its ping to the phone fails with 100% loss). The phone (`fairphone-5-5g`, Android)
  reaches the Pi over the tailnet: `tailscale ping` 34 to 46 ms via the Tokyo relay
  (no direct path, both behind NAT), and its SSH attempts reached sshd (as
  `u0_a308`, then as `htm`; refused, since no phone key is authorised yet). Blocked
  ports were not tested live from the phone (the policy's saved `tests` block
  asserts that ports 80 and 2375 are denied). The laptop has no Tailscale;
  `bridge-relay` has been offline for 11 days.
- Services planned to run here: not finalized overall, but two are
  named:
  1. An egress-proxy (own instance vs. sharing this repo's existing
     `egress-proxy` config is undecided).
  2. An expanded `bridge-relay`/bridge server, giving phone-triggered
     RunPod pod spin-up an always-on trigger point independent of the
     maintainer's dev machine. Not yet designed — see
     `runpod-rationale.md`.
  3. Planned, not built (design in `pi-rationale.md`): the Pi's own MCP server
     (item 21) and the keyholder (item 20).
  Other small always-on services may follow — not yet scoped.
- First-boot provisioning: `pi-provision/pi-firstboot.sh` is carried in
  `user-data` (cloud-init `write_files`, installed at
  `/usr/local/sbin/pi-provision-firstboot.sh`) and run by `pi-provision.service`
  (also from `write_files`; `Type=simple`, `Restart=on-failure` every 5 minutes,
  at most 6 starts per hour, enabled so every boot retries until the marker
  exists), so it cannot hold up boot. It checks the system (root, aarch64,
  Debian 13), waits for time sync, installs `wireguard-tools` (no recommended
  packages) and verifies it, links the credential stick (next items), enables the
  tunnel at boot with its DNS dispatcher, installs Docker and Tailscale (the
  daemon only; the join is interactive; both modules added 2026-10-11), sets up the keyholder (see below), then replaces the Wi-Fi password in
  `/boot/firmware/network-config` with a placeholder once cloud-init is done (only
  if the root-only netplan copy exists) and verifies that. A skipped scrub fails the
  run, so it is retried. Log: `/var/log/pi-provision.log`; marker:
  `/var/lib/pi-provision.done`. Tested on the Pi with fresh flashes of both cards
  (2026-10-07, 2026-10-11), including a boot with no network and one without the
  stick. It carries no secret and no VPN config (those live on the stick).
- WireGuard / Proton VPN: `wireguard-tools` 1.0.20210914-3 is installed by the
  first-boot script (kernel module `wireguard` is available as
  `CONFIG_WIREGUARD=m`). The Proton config (`wg-JP-154.conf`, Japan server, `DNS`
  line removed because the Pi has no `resolvconf`) lives on the credential stick
  (next item), reachable as `/etc/wireguard/` (mode 600, root). Tested by hand
  2026-10-04 on an earlier card: handshake, a Japanese public IP, IPv4 and IPv6
  through the tunnel. Re-tested 2026-10-07 on a fresh flash, with the laptop's
  ProtonVPN up the whole time: `wg-quick up` gave a handshake, the Pi's public
  address changed (country JP), IPv4 and IPv6 worked, the SSH session stayed up and
  the route to the laptop (`192.168.137.1`) stayed on `eth0`; `wg-quick down`
  restored the original address and routes. Over the cable only (`wlan0` was not
  connected). **Up at every boot** (2026-10-07): `wg-quick@wg-JP-154` is enabled; the first-boot
  script does this when exactly one config is present (`module_wireguard_autostart`,
  also `pi-firstboot.sh autostart`). A drop-in `wg-quick@.service.d/pi-provision.conf`
  requires the stick's mount and restarts the unit every 30 s on failure; with no
  stick the unit fails and the Pi still boots and stays reachable (the way out if a
  tunnel ever blocks access). Tested on the live Pi: reboot, tunnel up unaided with
  a handshake, Proton address, tunnel resolver and SSH intact. Boot without the stick (tested 2026-10-11): the device wait for
  `PIKEYS` times out after 10 s, the mount, its fsck and the tunnel unit fail with
  `dependency`, the Pi boots and stays reachable, the tunnel stays down and the
  Pi's own network and DNS are untouched. A failed mount is not retried when the
  stick is plugged back in: reboot (or run `pi-firstboot.sh keystore` and start the
  tunnel unit); after replug and reboot the tunnel came up unaided. The autostart
  step inside a fresh-flash first boot is tested. Boot with no network (tested 2026-10-11, cable out): the tunnel unit
  started and finished at once (the endpoint is an address, so `wg-quick up` needs no
  lookup and sets up the interface offline); when the cable came in, `eth0` got its
  lease, WireGuard handshook within seconds, the dispatcher put `10.2.0.1` on `eth0`,
  and the Pi exited through Proton, with no restart (`NRestarts=0`). So the 30 s
  restart only matters if `wg-quick up` itself fails (for example an endpoint given
  as a name). That path was forced on the real unit (a temporary
  `ExecStartPre=/bin/false` drop-in): the unit went to `auto-restart`, retried every
  30 s (`NRestarts` 2 after 75 s), and once the failure was removed the next retry
  succeeded with handshake, Proton address and tunnel DNS.  DNS: without a fix the Pi kept using the laptop's resolver
  (`192.168.137.1`, on the cable subnet, outside the tunnel) with the tunnel up, a
  DNS leak. The config now carries `PostUp`/`PostDown` hooks (added by
  `push_wireguard_config.py` from the config's own `DNS` line) that point
  NetworkManager's connected devices at the tunnel resolver while the tunnel is up
  and `nmcli device reapply` them on the way down. Tested 2026-10-07: tunnel up,
  `/etc/resolv.conf` has only `10.2.0.1`, which answers from a Proton exit address;
  tunnel down, the previous resolvers are back exactly, with `eth0` and `wlan0` both
  connected. The hooks alone only cover devices connected when the tunnel comes
  up; a device that connects or reconnects later (measured: `eth0` got its lease
  after the tunnel on a first boot) kept its network's DNS. So `PostUp` also writes
  the resolver to `/run/pi-wg-dns/<interface>` (`PostDown` removes it first) and a
  NetworkManager dispatcher script, `/etc/NetworkManager/dispatcher.d/90-pi-wg-dns`
  (installed by the first-boot script), re-applies it on `up`, `dhcp4-change`,
  `dhcp6-change` and `reapply` for `eth*`/`wlan*`, only when the applied DNS differs;
  with no tunnel file it does nothing. Tested 2026-10-11: `wlan0` disconnect and
  reconnect while the tunnel was up (back to `10.2.0.1`), tunnel stop (each device's
  own DNS and the original address restored) and start, and a fresh flash (script
  installed it, `eth0` and `resolv.conf` show only `10.2.0.1`). IPv6 resolvers learned
  from the local network are ignored while the tunnel is up (`ipv6.ignore-auto-dns`; the tunnel's IPv6 resolver address is not
  known, so none is set); this network offers no IPv6 resolver, so that part is
  accepted by NetworkManager but its effect is untested. This is the reason the
  Pi holds its own config: its traffic through the laptop's connection sharing
  bypasses the laptop's VPN (measured earlier, see the smoke-test report; today's
  Pi address before the tunnel again differed from the laptop's VPN address). Proton's own Linux app/CLI does
  not support headless setups. `resolvconf` is not installed; `iptables` (the `iptables-nft`
  backend) came in with Docker, and `nft` was there before. Note: `htm`'s PATH lacks `/usr/sbin`, so admin tools only show up
  with `sudo`.
- Credential stick (`PIKEYS`): a 4 GB USB stick, ext4 (not encrypted: an
  unattended boot cannot supply a passphrase), plugged into a blue USB 3 port of
  the Pi. Mounted at `/mnt/pi-keys` by label with `nofail` (a Pi without the
  stick still boots). Its top-level `links.conf` lists `<folder on the stick>
  <absolute target path>` per line; `pi-firstboot.sh` links each one (today only
  `wireguard /etc/wireguard`), never overwriting a populated directory on either
  side. Nothing in the script knows what the folders hold, so other credentials
  are a new line and folder on the stick. Tested 2026-10-07: live module run
  (moves existing files, idempotent on a second run), reboot (still mounted and
  linked), and a fresh flash of a second card with the stick left in (first-boot
  script linked it unaided). `pi-firstboot.sh keystore` re-runs the linking later;
  `pi-firstboot.sh format-keystore /dev/sdX` (explicit, never automatic) makes a
  new stick. `setups/pi-provision/push_wireguard_config.py --host IP` pushes the
  laptop's copy over SSH (the stick is reached through the link).

- Keyholder (`module_keyholder` in the first-boot script, `pi-firstboot.sh
  keyholder`; installed on the live Pi 2026-10-11 and through the first boot of a fresh flash of
  card 2 the same evening; design in `pi-rationale.md` item 20): high-value secrets are stored on the stick only as passphrase-encrypted files
  (`secrets/<name>.gpg`, gpg symmetric AES256, listed in `secrets.conf` with the user
  that reads each) and are decrypted into RAM on request (`/run/pi-secrets/<name>`,
  tmpfs, mode 0400, owned by that user, gone on power loss or a lock). Two root-owned
  helpers in `/usr/local/sbin`: `pi-unlock` (stdin protocol: `unlock` plus the
  passphrase, `lock`, `status`; all-or-nothing; output has names, never values) and
  `pi-secret-add` (admin only; encrypts a value onto the stick and checks that it
  decrypts back). The `pikeys` user (no password, not locked) may only run `pi-unlock`:
  one sudoers line, and an `sshd` drop-in (`/etc/ssh/sshd_config.d/10-pikeys.conf`)
  that forces that command for that user, with no tty, forwarding or password and its
  key file on the stick (`unlock/authorized_keys`, so it survives a re-flash). The
  module validates the sudoers rule and `sshd` (`sshd -t`, the applied forced command)
  before reloading and removes its own config if a check fails. The laptop client is
  `pi-provision/pi_keyholder.py`; what to revoke if the Pi is lost is
  `pi-stolen-checklist.md`. No secret is stored yet.

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
- The Pi's own Tailscale join uses no auth key (interactive approval, see
  Software). Tailscale auth key for the RunPod pod: not yet provisioned. Plan (from
  `runpod-rationale.md`): supplied to the RunPod pod via RunPod's
  `create-secret`, not hardcoded.
