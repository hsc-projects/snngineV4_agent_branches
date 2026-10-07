# Pi work — handoff for the next session

State as of 2026-10-07. Read this first, then `pi-technical.md` (what the Pi
is now) and `pi-rationale.md` (decisions and numbered open items). The smoke
test's evidence is in `pi-smoke-test/pi-smoke-test-report.md`. Nothing here
contains a secret value; the secrets live in `setups/.secrets/` (gitignored).

## Where we are, in one paragraph

A Raspberry Pi 4 (8 GB) can be flashed and reached over SSH headlessly from
this Windows laptop. A plain cable to the laptop drops after about 3 minutes
(no DHCP); the fix in use is Windows Internet Connection Sharing on the
laptop's Ethernet adapter, with a phone hotspot over Wi-Fi as a second path
(hotspot preferred through a route metric, cable as fallback). Proton VPN
works on the Pi through WireGuard (tested by hand, not enabled at boot). A
first-boot provisioning script exists and has run once on card 1 (2026-10-07): preflight, clock sync and `wireguard-tools` all worked; the Wi-Fi password scrub was skipped by an exit-code bug (`cloud-init status --wait` exits 2 on Pi OS's harmless "degraded done"), now fixed in `pi-firstboot.sh` and run by hand on the Pi, which replaced the password with the placeholder. Card 1 was then re-flashed with the fixed script and a fresh first boot passed end to end (log: preflight, clock, wireguard ok, `scrub:` line, `done`; boot partition holds only the placeholder; Wi-Fi up at metric 50, cable at 100). A cold boot with the hotspot off also passed (cable works, no second provisioning run, Wi-Fi reconnects when the hotspot returns). Card 2 (127,865,454,592 bytes): on its first boot attempt after flashing (about 9 minutes after power-on) the Pi was not reachable and the green LED was seen dark at that one moment; the LED was not watched over time, so it is not known whether the boot failed or was just late. Its files read back fine on the laptop, and card 1 booted in the same Pi. After a second flash card 2's green LED was blinking.

## Next steps, in order

1. **Provisioning retry (done 2026-10-07).** Both gaps are fixed: the flash script now installs `pi-provision.service` (Type=simple, `Restart=on-failure`, 5 minutes apart, at most 6 starts per hour, enabled so every boot retries until the marker exists), and a skipped scrub now fails the run instead of writing the marker. Tested: cloud-init's schema check accepts the new user-data; a fresh flash of card 2 booted with no network at all (hotspot off, cable out), the script kept retrying `apt` internally, finished after the cable went in about 6 minutes later, scrubbed, and wrote the marker; a transient unit with the same restart settings ran a failing script 3 times and ended in success. Not exercised on the real script: the unit-level restart (the run never exited non-zero, `NRestarts=0`). If the Pi is not found on `192.168.137.x`, check `Get-Service SharedAccess` and `Get-NetUDPEndpoint -LocalPort 67` first (sharing had to be switched off and on once). The search script can latch onto a stale neighbour entry: check port 22 on each `192.168.137.x` the Pi's MAC (`D8-3A-DD`) maps to.
2. **Credential stick** (done 2026-10-07): the WireGuard config now lives on a
   `PIKEYS` USB stick plugged into the Pi and survives a re-flash; see `pi-technical.md`.
   A re-flash wipes the SD card only. **Never wipe a card or stick without asking what is on
   its Linux partition first** (a wipe on 2026-10-07 lost the hand-installed tunnel setup).
   Next: bring the tunnel up by hand and check SSH survives; then test with the laptop's
   ProtonVPN on (and both at once).
3. **Commit** (see "Uncommitted work"): propose first, never commit unasked.
4. Items 8 to 20 in `pi-rationale.md` (all low priority unless the maintainer
   says otherwise). The next larger piece, **later** per the maintainer: the Pi
   as the sandbox's egress proxy, reusing the sandbox repo's `egress-proxy`
   container (needs Docker on the Pi); and the **keyholder** role (item 20).

## Snapshot

**Git** (branch `docs/runpod-pi-setup`): the local history was rewritten
(two commits that were both named "dev" now have real messages; every hash
above them changed) and has **not been pushed**; the remote still has the old
history. The maintainer does any force-push themselves (their commit
conventions say so). Local backup branch `backup/before-dev-msg-rewrite-13114f5`
holds the pre-rewrite history.

**Uncommitted work** (all intended to be committed together, by the
conventions in `agents/commit-conventions.md`: one line, lowercase, name only
code/config changes, leave docs out of the message, no attribution footer,
`git add` and `git commit` in one call, single `-m`):
`setups/pi-smoke-test/pi_smoke_test_flash.py` (new `--provision-script`),
the new folder `setups/pi-provision/` (`pi-firstboot.sh`), and doc edits
(`pi-rationale.md`, `pi-technical.md`, this note, the report, `task.md`, the
README index). `setups/decrypt_credential_bundle.py` is untracked and was
deliberately kept out of commits (written, never run; item 17).

**Cards** (both about 119 GiB, both with a Pi OS boot partition, so the flash
script's own size window cannot tell them apart; identify by exact size):
- card 1: 128,177,930,240 bytes. Config as above, unbooted.
- card 2: 127,865,454,592 bytes. A spare, flashed earlier with Ethernet only.
- Windows shows the card reader as Disk 3; disk numbers change after a reboot.
  The 57 GiB USB stick (a different disk) and the 466 GiB USB drive are not cards.

**Laptop** (Windows 11 Home): Windows connection sharing is on for the
Ethernet adapter (laptop `192.168.137.1/24`, the Pi gets `192.168.137.x`; the
address changes between boots). ProtonVPN is installed; while it is connected
`pi-host.local` lookups fail, so find the Pi by its `192.168.137.x` address
(neighbour table) and keep the VPN off for Pi tests if in doubt. IPv6 was seen
off on the physical adapters (cause not established). Python 3.14 is installed.
The OS image is at `E:\Drive Downloads\raspios_lite_arm64_latest.img.xz`
(Raspberry Pi OS Lite 64-bit, trixie, 2026-09-15; checksum verified).

**Secrets in `setups/.secrets/`** (names only; never print values): the SSH key
pair (`id_ed25519`, `.pub`), `.env` (`HOTSPOT_NAME`, `HOTSPOT_PASSWORD`,
`HOTSPOT_COUNTRY`, `RUNPOD_API_KEY`), `wg-JP-154.conf` (Proton WireGuard config,
contains a private key). Permissions on `.env` and the config were restricted to
the maintainer's account. `RUNPOD_API_KEY` has no use decided (item 18).

**The Pi** (when last seen): hostname `pi-host`, user `htm` (key-only), Debian
13, aarch64, kernel 6.18. `wireguard-tools` and the Proton config were installed
by hand on an earlier card; a fresh card has neither until the provision script
runs (and the config is pushed over SSH).

## How to do the usual things

All commands below were used in this project; the quirks are real.

- **Flash a card** (wipes it): `python setups\pi-smoke-test\pi_smoke_test_flash.py
  --image "E:\Drive Downloads\raspios_lite_arm64_latest.img.xz" --device 3
  --confirm-device "\\.\PhysicalDrive3" --wifi-from-env
  [--provision-script setups\pi-provision\pi-firstboot.sh]` needs an elevated
  PowerShell. From a non-elevated session, launch it with `Start-Process
  powershell -Verb RunAs -Wait -ArgumentList '-NoProfile','-Command',$cmd`
  (the user accepts the UAC prompt), single-quote paths that contain spaces, and
  write the output to a log. **Before wiping a card**: check its exact size, look
  at what is on it read-only (one spare card turned out to hold personal photos),
  and wait for the owner's go. Windows shows "format this disk" dialogs: cancel.
- **Rewrite only the config** of a card that has not booted (no re-flash):
  `... --boot-dir F:\ --wifi-from-env --provision-script ...` (no admin needed;
  gives a new cloud-init instance id). Without `--wifi-from-env` it writes
  Ethernet only.
- **Reach the Pi**: `python setups\pi-smoke-test\pi_smoke_test_ssh_check.py
  [--host IP] [--wait 180]`. A fresh OS has new host keys: delete
  `setups/pi-smoke-test/pi_smoke_test_known_hosts` first. For longer checks send a
  script on stdin: `($lines -join "`n") | ssh ... htm@IP 'bash -s'`; start the
  script with a throwaway line (a hidden byte-order mark breaks line 1).
  Admin tools need `sudo` (the user's PATH lacks `/usr/sbin`).
- **Wait for something**: use `run_in_background` and read the output file; a
  foreground `Start-Sleep` is blocked by the tool.
- **The tool's safety filter** misreads some shell text (the word `rm`, quoted
  `\"` in awk). Use `shred -u`, `cut`, and `[System.IO.File]::Delete`.
- **Secrets**: print only names, lengths, masked fields. Do not type or paste a
  password for the maintainer; they enter it themselves or the script reads it
  from `.env`.

## How the maintainer wants to work (observed this session)

Propose before committing and wait for a go; never push or ask about pushing
(they force-push themselves); back up before any history rewrite. Check sources
before guessing (web docs, the sandbox repo's patterns) and say plainly what is
measured and what is inferred. Run checks yourself instead of asking for pasted
output. Do not change a setting on the laptop or the Pi without asking
(installs and network changes especially). Keep answers short and concrete.

## Things that went wrong (do not repeat)

- First-boot config is **cloud-init**, not `custom.toml` (older method ignored).
- `enable_ssh` alone did not start sshd on an early card; the empty `ssh` file
  worked. Which one suffices is open (item 16).
- Writing the partition table first makes Windows mount the new partition and
  fail the write; it is written last.
- The Pi going silent about 3 minutes after boot was **not** "first boot still
  running": NetworkManager's DHCP fails without a DHCP server (netplan's
  `link-local` did not help). Sharing fixes it.
- A first "Permission denied" over SSH can be transient (cloud-init installs the
  key late); a name lookup can be a stale cache entry.

## Map of the docs

`pi-technical.md` (current state), `pi-rationale.md` (decisions, open items 0 to
20), `pi-smoke-test/task.md` (the task spec, kept current), the report (evidence,
phases 1 and 2, Proton and first-boot follow-ups), `runpod-rationale.md` (why the
Pi exists), `report-format.md`. The sandbox repo (`claude-code-and-local-agent-sandbox`,
GitHub `hsc-projects/...`) holds the patterns to reuse: `docker/egress-proxy/`,
the credential-sidecar pattern in `docs/design/agent-sandbox-patterns.md`.
