# Task: Pi host flash + SSH smoke test

## Order note (2026-09-28)

`pi-rationale.md`'s open-items list puts research into existing
Tailscale-gateway/homelab patterns (item 0) ahead of any hardware/OS
commitment. The maintainer chose to run this narrow, hands-on smoke test
first instead: write/configure an OS image, flash the SD card, then check
SSH once the Pi is booted and connected. This task doesn't cancel that
ordering note — the broader research and the real OS decision (item 2)
still need doing — it just runs one concrete check ahead of it. The OS
choice made below is scoped to this smoke test only, not a final answer to
item 2.

## Scope and file/command boundary

**Only these locations are in scope for this task:**
1. This directory, `setups/pi-smoke-test/` (scripts, report).
2. The SD card: on Linux the mount `/media/htm/9C33-6BBD`, on Windows the
   physical disk the flash script detects and the maintainer confirms.
3. `setups/.secrets/`, read-only: the SSH key pair (`id_ed25519`,
   `id_ed25519.pub`) the Pi is configured to trust. Gitignored; never
   committed, never printed.

**Everything else needs explicit approval before being touched**, per
this host session's own boundary rule (`claude-code-and-local-agent-sandbox/AGENTS.md`,
"Where this session may touch") — this task doc calls out the specific
cases expected to come up, so they're recognized rather than worked
around:
- **`~/.ssh`** — do not read, write, or generate anything there. Use the
  key pair in `setups/.secrets/` instead (see "SSH key" below) and
  reference it with `ssh -i`; phase 2 also keeps its own known-hosts file
  in this directory.
- **Installing host packages** (`rpi-imager` via apt, `arp-scan`,
  anything else not already on this machine) is a system-wide change —
  propose the exact package/command in the report and wait for the
  maintainer's go-ahead before running it, same as any other host
  package install.
- **Any block device other than the confirmed SD card** — see "Safety"
  below.
- **Downloading the OS image itself** likely exceeds what the
  containerized fetch tool can carry (multi-hundred-MB to multi-GB, same
  situation as the local-model `.gguf` downloads recorded in the sandbox
  repo's `docs/design/status.md`). Propose a host-side `wget`/`curl` for
  this one download and wait for the maintainer's explicit go-ahead
  before running it — don't fall back to it unprompted.
- **RunPod, credentials, or any cloud resource** — out of scope entirely,
  same as the GPU smoke test's own scope line.

## Safety: confirm the target block device before writing anything

Flashing writes raw bytes to a block device. Writing to the wrong one
can destroy data on the host's own disks. Before any `dd`/`rpi-imager`
write:
- Resolve `/media/htm/9C33-6BBD`'s actual backing device (e.g. via
  `lsblk`/`findmnt`), and confirm its size is SD-card-sized (a few GB to
  ~256 GB), not the host's main drive.
- Never pass a bare device path to a flashing command without having
  printed and visually confirmed it first in the same helper script or
  session — no guessing, no reusing a device path from memory across
  runs (a re-plugged card can enumerate under a different `/dev/sdX`).
- If anything about device identification is ambiguous, stop and ask
  rather than proceeding on a best guess.

## Working autonomously

Proactively look for anything blocking end-to-end work (missing tools,
permission prompts, sandbox-boundary questions) and propose the exact
fix in `pi-smoke-test-report.md` as soon as it's found, then keep working
on whatever doesn't depend on it while that's pending — same convention
as the GPU smoke test.

## Helper scripts are fine

Write helper scripts freely in this directory to reduce manual/repeated
steps (image download+customize+flash, SSH discovery+check) — explicitly
allowed for this task. Naming pattern: `pi_smoke_test_<descriptor>.py` (or `.sh`).

## Goal — two phases

Unlike the GPU smoke test, phase 2 does **not** start immediately after
phase 1 — it depends on a real-world action only the maintainer can do
(physically move the card to the Pi, power it, connect it to the
network). Phase 1 ends with a report and an explicit stop; phase 2 starts
only once the maintainer confirms the Pi is booted and reachable on the
network. Don't poll for that in a loop — wait for the maintainer to say
so, the same way any other turn-taking works.

### Phase 1 — write, configure, and flash the image

1. **OS pick (scoped to this task, see "Order note" above):** Raspberry
   Pi OS Lite, 64-bit (Debian trixie, release of 2026-09-15) — smallest
   headless image, matches the general-purpose Docker-capable host
   `pi-rationale.md` describes. **First-boot configuration uses
   cloud-init**: this release ships `user-data`, `network-config` and
   `meta-data` on the boot partition and no longer reads `custom.toml`
   (found the hard way: a card configured that way booted as an
   unconfigured `raspberrypi` with SSH off). Source:
   https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/.
   `rpi-imager --cli` only does a raw write plus checksum, with no
   customization flags, so the flash script writes the image itself
   (Python `lzma` on Windows, `xzcat | dd` on Linux) and then edits the
   boot partition. The image is verified against the SHA-256 published
   beside it. Document whichever path was actually used in the report.
2. **Hostname:** `pi-host` (maintainer confirmed 2026-09-28 default; not a
   project-specific name — this repo's own convention against
   deployment-specific naming in committed material applies here too).
3. **Account:** username `htm` (maintainer, 2026-09-28). Key-only auth,
   no password set (maintainer confirmed the key-only default).
4. **SSH key:** the maintainer's key pair in `setups/.secrets/`
   (`id_ed25519` / `id_ed25519.pub`, gitignored, not `~/.ssh`). The flash
   script bakes the public key into the `htm` account via `user-data` and
   refuses to run if the `.pub` is missing — it never generates a key.
   (An earlier version of this task generated a throwaway key in this
   directory; that is no longer done.)
5. **Networking.** `network-config` always enables Ethernet (`eth0`,
   `dhcp4: true`, optional). **A cable straight to the laptop needs a DHCP
   source**, or NetworkManager's DHCP fails every 45 s and the Pi goes
   silent about 3 minutes after every boot (measured; netplan's
   `link-local` option does not fix it). Use **Windows Internet Connection
   Sharing** on the laptop's Ethernet adapter (Wi-Fi adapter Properties,
   Sharing tab), which also gives the Pi internet through the laptop. **Wi-Fi is
   optional**, decided by an explicit `y`/`n` question in the flash script
   (no default), or non-interactively with `--wifi-from-env` (the hotspot
   name and password from `HOTSPOT_NAME`, `HOTSPOT_PASSWORD` and optional
   `HOTSPOT_COUNTRY` in the gitignored `setups/.secrets/.env`; never
   printed). The regulatory country code defaults to a generic `US` and
   should be the country the Pi is used in; nothing about the network or
   the maintainer's location/device is hardcoded in any committed file,
   including this doc. A Wi-Fi password is not saved by the script but
   **is written in plain text to `network-config` on the card**.
6. **Flash**, per the "Safety" section above, then safely eject the card
   so it's ready to be physically moved. On Windows this needs an
   Administrator terminal: the script clears the card's partition table,
   writes `\\.\PhysicalDriveN` directly, and re-checks that the disk is
   not a system/boot disk and is within the SD-card size window right
   before every destructive step. Windows blocks writes into the sectors
   of a mounted volume, so the script writes the first 1 MiB (partition
   table) **last**; writing it first makes Windows mount the new partition
   mid-write and the next write fails with `Bad file descriptor`. The
   "format this disk" dialogs Windows shows are to be cancelled.
   `--confirm-device <path>`, `--no-wifi` and `--wifi-from-env` make the run
   non-interactive (an elevated run can then be launched with
   `Start-Process -Verb RunAs`, the maintainer accepting the UAC prompt;
   single-quote paths that contain spaces); `--boot-dir <drive>` skips the
   flash and writes only the cloud-init files (with a new `instance_id`,
   and Wi-Fi if `--wifi-from-env` is given) onto an already-flashed card.
   Check the card's contents (the identity table's `USED%`, or a read-only
   look) before flashing a card that is not known to be blank. The boot
   partition also gets an empty `ssh` file: `enable_ssh` in `user-data`
   alone did not start sshd on this image (known issue, rpi-imager #1612).
7. **Stop and report** (see "Reporting format" below), then wait — don't
   start phase 2 until the maintainer confirms the Pi is powered on and
   connected.

### Phase 2 — SSH check (after the maintainer confirms the Pi is up)

1. **Find the Pi on the local network.** Try, in order, whatever's
   already available without a new install: the mDNS names `pi-host.local`
   and `raspberrypi.local` (IPv4 or IPv6, including a link-local address
   with its interface scope), then the ARP table filtered to Raspberry Pi
   Foundation MAC prefixes, then optionally (`--sweep`) a port-22 probe of
   the local /24. `--host` skips discovery. Anything needing a new
   package (e.g. `nmap`, `arp-scan`) goes through the "Working
   autonomously" / host-package-install approval path first.
2. **SSH in** using the `setups/.secrets` key
   (`ssh -i setups/.secrets/id_ed25519 ...`, with a task-local
   known-hosts file and no user ssh config), confirm it lands on the
   actual Pi (hostname must be `pi-host`), and run a couple of harmless
   read-only checks (hostname, kernel, OS version, disk space) as
   evidence, not as new scope. On Windows the script first restricts the
   key file's ACL with `icacls`, which `ssh` requires. The Pi is usually
   reachable within about a minute of power-on. A "connection refused" or a
   first "Permission denied" early in boot can be normal (cloud-init enables
   SSH and installs the key late), and the script retries within its time
   limit. **A Pi on a plain cable with no DHCP source will go silent about
   3 minutes after boot** (see step 5): that is a fault of the setup, not
   "first boot still running". Prerequisites for a reliable run: Windows
   connection sharing on the laptop's Ethernet adapter, or Wi-Fi configured
   on the Pi; IPv6 was seen off on the laptop's physical adapters (also
   while ProtonVPN was connected; cause not established). A fresh OS
   install has new SSH host keys, so delete the
   task-local known-hosts file first.
3. **Bounded runtime, no indefinite hangs:** any discovery or connection
   script needs an iteration cap / timeout with a clear failure message
   (this repo's — and the sandbox repo's — standing rule on scripts that
   wait on another process), not an open-ended retry loop.
4. **Append the phase 2 section to the report** and stop. (Recording the
   findings in `pi-rationale.md`/`pi-technical.md` was done on
   2026-10-04 at the maintainer's request; the original convention was a
   separate later step.)

## Deliverables (all in this same `pi-smoke-test/` directory)

- `task.md` — this file.
- `pi_smoke_test_flash.py` — phase 1: flash + cloud-init customization
  helper (Linux and Windows).
- `pi_smoke_test_ssh_check.py` — phase 2: discovery + SSH check helper,
  bounded runtime (Linux and Windows).
- `../pi-provision/pi-firstboot.sh` — the first-boot script the flash script
  can embed (`--provision-script`); see the report's first-boot follow-up.
- The SSH key pair, the Wi-Fi `.env` and the Proton WireGuard config live in
  `setups/.secrets/` (gitignored), not in this directory.
- Current state and next steps for a new session: `../pi-handoff.md`.
- `pi-smoke-test-report.md` — one section per phase, each following
  `setups/report-format.md`'s summary-then-subsections structure.

## Reporting format

Each phase's entry in `pi-smoke-test-report.md` follows
`setups/report-format.md`'s shared convention (summary at top, details in
subsections below).
