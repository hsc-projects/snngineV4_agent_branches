# Pi smoke test — report

Structure per `setups/report-format.md`: one top-level section per phase,
each with a short summary followed by detail subsections. Corrected
2026-10-04: an earlier version of this report blamed the Pi's early silence
on "first boot still running" and presented netplan's `link-local` as the
fix; both were wrong (see Phase 2).

## Phase 1 — write, configure, and flash the image

**Summary: done (2026-10-04), from a Windows laptop, after a failed first
attempt on Linux (2026-09-28).** A Raspberry Pi OS Lite 64-bit card was
flashed with `pi_smoke_test_flash.py`, configured for hostname `pi-host`,
account `htm` and key-only SSH using the key pair in `setups/.secrets/`.
It booted, and phase 2 logged in over SSH. Getting there took several
corrections, listed below: the first-boot mechanism changed (cloud-init,
not `custom.toml`), Windows blocks writing a partition table before the
data, sshd did not start from `user-data` alone, and the card looked faulty
on one reader but was fine on another.

### What was built

- `pi_smoke_test_flash.py` (this directory), Linux and Windows:
  auto-detects the SD card (refuses to guess; re-checks the disk is not a
  system/boot disk and is in the SD-card size window right before every
  destructive step), prints a device identity table (the `USED%` column is
  a warning: a card with data on it shows a non-zero value), asks for
  confirmation, writes the image, then writes the cloud-init files to the
  boot partition. Windows: clears the partition table and writes
  `\\.\PhysicalDriveN` with Python's `lzma`; needs an Administrator
  terminal. Linux: `xzcat | dd`.
- Flags: `--device`, `--image`, `--confirm-device <path>` (non-interactive
  confirmation, exact match only), `--no-wifi`, `--wifi-from-env` (Wi-Fi
  from `HOTSPOT_NAME`, `HOTSPOT_PASSWORD` and optional `HOTSPOT_COUNTRY` in
  the gitignored `setups/.secrets/.env`; the values are never printed),
  `--boot-dir <drive>` (no flash: only (re)write the cloud-init files onto
  an already-flashed card, with a new `instance_id`; combines with
  `--wifi-from-env`), and two experiment switches `--no-ssh-file` and
  `--no-enable-ssh`.
- Files written to the boot partition: `user-data` (hostname `pi-host`, user
  `htm`, public key from `setups/.secrets/id_ed25519.pub`, password login
  locked, `ssh_pwauth: false`, `enable_ssh: true`), `network-config`
  (Ethernet `eth0`: `dhcp4: true`, `optional: true`; plus `wlan0` if Wi-Fi
  is asked for), and an empty `ssh` file. The legacy `custom.toml` and the
  `init=` boot parameter are not used or are removed.
- Image: Raspberry Pi OS Lite 64-bit (Debian trixie), release 2026-09-15,
  541,414,936 bytes, SHA-256 `cdf4f3bf…ee627e5`, equal to the checksum
  published beside it; downloaded with `curl` to a folder outside the repo.
- `.gitignore` entries: `setups/.secrets/` (key pair and `.env`), the
  image, the phase 2 known-hosts file.

### What went wrong, and what fixed it

1. **Linux, 2026-09-28: the write failed with a hardware medium error.**
   `dd` and then `f3write` failed at different sectors with kernel Medium
   Errors. On Windows, with a different reader, the same card took a full
   2,920 MiB write and booted the Pi, so the Linux reader is the more
   likely culprit (inferred; the first reader was never tested with another
   card). One Windows attempt also showed the reader as "No Media" until the
   card was re-seated.
2. **`custom.toml` was ignored.** This release configures first boot with
   cloud-init (`user-data`, `network-config`, `meta-data`) and no longer reads
   `custom.toml`. A card configured that way booted as an unconfigured
   `raspberrypi` with SSH off. Source:
   https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/ .
   A card that has already booted needs a new `instance_id` in `meta-data`
   for cloud-init to apply edited files; `--boot-dir` does that.
3. **sshd did not start from `enable_ssh: true` alone.** A known problem on
   Lite (https://github.com/raspberrypi/rpi-imager/issues/1612, workaround:
   an empty `ssh` file on the boot partition). The `ssh` file was added and
   was gone from the boot partition after the Pi's first boot, so the Pi did
   consume it. Whether `enable_ssh` alone would have sufficed on a fresh
   flash is not established (every working card had both).
4. **Windows blocks direct writes into the sectors of a mounted volume**
   ([Microsoft: restricted direct disk access](https://learn.microsoft.com/en-us/previous-versions/windows/hardware/design/dn653576(v=vs.85))).
   The first Windows write put the partition table in the first chunk;
   Windows mounted the new boot partition (and opened its "format this
   disk" dialog) and the next write failed with `[Errno 9] Bad file
   descriptor`. Fix: write everything except the first 1 MiB first, and the
   first 1 MiB (partition table) last. Logic tested offline against a temp
   file with four image sizes; the real writes then succeeded. The "format"
   dialogs Windows shows for the Linux partition are to be cancelled.
5. **A second spare card turned out to hold personal files** (about 16 GB of
   photos and videos). It was not flashed until the owner had emptied it. The
   identity table's `USED%` column and a read-only look at the card first are
   the check.

### Notes for whoever picks this up

- A Wi-Fi password, whether typed or read from `.env`, is **written in plain
  text to `network-config` on the card**; the script does not save it
  anywhere else.
- The key in `setups/.secrets/` matched its public file (checked by
  deriving the public key from the private one).
- Reading the Pi's Linux root partition from Windows: `wsl --mount` does not
  support SD card readers (Microsoft's documentation); usbipd-win would be
  needed. Not set up.
- Nothing is committed from the 2026-10-04 correction pass.

## Phase 2 — SSH check

**Summary: done (2026-10-04), with an important correction.** The check
script found the Pi by mDNS and logged in as `htm` with the
`setups/.secrets` key, first over a plain direct cable and later over the
cable with Windows Internet Connection Sharing and over a phone hotspot:

```
hostname: pi-host
kernel:   Linux pi-host 6.18.50+rpt-rpi-v8 ... aarch64 GNU/Linux
os:       Debian GNU/Linux 13 (trixie)
disk (/): /dev/mmcblk0p2  117G  3.9G  109G   4% /
```

The root partition had grown to the whole card, and the Ethernet address
was a Raspberry Pi vendor address. **A plain direct cable (no DHCP server)
does not stay up:** the Pi becomes unreachable about 3 minutes after every
boot. Cause, measured below. With Windows sharing on the laptop's Ethernet
adapter (a DHCP server for the Pi) the cable link was stable, and the Pi
also joined a phone hotspot over Wi-Fi.

### What was built

- `pi_smoke_test_ssh_check.py` (this directory), Linux and Windows. Discovery
  in order: `--host`; the mDNS names `pi-host.local` and `raspberrypi.local`
  (IPv4 or IPv6, with the interface scope an `fe80::` address needs); the
  ARP table filtered to Raspberry Pi vendor prefixes; optionally `--sweep`
  (port-22 probe of the local /24). Then SSH with a task-local known-hosts
  file, no user ssh config, `BatchMode`, bounded retries (`--wait`, default
  180 s), then harmless read-only commands. On Windows it first restricts
  the key file with `icacls`. Success requires hostname `pi-host`. A first
  "Permission denied" is retried: sshd can be up before cloud-init has
  installed the key.

### The dropout, its cause, and the fix (the correction)

- **Observed:** with the Pi cabled straight to the laptop, every boot of
  two different cards ended with the Pi silent about 3 minutes in, the
  link still up (`carrier=1` on the Pi). Earlier "it is still doing first
  boot" explanations were wrong: the Pi's early reachability was just
  the window before the failure.
- **Cause, from the Pi's own NetworkManager log:** the profile `netplan-eth0`
  asks for DHCP (45 s timeout). With no DHCP server the activation fails
  every 45 s (`ip-config-unavailable`; the Pi's IPv6 and mDNS address is
  withdrawn and re-added about a second later each time). The profile has
  `ipv6.method ignore`, so no address family succeeds. The SSH session died
  about when a fourth failure was due (4 x 45 s, about 3 minutes after
  activation began), both times; that NetworkManager then stops retrying and
  leaves `eth0` down is inferred from the timing, not seen in a log (the
  capture ended with the connection).
- **Confirmed by changing it:** setting `ipv6.method link-local` on the
  running profile (runtime only, reverts on reboot) kept NetworkManager in
  `connected` for the full 8.5-minute watch, past the old failure point.
- **Netplan's `link-local: [ipv4, ipv6]` does nothing here.** A freshly
  flashed card with the line produced the same NetworkManager profile
  (`ipv6.method ignore`, `ipv4.link-local` default) and dropped the same
  way. It was removed from the script.
- **Fix used: Windows Internet Connection Sharing** on the laptop's
  Ethernet adapter (Wi-Fi adapter Properties, Sharing tab; the dropdown is
  absent when only one other adapter exists). The laptop's Ethernet then
  has `192.168.137.1/24` and answers DHCP and DNS; the Pi got
  `192.168.137.x`, a default route and DNS, reached the internet, and
  stayed `connected` for 96 consecutive 5 s heartbeats (8 minutes), with the
  default `dhcp4: true` config and no other change. Windows can drop
  sharing after a reboot, sleep or a change of Wi-Fi network (documented
  behavior, not seen here).
- **VPN:** with ProtonVPN connected on the laptop, the laptop's public IP
  changed but the Pi's did not: the Pi's traffic bypasses the VPN tunnel
  (sharing is on the Wi-Fi adapter). The Pi stayed reachable and online.
- **Phone hotspot (Wi-Fi):** the card flashed with `--wifi-from-env`
  joined the hotspot (`wlan0` got a `10.x` address), reached the internet
  through `wlan0` alone (its public IP was the phone's carrier address,
  different from the laptop's), and with both `eth0` (sharing) and `wlan0`
  up all 72 heartbeats over 6 minutes showed both `connected`. With both up,
  the default route preferred `eth0` (metric 100) over `wlan0` (600). The
  maintainer wants the hotspot preferred, so the flash script now sets
  `wlan0`'s route metric to 50 through netplan `dhcp4-overrides` (documented
  for the NetworkManager renderer); this is not yet tested on the Pi.

### Hiccups

- **IPv6 was disabled on every adapter of the laptop.** The first time it
  was seen, the maintainer reported the VPN as not connected; later, with
  ProtonVPN connected, IPv6 was again off on the physical adapters and on
  only on the VPN adapter. That the VPN client causes it is therefore **not
  established** (it might leave the setting changed after a disconnect, or
  something else changed it). The maintainer had not enabled IPv6 support in
  the Proton app. The Pi tests with sharing and the hotspot used IPv4 only
  (the Pi never had a global IPv6 address). With IPv6 off, discovery of a
  Pi on a plain direct cable (IPv6 only) fails. Re-enabled by the
  maintainer with `Enable-NetAdapterBinding -Name "Ethernet" -ComponentID
  ms_tcpip6`.
- **Windows' mDNS cache returns an address after the Pi stops answering**,
  so a successful name lookup is not proof the Pi is up; ping or the SSH
  result is.
- **The Pi's clock is wrong for a few seconds after boot** (corrected by
  network time once the network is up), so an HTTPS request in that window
  fails with "certificate is not yet valid".
- **The Pi's journal is volatile** (`Storage=volatile`, although
  `/var/log/journal` exists): the previous boot's log is lost on reboot, so
  a dropout has to be watched live.
- A name lookup can return an old address if the Pi's address changed: the
  stock first boot used a stable-privacy IPv6 address, the netplan-configured
  one used an EUI-64 address derived from its MAC. A new OS install gets
  new SSH host keys, so the task-local known-hosts file must be deleted.
- `iw` is not installed on the Pi, so the Wi-Fi regulatory domain
  (set to `JP` through `network-config`) and the link frequency were not
  read back.

### Not established

- Whether `enable_ssh` alone, or the `ssh` file alone, starts sshd on a fresh
  flash (every working card had both).
- Behavior behind a router/DHCP network: not tested, and not the intended
  deployment (no router for this host/Pi combination).
- Whether the regulatory domain took effect on the Pi, and whether a
  hotspot on channels 12 or 13 would be joined.
- Whether sharing survives a laptop reboot or sleep.
- Whether Proton's client can share its own tunnel adapter, and a VPN
  running on the Pi itself: neither tried.
- Docker, Tailscale and the egress proxy on the Pi: not installed at the time
  (Docker and Tailscale since: see the 2026-10-11 follow-up at the end; the egress
  proxy is not built).

## Follow-up — first-boot provisioning script (2026-10-05 to 2026-10-07)

**Summary: written and tested offline; later tested on the Pi (see the follow-up "first boots, retry, credential stick,
tunnel at boot" below).**
`setups/pi-provision/pi-firstboot.sh` is embedded in the card's `user-data` by
`pi_smoke_test_flash.py --provision-script` (cloud-init `write_files`, started
with `systemd-run` so it cannot block boot). It was modelled on the sandbox
repo's Dockerfile/entrypoint habits: preflight checks that refuse an untested
system (root, aarch64, Debian 13), one function per module with one result
line each, an active check after each install, bounded waits, and a verified
scrub of a credential. Modules: `wireguard-tools` (installed with
`--no-install-recommends`, then `wg --version` and a kernel-module dry run),
and replacing the Wi-Fi password in `/boot/firmware/network-config` once
cloud-init is done (only if the root-only netplan copy exists), then checking
it. It deliberately carries no VPN config or key. The flash script also gained
`--wifi-from-env` (hotspot from `setups/.secrets/.env`), a Wi-Fi route metric of
50 so the hotspot is preferred over the cable, and `--boot-dir` that can take
both. Offline: `bash -n` and 14 checks of the scrub and the root check on fake
files pass. At that point card 1 had been flashed and rewritten with the final config and
script, and had not been booted. The preflight's OS and architecture checks and
the whole boot path can only be tested on the Pi.

## Follow-up — Proton VPN on the headless Pi (2026-10-04)

**Summary: works, through WireGuard, not through Proton's own app.** A
WireGuard config for a Japan server, generated in the Proton account, was
installed on the Pi and brought up by hand: the handshake completed, the
Pi's public IP changed to a Japanese address, IPv4 and IPv6 traffic went
through the tunnel, and the SSH session survived. It was a one-off test:
the tunnel is not enabled at boot, DNS through the tunnel was not tested,
and the tunnel is down again.

### Why WireGuard

- Proton's official Linux CLI lists "Headless setups are not currently
  supported" as a limitation and its README does not mention ARM or the
  Raspberry Pi ([ProtonVPN/proton-vpn-cli](https://github.com/ProtonVPN/proton-vpn-cli)).
- The supported manual route is a WireGuard config from the account
  (Downloads, WireGuard configuration; platform GNU/Linux; one server per
  file; the file name must be under 15 characters) placed in
  `/etc/wireguard/` and started with `wg-quick`
  ([Proton's guide](https://protonvpn.com/support/wireguard-linux)).

### What was checked and done

- Pi prerequisites (read-only): kernel `6.18.50+rpt-rpi-v8` aarch64 with
  `CONFIG_WIREGUARD=m` and the module file present, `/dev/net/tun`,
  `nft` and `sysctl` present under `/usr/sbin`, `iptables` and `resolvconf`
  absent. `wg-quick` uses `nft` when it exists, so no iptables was needed.
  Note: the `htm` user's PATH lacks `/usr/sbin`, so `command -v` and
  `modinfo` run as `htm` wrongly reported tools as missing; check with `sudo`.
- Installed with `apt-get install --no-install-recommends wireguard-tools`
  (1.0.20210914-3, arm64). `--no-install-recommends` avoids pulling
  `resolvconf`, which could fight NetworkManager over `/etc/resolv.conf`.
- The config in `setups/.secrets/wg-JP-154.conf` (gitignored; it holds the
  WireGuard private key, never printed) has addresses `10.2.0.2/32` and an
  IPv6 address, `AllowedIPs = 0.0.0.0/0, ::/0`, one `Endpoint`, and a
  25 s keepalive. The Pi's copy had the `DNS =` line removed, was sent with
  `scp`, installed with `install -m 600 -o root -g root`, and the laptop's
  temporary copy and the Pi's `/tmp` copy were deleted. The laptop's copy
  had inherited permissions readable by other local accounts and was
  restricted to the current user with `icacls` (as was `.env`).
- Test with a safety net: a `systemd-run --on-active=150` timer was set to
  run `wg-quick down` by itself before the tunnel came up.

### Result

| Check | Result |
|---|---|
| `wg-quick up` | exit 0, handshake 6 s old, bytes flowing both ways |
| Route to `1.1.1.1` | through `wg-JP-154` |
| Pi's public IP, tunnel up | a Japanese Proton address (lookup service: `JP`) |
| Pi's public IP before and after | the laptop's connection address |
| Ping `1.1.1.1` | 0% loss, about 4 ms |
| IPv6 | a public IPv6 address was reachable through the tunnel |
| SSH session | stayed up (wg-quick keeps connected-subnet routes via `ip rule table main suppress_prefixlength 0`) |

### Not established

- **DNS through the tunnel.** With the `DNS` line removed the Pi's lookups
  still go to the laptop's resolver, outside the tunnel (a DNS leak).
  Handling it needs `resolvconf`/`openresolv` or an equivalent, tested
  separately.
- Starting the tunnel at boot (`wg-quick@`), behavior when the tunnel
  drops (no kill switch was set up), and the interplay with Tailscale.
- Behavior over the hotspot path; the test ran with the cable path as the
  Pi's default route.
- Whether Proton's other config options (not read) matter for this use.

## Follow-up — first boots, retry, credential stick, tunnel at boot (2026-10-07 to 2026-10-11)

**Summary: all of it works on the Pi, tested with fresh flashes.** What changed
after the offline version:

- **First boots.** Card 1's first boot installed `wireguard-tools` but skipped the
  Wi-Fi scrub: `cloud-init status --wait` exits 2 on Pi OS's harmless "degraded
  done", which the script read as a timeout. Fixed (0 and 2 count as done). The
  log then showed the real `scrub:` line on fresh flashes.
- **Retry.** `pi-provision.service` replaces the one-shot `systemd-run`: retried
  every 5 minutes (at most 6 starts per hour) and again on every boot until the
  marker exists; a skipped scrub no longer writes it. Tested: a boot with no
  network finished once the cable came in; a forced-failure test of the tunnel
  unit's restart policy retried at 30 s spacing and recovered.
- **Credential stick.** A USB stick labelled `PIKEYS` (ext4, mounted by label with
  `nofail`) holds credentials; its `links.conf` maps folders to paths on the Pi
  (today `wireguard /etc/wireguard`). Moves existing files, idempotent, survives a
  reboot and a re-flash; a boot without it fails cleanly after 10 s.
- **Tunnel at boot with tunnel-only DNS.** `wg-quick@` is enabled; the config's
  `PostUp`/`PostDown` point NetworkManager at the tunnel resolver, and a
  dispatcher script re-applies it to devices that connect later (measured gap:
  `eth0` came up after the tunnel on a first boot and kept the laptop's DNS).
- **Laptop side.** Connection sharing stopped twice and had to be restarted;
  `setups/restart-sharing.bat` does it in one call. A leftover sharing setting on
  the old adapter made `EnableSharing` fail (`0x80040201`).
- **Wiping cards loses what is on their Linux partition**, which Windows cannot
  read: the hand-installed tunnel setup of 2026-10-04 was lost that way.

## Follow-up — Docker, Tailscale and the tailnet policy (2026-10-11)

**Summary: works, tested by hand on the Pi and then through the script on fresh
flashes of both cards; two failures on the way, both understood.** Configuration
is in `pi-technical.md` and the reasoning in `pi-rationale.md` (items 13 and 14);
this section holds only what was measured.

- **Method.** Before each install the baseline was recorded (tunnel handshake,
  resolver, public address, routes, nftables tables) and repeated afterwards. Each
  install was done by hand first, then moved into the script and run through its
  own install path on card 2 (about 3 minutes from power-on to done) and again on
  card 1 (the script's final text).
- **Docker.** Docker's signing key matched its published fingerprint. After the
  install the tunnel handshake stayed fresh, the resolver stayed on the tunnel's,
  and SSH was never interrupted. A container's public address equalled the host's
  (so container traffic leaves through the tunnel), and names resolved through the
  tunnel's resolver. `iptables` arrived as a dependency and the active backend was
  `iptables-nft`. (The first container test failed only because busybox's `wget`
  has no `-4`.)
- **Tailscale.** No fingerprint is published for its key, so the one seen was
  recorded and pinned (trust on first use). After the join the handshake, resolver
  and public address were unchanged. Its routing rules sit before WireGuard's and
  do not overlap; its own traffic bypasses the tunnel (its netcheck reported the
  home connection's address, relay Tokyo). The phone and the Pi answered each
  other's `tailscale ping` in 34 to 46 ms through the relay (no direct path).
- **Key expiry.** A node joined without a tag expires (2027-04-09). Tagging it
  afterwards in the console did not remove that (the console still said 6 months).
  A join with `--advertise-tags=tag:pi` on card 1 gave `KeyExpiry None`.
- **Policy.** Before the policy the Pi pinged the phone with 0% loss; after it,
  100% loss, with the Pi tagged and the phone's SSH attempts still reaching sshd (as
  `u0_a308`, then as `htm`; refused, no phone key exists yet).
- **Failure 1: the login link timed out.** `tailscale up` ends with
  `context canceled` after about 10 minutes and needs a new link.
- **Failure 2: ProtonVPN on the laptop cut the Pi off.** Card 1's first boot got
  through WireGuard and Docker, then the Pi had neither DNS nor internet: even
  packets marked to bypass the tunnel got nowhere, and the tunnel's handshake was 22
  minutes old. The laptop's own internet and sharing service were fine, but the
  ProtonVPN adapter held its default route (metric 0). The internet came back once
  the VPN was disconnected (cause inferred from the routes and the timing). During
  the outage the Tailscale module failed with a clear log line, and the retry service
  used up its 6 starts and stayed failed; `reset-failed` plus `start` finished the
  run (earlier modules reported "already installed", marker written).

### Not established

- SSH from the phone with a key, and the blocked ports from the phone live (the
  policy's saved `tests` block asserts them; not seen).
- Behavior when the tunnel drops (still no kill switch).
- Whether a re-flash can keep the Tailscale identity (it cannot today; linking the
  state onto the stick is undecided).
