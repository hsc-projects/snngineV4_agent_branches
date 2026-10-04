# Pi smoke test — report

Structure per `setups/report-format.md`: one top-level section per phase,
each with a short summary followed by detail subsections.

## Phase 1 — write, configure, and flash the image

**Summary: done (2026-10-04), from a Windows laptop, after a failed first
attempt on Linux (2026-09-28).** A Raspberry Pi OS Lite 64-bit card was
flashed with `pi_smoke_test_flash.py`, configured for hostname `pi-host`,
account `htm` and key-only SSH using the key pair in `setups/.secrets/`.
It booted and phase 2 logged in over SSH. Getting there took four
corrections, all listed below: the first-boot mechanism changed
(cloud-init, not `custom.toml`), Windows blocks writing a partition table
before the data, sshd did not start from `user-data` alone, and the card
looked faulty on one reader but was fine on another.

### What was built

- `pi_smoke_test_flash.py` (this directory), Linux and Windows:
  auto-detects the SD card (refuses to guess; re-checks the disk is not a
  system/boot disk and is in the SD-card size window right before every
  destructive step), prints a device identity table, asks for confirmation,
  writes the image, then writes the cloud-init files to the boot partition.
  Windows: clears the partition table, writes `\\.\PhysicalDriveN` with
  Python's `lzma`; needs an Administrator terminal. Linux: `xzcat | dd`.
  Flags: `--device`, `--image`, `--confirm-device <path>` (non-interactive
  confirmation, exact match only), `--no-wifi`, `--boot-dir <drive>` (no
  flash: only (re)write the cloud-init files onto an already-flashed card,
  with a new `instance_id`).
- Files written to the boot partition: `user-data` (hostname `pi-host`, user
  `htm`, public key from `setups/.secrets/id_ed25519.pub`, password login
  locked, `ssh_pwauth: false`, `enable_ssh: true`), `network-config`
  (Ethernet `eth0`, DHCP, `link-local: [ipv4, ipv6]`, optional; Wi-Fi only
  if asked), and an empty `ssh` file. The legacy `custom.toml` and the
  `init=` boot parameter are not used or are removed.
- Image: Raspberry Pi OS Lite 64-bit (Debian trixie), release 2026-09-15,
  541,414,936 bytes, SHA-256 `cdf4f3bf…ee627e5`, equal to the checksum
  published beside it; downloaded with `curl` to a folder outside the repo.
- `.gitignore` entries: `setups/.secrets/`, the image, the phase 2
  known-hosts file.

### What went wrong, and what fixed it

1. **Linux, 2026-09-28: the write failed with a hardware medium error.**
   `dd` and then `f3write` failed at different sectors with kernel Medium
   Errors. On Windows, with a different reader, the same card took a full
   2,920 MiB write and booted the Pi, so the Linux reader is the more likely culprit (inferred; the
   first reader was never tested with another card). One Windows attempt
   also showed the reader as "No Media" until the card was re-seated.
2. **`custom.toml` was ignored.** This release configures first boot with
   cloud-init (`user-data`, `network-config`, `meta-data`) and no longer reads
   `custom.toml`. A card configured that way booted as an unconfigured
   `raspberrypi` with SSH off. Source:
   https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/ .
   A card that had already booted needs a new `instance_id` in `meta-data`
   for cloud-init to apply edited files; `--boot-dir` does that.
3. **sshd did not start from `enable_ssh: true` alone.** A known problem on
   Lite (https://github.com/raspberrypi/rpi-imager/issues/1612, workaround:
   an empty `ssh` file on the boot partition). The `ssh` file was added. The
   card that finally worked had both `enable_ssh` and the `ssh` file and was
   freshly flashed, so which of the two (or the fresh first boot) made the
   difference is not established.
4. **Windows blocks direct writes into the sectors of a mounted volume**
   ([Microsoft: restricted direct disk access](https://learn.microsoft.com/en-us/previous-versions/windows/hardware/design/dn653576(v=vs.85))).
   The first Windows write put the partition table in the first chunk;
   Windows mounted the new boot partition (and opened its "format this
   disk" dialog) and the next write failed with `[Errno 9] Bad file
   descriptor`. Fix: write everything except the first 1 MiB first, and the
   first 1 MiB (partition table) last. Logic tested offline against a temp
   file with four image sizes; the real write then succeeded (2,920 MiB).
   The "format" dialogs Windows shows for the Linux partition are to be
   cancelled; nothing needs formatting.

### Notes for whoever picks this up

- The Wi-Fi password, if given, is **written in plain text to
  `network-config` on the card**; the script does not save it anywhere else.
- The key in `setups/.secrets/` matched its public file (checked by
  deriving the public key from the private one).
- `pi-rationale.md` and `pi-technical.md` are intentionally not edited here
  (task rule); recording the findings there is a separate step.
- Nothing is committed.

## Phase 2 — SSH check

**Summary: done (2026-10-04).** `pi_smoke_test_ssh_check.py` found the Pi by
mDNS (`pi-host.local`, an IPv6 link-local address) and logged in as `htm`
with the `setups/.secrets` key on the first SSH attempt, over a LAN cable
connected straight to the laptop, with no router or DHCP server:

```
hostname: pi-host
kernel:   Linux pi-host 6.18.50+rpt-rpi-v8 ... aarch64 GNU/Linux
os:       Debian GNU/Linux 13 (trixie)
disk (/): /dev/mmcblk0p2  117G  3.9G  109G   4% /
```

The root partition had grown to the whole card (117 G), so first-boot
expansion finished. The Pi's Ethernet address was a Raspberry Pi vendor
address (`D8-3A-DD-…`).

### What was built

- `pi_smoke_test_ssh_check.py` (this directory), Linux and Windows. Discovery
  in order: `--host`; the mDNS names `pi-host.local` and `raspberrypi.local`
  (IPv4 or IPv6, with the interface scope an `fe80::` address needs); the
  ARP table filtered to Raspberry Pi vendor prefixes; optionally `--sweep`
  (port-22 probe of the local /24). Then SSH with a task-local known-hosts
  file, no user ssh config, `BatchMode`, bounded retries (`--wait`, default
  180 s), then harmless read-only commands. On Windows it first restricts
  the key file with `icacls`. Success requires hostname `pi-host`.

### Hiccups

- **IPv6 was disabled on every adapter of the laptop**, including the
  Ethernet one the Pi was plugged into. With IPv6 off neither mDNS nor the
  Pi's link-local address can work on a direct cable. It was re-enabled by
  the maintainer (`Enable-NetAdapterBinding -Name "Ethernet" -ComponentID
  ms_tcpip6`). The cause of it being off was not established; a VPN client
  was installed (not connected when checked).
- **Early silence was the first boot, not a fault.** For several minutes
  after power-on the Pi's green LED blinked, the Pi did not answer pings,
  and SSH was refused or timed out; it became reachable only after the LED
  went dark. Several rounds of earlier checks were run too early and were
  misread as faults. Wait until the LED is dark before judging.
- **A first "Permission denied (publickey)" can be transient.** sshd can be
  up before cloud-init has installed the key; the script keeps retrying
  instead of stopping at the first denial.
- **Windows' mDNS cache returns an address after the Pi stops answering**,
  so a successful name lookup is not proof the Pi is up; ping or the SSH
  result is.
- A name lookup can return an old address if the Pi's address changed:
  the stock first boot used a stable-privacy IPv6 address, the netplan-
  configured one used an EUI-64 address derived from its MAC.

### Not established

- Whether `link-local: [ipv4, ipv6]` in `network-config` mattered: the card
  that worked was flashed before it was added to the script. It stays as the
  documented option for a direct cable
  ([netplan docs](https://netplan.readthedocs.io/en/stable/netplan-yaml/);
  NetworkManager's lack of an automatic IPv4 link-local fallback:
  https://forums.raspberrypi.com/viewtopic.php?t=388100).
- Which Raspberry Pi OS first-boot step takes the several minutes.
- Behavior behind a router/DHCP network and over Wi-Fi: not tested here.
