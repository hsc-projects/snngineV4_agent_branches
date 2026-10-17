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
- **Behind a router (2026-10-16): works, and is the simplest path.** The Pi's `eth0`
  takes its address and internet from the router's DHCP (`10.99.1.103/16`, gateway
  `10.99.0.254`, 2 ms to the internet); the tunnel, Tailscale and the keyholder come up as
  before, and nothing depends on Windows sharing. Other devices on the router reach it
  directly. Earlier paths, tested when no router was available:
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
  tagging an already-joined node does not).
  `CorpDNS` and `RouteAll` are off, Tailscale SSH and shields-up are off (the
  normal sshd is the only SSH). The node state is in `/var/lib/tailscale` on
  the card (the primary copy), with a backup on the stick (`tailscale/tailscaled.state`,
  root, mode 600; `pi-firstboot.sh tailscale-backup` after a join). On a fresh flash
  the module puts it back while the node is not joined, so the Pi returns as the same
  node with no new login; the old card must not run at the same time. Tailscale's own traffic carries a
  mark and leaves by the main routing table (rule 5210), directly rather than
  through Proton; the tunnel's handshake, DNS and public address are unaffected.
  Access policy (text in `pi-provision/tailscale-policy.hujson`): the
  maintainer's own devices may open tcp 22 on `tag:pi` and nothing else; the
  Pi may start no connections to other devices. The phone (`fairphone-5-5g`,
  Android) reaches the Pi over the tailnet (via a relay, no direct path); the
  phone's key is authorised for the unlock user only (below). `bridge-relay` was offline (last seen 13 days before 2026-10-13).
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
  DNS dispatcher, installs Docker, git and Tailscale (the daemon only; the join is
  interactive), creates the `claude` user and installs tmux (`module_claude_user`), sets up the keyholder, then replaces the Wi-Fi password in
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
    down and its own network and DNS untouched.
  - **Stick pulled or plugged back in while running** (`module_keystore_hotplug`):
    systemd unmounts the vanished stick and stops the tunnel unit, but the stop cannot
    read the config, so the `wg-JP-154` interface and its routing stay up (traffic keeps
    leaving through Proton; the 5200 tailnet rules stay too). A udev rule
    (`/etc/udev/rules.d/90-pi-keystore.rules`) starts `pi-keystore-recover.service` when
    a device labelled `PIKEYS` appears: `/usr/local/sbin/pi-keystore-recover` mounts it,
    and, for each enabled tunnel unit that is not active, runs `wg-quick down` (the
    config is readable again) and restarts the unit; an active tunnel is left alone,
    since the rule also fires when the stick is found at boot. The unit is rate-limited
    (5 starts in 300 s). No reboot is needed; it is complete about 30 s after the replug.
  - **Rule order:** the drop-in removes the 5200 rules before the tunnel starts and adds
    them after, because the kernel numbers wg-quick's rules just below the lowest existing
    one: a leftover 5200 would put them ahead of it.
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
  - **Tailnet traffic goes first:** the drop-in adds policy rules at priority 5200
    (`100.64.0.0/10` and `fd7a:115c:a1e0::/48`, lookup table 52) after the tunnel
    starts and removes them when it stops. Without them, a tunnel that comes up after
    `tailscaled` puts its rules (5208, 5209) ahead of Tailscale's, and unmarked replies
    to tailnet addresses (the SYN-ACK of an SSH handshake) go into the tunnel and time out.
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
  that it decrypts back; from 2026-10-17 it also refuses a passphrase that does not open the
  secrets already stored, because unlock is all-or-nothing; tested on a scratch stick, and the
  live Pi gets it at the next flash). The `pikeys` user (no password, not locked) may only
  run `pi-unlock`: one sudoers line, and an `sshd` drop-in
  (`/etc/ssh/sshd_config.d/10-pikeys.conf`) that forces that command for that
  user, with no tty, forwarding or password and its key file on the stick
  (`unlock/authorized_keys`, so it survives a re-flash). The module validates
  the sudoers rule and `sshd` (`sshd -t`, the applied forced command) before
  reloading and removes its own config if a check fails. The laptop client is
  `pi-provision/pi_keyholder.py`; what to revoke if the Pi is lost is
  `pi-stolen-checklist.md`. The phone (Termux, key `pikeys_ed25519`, one line in
  `unlock/authorized_keys`) reaches `pi-unlock` over the tailnet on mobile data
  (`status` returns `stick: mounted`). Two secrets are stored, both read by the `claude` user
  once unlocked (since 2026-10-17): `runpod_api_key` (50 bytes, the key's length; it was
  root-readable before, changed so agents can use it) and `rclone_config_pass` (43 bytes, the
  random passphrase of the cloud-drive config); the phone's unlock puts them in
  `/run/pi-secrets` (RAM, mode 400). The Pi's helpers read lines with plain `read -r`, so a client must not
  send carriage returns (the laptop client sends bytes for that reason).

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
  2026-10-11, and again on 2026-10-17 with the current script: the Docker, Tailscale,
  keyholder, SSH host keys, `agy`, Remote Control and VS Code web modules). The `PIKEYS` stick is
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
  the stick), and it keeps the SSH host keys (on the stick too), so the fingerprint stays
  the same and nothing needs deleting; only a new stick makes new keys
  (then delete `pi-smoke-test/pi_smoke_test_known_hosts` and `ssh-keygen -R pi-host` on the
  phone and laptop). Without a Tailscale backup on the stick, delete the old node. To rewrite only the config of a card that has not
  booted: the same script with `--boot-dir F:\ --wifi-from-env --provision-script ...`
  (no admin; new cloud-init instance id).
- **Find and reach the Pi:** `python setups\pi-smoke-test\pi_smoke_test_ssh_check.py
  [--host IP] [--wait 180] [--sweep]`, from PowerShell (Git Bash's `ssh` rejects the
  `nul` it passes). The neighbour table can hold a stale entry: check port 22 on each
  `192.168.137.x` that maps to the Pi's MAC prefix `D8-3A-DD`. For longer checks pipe a
  script to `ssh ... htm@IP 'bash -s'`, starting with a throwaway line (a byte-order
  mark breaks line 1).
- **Windows sharing:** `setups\windows\restart-sharing.bat` (asks for admin) starts the
  service, switches sharing off everywhere and on for the chosen pair, and checks that
  DHCP listens; it detects the internet-side adapter (`-Public NAME` overrides). One
  shared connection at a time. A Pi that sat
  without DHCP for hours needs its cable replugged or a power cycle once sharing is
  back. If Wi-Fi as the internet side fails with `0x80040201`, use phone USB tethering
  (rationale item 19). The laptop's own Wi-Fi adapter was unreliable (it nearly froze the laptop),
  so since 2026-10-17 a USB Wi-Fi adapter in the laptop is the preferred internet side; if the
  script picks the wrong adapter, name it with `-Public NAME`.
- **After plugging the stick back in** it mounts and the tunnel returns by itself
  (see Software). `push_wireguard_config.py --host IP` is only for a new or changed
  config or a new stick.
- **If the provision service gave up** (6 starts per hour, so after about half an
  hour without network): `sudo systemctl reset-failed pi-provision.service`, then
  `sudo systemctl start pi-provision.service`.
- **Tailscale join:** the login link lasts 10 to 15 minutes, then the command exits
  with `context canceled` and needs a new one. Only without a backup on the stick: delete
  the node's stale predecessor in the admin console first, or the name gets a number.
- **Phone unlock (Termux, rebuilt after a reinstall):** `pkg install openssh`, then
  `ssh-keygen -t ed25519 -N "" -f ~/.ssh/pikeys_ed25519` and append the public line to
  `/mnt/pi-keys/unlock/authorized_keys` on the Pi (root-owned, group `pikeys`, mode 640).
  The command `$PREFIX/bin/pi-keys unlock|lock|status` runs
  `ssh -i ~/.ssh/pikeys_ed25519 -o IdentitiesOnly=yes pikeys@pi-host` and sends the request
  on stdin (`unlock`, then the passphrase on the next line, read with a hidden prompt; the
  other two verbs alone). Termux:Widget (same store and signing key as Termux) lists the
  scripts in `~/.shortcuts/` (`pi-unlock.sh`, `pi-lock.sh`, `pi-status.sh`, each calling
  `pi-keys <verb>` and waiting for Enter); each opens a terminal, so the passphrase prompt
  works. The Pi's SSH host keys are kept on the stick, so a re-flash keeps the fingerprint and
  the phone needs nothing (with a new stick: `ssh-keygen -R pi-host`, then check the
  fingerprint when it asks). The passphrase is 5 random words; paste it, since
  a stray space or autocorrect fails the unlock (`unlock failed`, 2 s delay each).
  A fourth widget script, `~/.shortcuts/pi-code.sh`, opens VS Code in the browser in one tap: it
  reads the connection token from the stick over SSH as `claude` (key `claude_ed25519`), then
  `termux-open-url`s `https://pi-host.tail5deeb7.ts.net/?tkn=<token>&folder=/home/claude/work`
  (the tailnet grant allows tcp 443; rationale item 28).
- **Claude Code on the Pi (2026-10-16, bare, no container):** an unprivileged user `claude`
  (groups `claude users`, no sudo, no password) holds the install and the login. Claude Code
  2.1.301 was installed as that user with Anthropic's official installer (read first; it
  downloads from `downloads.claude.ai`, checks the binary's SHA-256 against the manifest, and
  installs under the user's home: `~/.local/bin/claude`, on the card). The user and its
  wiring come from `module_claude_user` (also `pi-firstboot.sh claude-user`): the phone's key
  `claude_ed25519` (separate from the unlock key) is the only authorised key, kept on the
  stick (`claude/authorized_keys`, read by an sshd drop-in `20-claude.conf` for that user;
  no stick, no login as `claude`), and `~/.bashrc` sets `CLAUDE_CONFIG_DIR` to
  `/mnt/pi-keys/claude/config` while the stick is mounted (otherwise a `claude` function
  refuses to start, so it cannot log in a second time on the card). `git` and `tmux` are
  installed (git by the first-boot script). To use it: from Termux `ssh -i
  ~/.ssh/claude_ed25519 -o IdentitiesOnly=yes claude@pi-host`, then `tmux new -s claude`
  (`tmux attach -t claude` after a drop) and `claude`. Remote Control runs by itself as
  `claude-rc.service` (next entry); its session `pi` shows in the Claude app and
  claude.ai/code. A hand-started `/remote-control` in tmux also works but ends at reboot. The login (`/login`, subscription type `pro`) has
  the full scope set including `user:sessions:claude_code`, which Remote Control needs;
  `setup-token` and API keys do not. The URL printed by `/login` is pasted into the phone's
  address bar (line breaks from the wrapped terminal are stripped there) and the code it shows
  is pasted back. The login lives on the stick in plain files (mode 600, owner `claude`; about 20 MB of
  config, history and transcripts on a 4 GB stick), so a re-flash keeps it. The module also
  installs the binary itself (2026-10-17): Anthropic's installer first (3 attempts), else the
  copy cached on the stick (`claude/bin/claude-<version>`, refreshed after each installer
  success); so after a flash `claude` starts logged in with nothing to run by hand (tested,
  including the cache fallback with the download hosts blocked). The revoke path is in
  `pi-stolen-checklist.md`.
- **Also from first boot (2026-10-17):** `module_ssh_hostkeys` (host keys in `ssh-host/` on
  the stick), `module_agy` (`agy` in `~/.local/bin`, `~/.gemini` linked to `claude/gemini` on
  the stick, binary cached as `claude/bin/agy`), `module_claude_rc` (`claude-rc.service`, logs
  in `journalctl -u claude-rc`; trusted folders listed in the stick's `claude/trusted-dirs`)
  and `module_vscode_web` (`vscode-web.service`, loopback port 8000, token on the stick;
  rationale item 28; `serve-web` downloads its server on the first request, so the module
  makes that request itself). These extras download from third-party servers, so a failure
  there never blocks the core modules (Tailscale, keyholder): it is logged as `optional step
  ... failed`, the run goes on and ends non-zero without the marker, and the unit retries the
  whole run. Each also runs alone: `pi-firstboot.sh ssh-hostkeys|agy|claude-rc|vscode-web`.
  From the laptop: `ssh pi` or VS Code Remote-SSH host `pi` (user `claude`). Tested on the
  live Pi (including a reboot, and the installers fetching all three binaries from nothing) and
  on a fresh flash of card 2 (2026-10-17): every module ran with no manual step, the SSH
  fingerprint stayed the same, and both CLIs answered at once with their logins from the stick.
- **Cloud drives (2026-10-17; rationale item 23):** `module_cloud` installs rclone
  (`/usr/local/bin/rclone`, cached as `claude/bin/rclone` on the stick) and root-owned scripts:
  `/usr/local/bin/pi-cloud`, `/usr/local/sbin/pi-cloud-pass` (prints the config passphrase from
  `/run/pi-secrets/rclone_config_pass`, else from `cloud/config-pass` on the stick) and the phone
  login script in `/usr/local/share/pi-phone/`. Use: `pi-cloud status|login P|logout P|ls P
  [sub]|push [opts] P dir [sub]|pull [opts] P sub dir|sync|auto on|off` with P one of `gdrive
  dropbox onedrive mega proton`; the Pi's folder on every drive is `snngine-pi`; copy-only. Options
  of push and pull: `--videos`, `--only EXT,EXT`, `--exclude PATTERN` (ordered rclone `--filter`
  rules: excludes, then the includes, then `- *`; separate `--include` and `--exclude` flags are
  not applied in order and let an excluded folder through). **Timer:** `pi-cloud-sync.timer`
  (every 5 minutes, `OnBootSec=3min`) runs `pi-cloud sync` as `claude`, which does the jobs in
  `claude/sync.conf` on the stick (root-owned; one per line: `push|pull PROVIDER LOCALDIR
  SUBPATH|- [options]`): the whole `output/` folder of each task, both ways, and `dump` pulled into
  `~/dump`. Logs: `journalctl -u pi-cloud-sync`. Skips a round while locked, leaves files younger
  than a minute, and never fails the unit. One-time setup, from the laptop (prompts for the
  keyholder passphrase; the value is random and never shown): `python
  setups/pi-provision/pi_keyholder.py --host ADDRESS add rclone_config_pass --consumer claude
  --generate`. Logins, from the phone: the Termux:Widget shortcut `pi-cloud-login.sh` is a stub
  (`ssh claude@pi-host cat /usr/local/share/pi-phone/pi-cloud-login.sh` into a temporary file,
  then `bash` on it; the record is `pi-provision/phone/pi-cloud-login.sh`), so changes to the
  login script never need pasting again. It unlocks the keyholder if needed; type a provider
  at the `>` prompt, or `logout PROVIDER`. gdrive asks for an optional own client id and secret
  and the scope (blank, or `full`); onedrive opens the sign-in by itself; dropbox needs the key
  and secret of your own Dropbox app (developer console, "App folder" access, redirect URI
  `http://localhost:53682/`); mega and proton need the dedicated account's email and password.
  `pi-cloud auto on` (when unlocked) makes the logins and the timer work without an unlock (the
  stick alone then opens them). The config is `cloud/rclone.conf` on the stick, encrypted by
  rclone. Runs alone as `pi-firstboot.sh cloud`.
- **GitHub and the project clones (2026-10-17):** `module_github` installs `gh` and keeps its
  login on the stick (`GH_CONFIG_DIR` is `claude/gh`; set in `~/.bashrc` while the stick is
  mounted, and `gh` refuses to run without it); git uses it for https://github.com through a
  credential helper in the `claude` user's `~/.gitconfig`, and takes its identity from the
  stick's `claude/git-identity` (name, then email). Sign in once, as `claude` (device code; the
  scope is whatever you approve; full for now: repo, read:org, gist, workflow): `GH_CONFIG_DIR=
  /mnt/pi-keys/claude/gh gh auth login -h github.com -p https -w -s repo,read:org,gist,workflow`,
  then enter the printed code at https://github.com/login/device. The repos are cloned in
  `~/dev` on the card, as on the laptop's `E:\dev`: `autonomous-blender-sculptor`,
  `claude-code-and-local-agent-sandbox`, `private-public-repo-skills`,
  `private-public-repo-skills-internal`, `private-public-repo-skills-testing`,
  `SNNgine3D_agent_branches`, `snngineV4_agent_branches`, with the laptop's local branches that
  exist on GitHub (the laptop's local-only branches and its uncommitted changes are not on the
  Pi). The two task `output/` folders were copied from the laptop once; the cloud sync keeps
  them in step afterwards. Not automatic yet: cloning after a re-flash.
- **agy for the snngineV4 project (2026-10-17):** the laptop runs agy there with `agentMode:
  accept-edits`, `toolPermission: always-proceed`, `allowNonWorkspaceAccess: true` and that repo as
  its only trusted workspace. agy's settings are global (the CLI documents no per-project
  settings), so on the Pi `module_agy` sets the global trusted workspaces to exactly the two repos
  (`snngineV4_agent_branches`, `SNNgine3D_agent_branches`) and `allowNonWorkspaceAccess: true`
  (agents need `~/dump` and `/run/pi-secrets`, outside the project), and installs
  `/usr/local/bin/agy-snngine`, which starts agy in the snngineV4 repo with `--mode accept-edits
  --dangerously-skip-permissions --add-dir ~/dev/SNNgine3D_agent_branches`: the always-proceed
  permission belongs to that launcher only (the maintainer's decision), and plain `agy` keeps
  asking before it runs a command. Headless `agy -p` cannot approve commands without the flag.
- **RunPod key for agents (2026-10-17):** the keyholder secret `runpod_api_key` is listed for the
  `claude` user in the stick's `secrets.conf` (it was root), so after an unlock from the phone
  `/run/pi-secrets/runpod_api_key` (RAM, mode 400) is readable by agents on the Pi, and it is gone
  after a lock or reboot. It is the key the RunPod MCP (`https://mcp.getrunpod.io/`, an
  `Authorization` header) and the RunPod scripts need; the MCP config and the pod SSH key are not
  set up on the Pi yet (the maintainer will do that on first use).
- **One-click shortcuts on the phone (Termux:Widget):** `pi-ssh.sh` opens an SSH session as
  `claude` in a tmux session (`tmux new-session -A -s main`: the same session again after a
  drop), and `pi-agy.sh` runs `agy-snngine` in a tmux session named `agy` the same way. Both
  are two-line scripts around `ssh -t -i ~/.ssh/claude_ed25519 -o IdentitiesOnly=yes
  claude@pi-host`, with the logic on the Pi, so they never need updating.
- **Past errors:** first boot is configured by cloud-init, not `custom.toml`;
  `enable_ssh` alone did not start sshd on an early card (the empty `ssh` file did;
  rationale item 16); write the partition table last (Windows mounts the new
  partition and fails the write); a first "Permission denied" over SSH can be
  transient (cloud-init installs the key late). Admin tools need `sudo` (the PATH lacks
  `/usr/sbin`).
