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

**Only two locations are in scope for this task:**
1. This directory, `setups/pi-smoke-test/` (scripts, report, a
   task-local SSH keypair).
2. The SD card mount, `/media/htm/9C33-6BBD` — currently empty, already
   one of the few places this host session may touch without asking.

**Everything else needs explicit approval before being touched**, per
this host session's own boundary rule (`claude-code-and-local-agent-sandbox/AGENTS.md`,
"Where this session may touch") — this task doc calls out the specific
cases expected to come up, so they're recognized rather than worked
around:
- **`~/.ssh`** — do not read, write, or generate anything there. Generate
  a dedicated keypair *inside this task's own directory* instead (see
  "SSH key" below) and reference it with `ssh -i`.
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
allowed for this task. Naming pattern: `pi_smoke_test_<descriptor>.sh`.

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
   Pi OS Lite, 64-bit — smallest headless image, matches the
   general-purpose Docker-capable host `pi-rationale.md` describes, and
   is the default `rpi-imager` targets. If `rpi-imager` (CLI mode) is
   available or its install is approved, prefer it — it can do
   download + OS customization (hostname, SSH, keys) + flash in one
   tool, rather than hand-editing the boot partition. If it isn't
   available and installing it isn't approved in time, fall back to the
   manual path: download the image, `xz`-decompress, write with `dd`,
   then mount the flashed boot partition and drop in `ssh` (empty file,
   enables sshd) and `userconf.txt` (or `firstrun.sh`) for the account
   and key. Document whichever path was actually used in the report.
2. **Hostname:** `pi-host` (maintainer confirmed 2026-09-28 default; not a
   project-specific name — this repo's own convention against
   deployment-specific naming in committed material applies here too).
3. **Account:** username `htm` (maintainer, 2026-09-28). Key-only auth,
   no password set (maintainer confirmed the key-only default).
4. **SSH key:** generate a dedicated ed25519 keypair inside this
   directory (e.g. `pi_smoke_test_key` / `pi_smoke_test_key.pub` — not
   `~/.ssh`, see "Scope" above), bake the public key into the `htm`
   account's SSH config, and add the private key to `.gitignore` before
   anything is committed. Note in the report that it's a throwaway
   smoke-test key, not the eventual Pi host's real credential.
5. **Networking: Wi-Fi (changed 2026-09-28, was Ethernet/DHCP-only).**
   The maintainer wants to share a mobile hotspot rather than run a LAN
   cable, and may need this for more than one network/region over time.
   Nothing about the network (SSID, region/country code) or the
   maintainer's own location/device is hardcoded anywhere, including in
   this doc — `pi_smoke_test_flash.py` prompts for the SSID and the
   regulatory country code at runtime each run (country defaults to a
   generic `US` if left blank, never assumed from context), and the
   password is prompted via `getpass` and never written to any file. See
   `pi_smoke_test_flash.py`'s own comments for why (this repo's rule
   against committing secrets *or* personal/location-identifying details
   — corrected 2026-09-28 after an earlier version of this section named
   the maintainer's specific device and travel plan).
6. **Flash**, per the "Safety" section above, then safely unmount/eject
   the card so it's ready to be physically moved.
7. **Stop and report** (see "Reporting format" below), then wait — don't
   start phase 2 until the maintainer confirms the Pi is powered on and
   connected.

### Phase 2 — SSH check (after the maintainer confirms the Pi is up)

1. **Find the Pi on the local network.** Try, in order, whatever's
   already available without a new install: `ping pi-host.local` /
   `raspberrypi.local` (mDNS, if avahi tooling is present), then an ARP
   table read for a Raspberry Pi Foundation MAC prefix. Anything needing
   a new package (e.g. `nmap`, `arp-scan`) goes through the "Working
   autonomously" / host-package-install approval path first.
2. **SSH in** using the task-local key from phase 1
   (`ssh -i pi_smoke_test_key ...`), confirm it lands on the actual Pi
   (hostname/`uname -a`), and run a couple of harmless read-only checks
   (disk space, OS version) as evidence, not as new scope.
3. **Bounded runtime, no indefinite hangs:** any discovery or connection
   script needs an iteration cap / timeout with a clear failure message
   (this repo's — and the sandbox repo's — standing rule on scripts that
   wait on another process), not an open-ended retry loop.
4. **Append the phase 2 section to the report** and stop — closing the
   open item in `pi-rationale.md`/`pi-technical.md` is a separate later
   step that will use this task's findings, same as the GPU smoke test's
   own convention (don't edit those files from this task).

## Deliverables (all in this same `pi-smoke-test/` directory)

- `task.md` — this file.
- `pi_smoke_test_flash.sh` — phase 1: download/customize/flash helper.
- `pi_smoke_test_ssh_check.sh` — phase 2: discovery + SSH check helper,
  bounded runtime.
- `pi_smoke_test_key` / `pi_smoke_test_key.pub` — task-local throwaway
  keypair; the private half must be gitignored before any commit.
- `pi-smoke-test-report.md` — one section per phase, each following
  `setups/report-format.md`'s summary-then-subsections structure.

Don't edit `pi-rationale.md` or `pi-technical.md` from this task — noting
findings there is a separate later step.

## Reporting format

Each phase's entry in `pi-smoke-test-report.md` follows
`setups/report-format.md`'s shared convention (summary at top, details in
subsections below).
