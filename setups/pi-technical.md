# Pi host — technical

Current configuration for the dedicated always-on host (a PoE Raspberry
Pi): a general-purpose Docker-capable machine, running small always-on
services — the egress proxy the RunPod agent pod reaches over Tailscale,
and potentially other MCP servers/services alongside it. Rationale,
alternatives, and open items: `pi-rationale.md`. Why this machine exists
at all (the RunPod-side egress problem that triggered it):
`runpod-rationale.md`. Evidence for the statements below (what was tested,
when, with what result): `pi-smoke-test/pi-smoke-test-report.md`.

## Hardware

Already owned, capable enough that hardware is not expected to be a
limiting factor — not a purchase decision.

- **Model:** Raspberry Pi 4 Model B, 8GB RAM, 1.5GHz 64-bit quad-core;
  aarch64, kernel `6.18.50+rpt-rpi-v8`; Ethernet vendor prefix `d8:3a:dd`.
- **Storage:** a 119.4 GiB (128 GB-class) SD card; the root partition
  (117 GB) is grown to fill the card on first boot. No other storage
  besides the credential stick (see Software).
- **PoE hat/injector:** not yet recorded (maintainer, 2026-09-28).

## Network

- On a Tailscale network (node `pi-host`, see Software). No RunPod pod
  reaches it yet; the pod's own Tailscale join is not set up.
- No router is planned for this host/Pi combination. Three paths (behind a
  router/DHCP network: not tested):
  1. **Plain cable straight to the laptop (no DHCP server): not usable.**
     The Pi has only an IPv6 link-local address and answers by mDNS
     (`pi-host.local`), but NetworkManager's DHCP on `eth0` fails every
     45 s and about 3 minutes after boot the Pi goes silent. IPv6 must
     also be enabled on the laptop; it was seen off on the physical
     adapters (cause not established).
  2. **Cable plus Windows Internet Connection Sharing on the laptop's
     Ethernet adapter: works.** The laptop becomes `192.168.137.1/24` and
     answers DHCP/DNS; the Pi gets `192.168.137.x` (changes between boots)
     and reaches the internet through the laptop. With a VPN connected on
     the laptop the Pi's traffic bypasses it. Sharing can reset after a
     laptop reboot, sleep or Wi-Fi change; with Wi-Fi as the internet side
     enabling it can fail with `0x80040201`, with phone USB tethering it
     worked (rationale item 19).
  3. **Wi-Fi to a phone hotspot (`wlan0`): works**, also alone. The flash
     script gives `wlan0` a route metric of 50 (netplan
     `dhcp4-overrides: route-metric`) so Wi-Fi is preferred when it is
     configured; `eth0` (metric 100) is the backup. The hotspot does not
     have to be on at boot, and `wlan0` reconnects by itself after a short
     absence. A cold boot with only the shared cable works (reachable
     about 40 s after power-on).
- `eth0` is configured through cloud-init's `network-config`: `dhcp4: true`,
  `optional: true`. Netplan's `link-local: [ipv4, ipv6]` has no effect on the
  generated NetworkManager profile (`ipv6.method ignore`), so it is not used.
- The Pi's clock is wrong for a few seconds after boot until network time
  syncs, so HTTPS fails in that window. Its journal is volatile
  (`Storage=volatile`): the previous boot's log is lost on reboot. `iw` is
  not installed.

## Software

- OS: **not finally chosen.** Currently Raspberry Pi OS Lite 64-bit
  (Debian 13 "trixie", release 2026-09-15), installed as the smoke test's
  OS (`pi-smoke-test/`). Hostname `pi-host`; account `htm` (key-only,
  passwordless `sudo`). First boot is configured by cloud-init (`user-data`,
  `network-config`, `meta-data` on the boot partition) plus an empty `ssh`
  file (the Pi deletes it once used); the older `custom.toml` is not read by
  this release.
- Docker (`module_docker` in the first-boot script): Docker Engine 29.9.0,
  `containerd.io` 2.4.1, buildx 0.38.0 and Compose 5.6.0 (`docker compose`)
  from Docker's own apt repository (`/etc/apt/sources.list.d/docker.sources`,
  key `/etc/apt/keyrings/docker.asc`, checked against the published
  fingerprint before use), arm64, trixie; not Debian's older `docker.io`.
  `iptables` uses the `iptables-nft` backend. Cgroup v2, systemd cgroup
  driver, overlayfs. No user is in the `docker` group; use `sudo docker`.
  Beside the Proton tunnel, containers leave through the tunnel with DNS
  through the tunnel resolver. Only `hello-world` and `busybox` were pulled.
- Tailscale (`module_tailscale` in the first-boot script): 1.104.1 from
  Tailscale's own apt repository (key
  `/usr/share/keyrings/tailscale-archive-keyring.gpg`; its primary fingerprint
  is pinned in the script, but Tailscale publishes none, so this is trust on
  first use). Joined interactively, never with an auth key on the card:
  `sudo tailscale up --accept-dns=false --hostname=pi-host --advertise-tags=tag:pi`.
  Current node: `pi-host`, 100.119.40.123, account `hsc-projects@`, tagged
  `tag:pi` from the join, key expiry None (a join with a tag disables expiry;
  tagging an already-joined node does not). An older node, `pi-host-test`
  (100.121.120.13, expires 2027-04-09), may still be listed in the console.
  `CorpDNS` and `RouteAll` are off, Tailscale SSH and shields-up are off (the
  normal sshd is the only SSH). The node state is in `/var/lib/tailscale` on
  the card, so a re-flash needs a new join. Tailscale's own traffic carries a
  mark and leaves by the main routing table (rule 5210), directly rather than
  through Proton; the tunnel's handshake, DNS and public address are unaffected.
  Access policy (text in `pi-provision/tailscale-policy.hujson`): the
  maintainer's own devices may open tcp 22 on `tag:pi` and nothing else; the
  Pi may start no connections to other devices. The phone (`fairphone-5-5g`,
  Android) reaches the Pi over the tailnet (via a relay, no direct path); no
  phone key is authorised for SSH yet. The laptop has no Tailscale;
  `bridge-relay` was offline (last seen 13 days before 2026-10-13).
- Services planned to run here: not finalized overall, but two are
  named:
  1. An egress-proxy (own instance vs. sharing this repo's existing
     `egress-proxy` config is undecided).
  2. An expanded `bridge-relay`/bridge server, giving phone-triggered
     RunPod pod spin-up an always-on trigger point independent of the
     maintainer's dev machine. Not yet designed — see
     `runpod-rationale.md`.
  3. Planned, not built (design in `pi-rationale.md`): the Pi's own MCP server
     (item 21). The keyholder (item 20) is built; see below.
  Other small always-on services may follow — not yet scoped.
- First-boot provisioning: `pi-provision/pi-firstboot.sh` is carried in
  `user-data` (cloud-init `write_files`, installed at
  `/usr/local/sbin/pi-provision-firstboot.sh`) and run by `pi-provision.service`
  (also from `write_files`; `Type=simple`, `Restart=on-failure` every 5 minutes,
  at most 6 starts per hour, enabled so every boot retries until the marker
  exists), so it cannot hold up boot. It checks the system (root, aarch64,
  Debian 13), waits for time sync, installs `wireguard-tools` (no recommended
  packages), links the credential stick, enables the tunnel at boot with its
  DNS dispatcher, installs Docker and Tailscale (the daemon only; the join is
  interactive), sets up the keyholder, then replaces the Wi-Fi password in
  `/boot/firmware/network-config` with a placeholder once cloud-init is done
  (only if the root-only netplan copy exists) and verifies that. A skipped
  scrub fails the run, so it is retried. Log: `/var/log/pi-provision.log`;
  marker: `/var/lib/pi-provision.done`. A whole first boot takes about 3
  minutes. It carries no secret and no VPN config (those live on the stick).
- WireGuard / Proton VPN: `wireguard-tools` 1.0.20210914-3 is installed by the
  first-boot script (kernel module `wireguard`, `CONFIG_WIREGUARD=m`). The
  Proton config (`wg-JP-154.conf`, Japan server, `DNS` line removed because the
  Pi has no `resolvconf`) lives on the credential stick, reachable as
  `/etc/wireguard/` (mode 600, root). The Pi holds its own tunnel because its
  traffic through the laptop's connection sharing bypasses the laptop's VPN.
  Proton's own Linux app/CLI does not support headless setups.
  - **Up at every boot:** `wg-quick@wg-JP-154` is enabled (the first-boot
    script does this when exactly one config is present: `module_wireguard_autostart`,
    also `pi-firstboot.sh autostart`). A drop-in `wg-quick@.service.d/pi-provision.conf`
    requires the stick's mount and restarts the unit every 30 s on failure.
  - **No stick:** the device wait for `PIKEYS` times out after 10 s, the mount,
    its fsck and the tunnel unit fail with `dependency`; the Pi still boots and
    stays reachable (the way out if a tunnel ever blocks access), with the tunnel
    down and its own network and DNS untouched. A failed mount is not retried when
    the stick is plugged back in: reboot (or run `pi-firstboot.sh keystore` and
    start the tunnel unit).
  - **No network at boot:** the unit still starts (the endpoint is an address, so
    `wg-quick up` needs no lookup); the handshake happens once `eth0` has a lease.
    The 30 s restart only matters if `wg-quick up` itself fails (for example an
    endpoint given as a name).
  - **DNS through the tunnel:** the config carries `PostUp`/`PostDown` hooks (added
    by `push_wireguard_config.py` from the config's own `DNS` line) that point
    NetworkManager's connected devices at the tunnel resolver while it is up and
    `nmcli device reapply` them on the way down. `PostUp` also writes the resolver
    to `/run/pi-wg-dns/<interface>` and a NetworkManager dispatcher script,
    `/etc/NetworkManager/dispatcher.d/90-pi-wg-dns` (installed by the first-boot
    script), re-applies it on `up`, `dhcp4-change`, `dhcp6-change` and `reapply`
    for `eth*`/`wlan*` when the applied DNS differs, so devices that connect later
    are covered; with no tunnel file it does nothing. IPv6 resolvers learned from
    the local network are ignored while the tunnel is up (`ipv6.ignore-auto-dns`);
    the effect of that was not tested (this network offers none).
  - `resolvconf` is not installed; `htm`'s PATH lacks `/usr/sbin`, so admin tools
    only show up with `sudo`.
- Credential stick (`PIKEYS`): a 4 GB USB stick, ext4 (not encrypted: an
  unattended boot cannot supply a passphrase), plugged into a blue USB 3 port of
  the Pi. Mounted at `/mnt/pi-keys` by label with `nofail` (a Pi without the
  stick still boots). Its top-level `links.conf` lists `<folder on the stick>
  <absolute target path>` per line; `pi-firstboot.sh` links each one (today only
  `wireguard /etc/wireguard`), never overwriting a populated directory on either
  side. Nothing in the script knows what the folders hold, so other credentials
  are a new line and folder on the stick. `pi-firstboot.sh keystore` re-runs the
  linking later; `pi-firstboot.sh format-keystore /dev/sdX` (explicit, never
  automatic) makes a new stick. `setups/pi-provision/push_wireguard_config.py
  --host IP` pushes the laptop's copy over SSH.
- Keyholder (`module_keyholder` in the first-boot script, `pi-firstboot.sh
  keyholder`; design in `pi-rationale.md` item 20): high-value secrets are
  stored on the stick only as passphrase-encrypted files (`secrets/<name>.gpg`,
  gpg symmetric AES256, listed in `secrets.conf` with the user that reads each)
  and are decrypted into RAM on request (`/run/pi-secrets/<name>`, tmpfs, mode
  0400, owned by that user, gone on power loss or a lock). Two root-owned
  helpers in `/usr/local/sbin`: `pi-unlock` (stdin protocol: `unlock` plus the
  passphrase, `lock`, `status`; all-or-nothing; output has names, never values)
  and `pi-secret-add` (admin only; encrypts a value onto the stick and checks
  that it decrypts back). The `pikeys` user (no password, not locked) may only
  run `pi-unlock`: one sudoers line, and an `sshd` drop-in
  (`/etc/ssh/sshd_config.d/10-pikeys.conf`) that forces that command for that
  user, with no tty, forwarding or password and its key file on the stick
  (`unlock/authorized_keys`, so it survives a re-flash). The module validates
  the sudoers rule and `sshd` (`sshd -t`, the applied forced command) before
  reloading and removes its own config if a check fails. The laptop client is
  `pi-provision/pi_keyholder.py`; what to revoke if the Pi is lost is
  `pi-stolen-checklist.md`. No secret is stored yet; a real reboot and an
  absent stick were not tested with it.

## Credentials

- SSH: login as `htm` with the key pair kept (gitignored) in
  `setups/.secrets/`. `user-data` locks the account's password and sets
  `ssh_pwauth: false`, so only key login is offered. The public key is baked
  into `user-data` by `pi-smoke-test/pi_smoke_test_flash.py`.
- Wi-Fi (phone hotspot): the name and password live in
  `setups/.secrets/.env` (`HOTSPOT_NAME`, `HOTSPOT_PASSWORD`, optional
  `HOTSPOT_COUNTRY`; gitignored) and are written to the card's
  `network-config` by `--wifi-from-env`. They end up **in plain text on the
  card** until the first-boot script scrubs the boot partition's copy.
- Proton WireGuard config (contains a private key): kept in
  `setups/.secrets/wg-JP-154.conf` (gitignored, restricted to the maintainer's
  account) and, root-only, on the stick. Never printed or committed.
- The Pi's own Tailscale join uses no auth key (interactive approval, see
  Software). Tailscale auth key for the RunPod pod: not yet provisioned. Plan (from
  `runpod-rationale.md`): supplied to the RunPod pod via RunPod's
  `create-secret`, not hardcoded.

## Operating the Pi

- **Cards** (both about 119 GiB with a Pi OS boot partition, so the flash script's
  size window cannot tell them apart; identify by exact size): card 1, 128,177,930,240
  bytes, the spare, out of the Pi; card 2, 127,865,454,592 bytes, in the Pi (flashed
  2026-10-11 with the Docker, Tailscale and keyholder modules). The `PIKEYS` stick is
  not a card to flash. Disk numbers change between sessions. **Before wiping a card or
  stick, ask what is on its Linux partition** (Windows cannot read it; a wipe on
  2026-10-07 lost the hand-installed tunnel setup, and one spare card held personal
  photos), check its exact size, and wait for the owner's go.
- **Flash** (wipes the card; elevated PowerShell, or `Start-Process powershell -Verb
  RunAs` with output to a log; single-quote paths with spaces; run in the background,
  since heavy writes make Windows disk queries slow; cancel Windows' "format this
  disk" dialogs): `python setups\pi-smoke-test\pi_smoke_test_flash.py --image
  <raspios_lite_arm64 image> --device N --confirm-device
  "\\.\PhysicalDriveN" --wifi-from-env --provision-script
  setups\pi-provision\pi-firstboot.sh` (image: Raspberry Pi OS Lite 64-bit,
  2026-09-15, checksum verified). A re-flash needs no WireGuard push (the config is on
  the stick); delete `pi-smoke-test/pi_smoke_test_known_hosts` first (new host keys)
  and the old Tailscale node. To rewrite only the config of a card that has not
  booted: the same script with `--boot-dir F:\ --wifi-from-env --provision-script ...`
  (no admin; new cloud-init instance id).
- **Find and reach the Pi:** `python setups\pi-smoke-test\pi_smoke_test_ssh_check.py
  [--host IP] [--wait 180] [--sweep]`, from PowerShell (Git Bash's `ssh` rejects the
  `nul` it passes). The neighbour table can hold a stale entry: check port 22 on each
  `192.168.137.x` that maps to the Pi's MAC prefix `D8-3A-DD`. For longer checks pipe a
  script to `ssh ... htm@IP 'bash -s'`, starting with a throwaway line (a byte-order
  mark breaks line 1).
- **Windows sharing:** `setups\restart-sharing.bat` (asks for admin) starts the
  service, switches sharing off everywhere and on for the chosen pair, and checks that
  DHCP listens; it detects the internet-side adapter (`-Public NAME` overrides). One
  shared connection at a time. A Pi that sat
  without DHCP for hours needs its cable replugged or a power cycle once sharing is
  back. If Wi-Fi as the internet side fails with `0x80040201`, use phone USB tethering
  (rationale item 19).
- **After plugging the stick back in,** reboot the Pi (a failed mount is not retried).
  `push_wireguard_config.py --host IP` is only for a new or changed config or a new
  stick.
- **If the provision service gave up** (6 starts per hour, so after about half an
  hour without network): `sudo systemctl reset-failed pi-provision.service`, then
  `sudo systemctl start pi-provision.service`.
- **Tailscale join:** the login link lasts 10 to 15 minutes, then the command exits
  with `context canceled` and needs a new one. Delete the node's stale predecessor in
  the admin console first, or the name gets a number.
- **Past errors:** first boot is configured by cloud-init, not `custom.toml`;
  `enable_ssh` alone did not start sshd on an early card (the empty `ssh` file did;
  rationale item 16); write the partition table last (Windows mounts the new
  partition and fails the write); a first "Permission denied" over SSH can be
  transient (cloud-init installs the key late). Admin tools need `sudo` (the PATH lacks
  `/usr/sbin`).
