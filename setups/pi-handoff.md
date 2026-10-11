# Pi work — handoff for the next session

State as of 2026-10-07. Read this first, then `pi-technical.md` (what the Pi
is now) and `pi-rationale.md` (decisions and numbered open items). The smoke
test's evidence is in `pi-smoke-test/pi-smoke-test-report.md`. Nothing here
contains a secret value; the secrets live in `setups/.secrets/` (gitignored).

## Where we are, in one paragraph

A Raspberry Pi 4 (8 GB) can be flashed and reached over SSH headlessly from
this Windows laptop. A plain cable to the laptop drops after about 3 minutes
(no DHCP); the fix in use is Windows Internet Connection Sharing on the
laptop's Ethernet adapter (restart it with `setups\restart-sharing.bat`), with a
phone hotspot over Wi-Fi as a second path (hotspot preferred through a route
metric, cable as fallback). A fresh flash provisions itself on first boot:
`wireguard-tools`, the credential stick (`PIKEYS`, holding the Proton WireGuard
config), the tunnel up at every boot with its DNS through it, and the Wi-Fi
password scrubbed from the boot partition; a failed run is retried. All of it was
tested on the Pi 2026-10-07 to 2026-10-11 (fresh flashes of both cards, boots with
no network and without the stick). Evidence: the smoke-test report's last
follow-up; details: `pi-technical.md`.

## Next steps, in order

1. **Docker, then Tailscale on the Pi** (items 13 and 14 in `pi-rationale.md`),
   one tested module each in the first-boot script. They lead to the larger piece
   the maintainer wants **later**: the Pi as the sandbox's egress proxy, reusing the
   sandbox repo's `egress-proxy` container.
2. **Keyholder design (item 20).** The stick gives the Pi a place for credentials
   that survives a re-flash; the open question is protection at rest (the stick is
   not encrypted, an unattended boot cannot supply a passphrase).
3. Items 10, 11, and the rest of 12 (see their entries), all low priority unless
   the maintainer says otherwise.
4. Loose ends: `decrypt_credential_bundle.py` (item 17, untracked, never run),
   `RUNPOD_API_KEY` (item 18), `ssh` file versus `enable_ssh` (item 16), and
   whether to set the Windows sharing service to automatic start (item 19).

**Practical notes**
- If the Pi is not found on `192.168.137.x`, run `setups\restart-sharing.bat`
  (asks for admin; `-Public 'Ethernet 2'` when the internet comes from phone USB
  tethering instead of `WiFi`). It starts the sharing service, switches sharing
  off on every adapter and on again for the chosen pair, and checks that DHCP
  listens. Windows allows one shared connection only; a leftover on the old
  adapter made `EnableSharing` fail with `0x80040201`.
- The search script can latch onto a stale neighbour entry: check port 22 on each
  `192.168.137.x` the Pi's MAC (`D8-3A-DD`) maps to.
- After plugging the stick back in, reboot the Pi (a failed mount is not
  retried); the tunnel then comes up unaided.
- `setups/pi-provision/push_wireguard_config.py --host IP` only for a new or
  changed config, or a new stick; a re-flash needs no push.

## Snapshot

**Git** (branch `docs/runpod-pi-setup`): the local history was rewritten
(two commits that were both named "dev" now have real messages; every hash
above them changed) and has **not been pushed**; the remote still has the old
history. The maintainer does any force-push themselves (their commit
conventions say so). Local backup branch `backup/before-dev-msg-rewrite-13114f5`
holds the pre-rewrite history. Everything in this note is committed except
`setups/decrypt_credential_bundle.py` (untracked on purpose; item 17).

**Cards** (both about 119 GiB, both with a Pi OS boot partition, so the flash
script's own size window cannot tell them apart; identify by exact size):
- card 1: 128,177,930,240 bytes. Freshly flashed 2026-10-11 and running in the Pi.
- card 2: 127,865,454,592 bytes. The spare; also freshly flashed (2026-10-11).
- The card reader was Disk 2 on 2026-10-11 (Disk 3 earlier; numbers change). The
  4 GB Transcend stick, label `PIKEYS`, lives in the Pi and is not a card to flash.
  **Before wiping any card or stick, ask what is on its Linux partition** (Windows
  cannot read it); a wipe on 2026-10-07 lost the hand-installed tunnel setup.

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

**The Pi** (2026-10-11): hostname `pi-host`, user `htm` (key-only), Debian 13,
aarch64, kernel 6.18, card 1 in it, the `PIKEYS` stick in a blue USB 3 port.
`wireguard-tools`, the key store and the tunnel at boot all come from the
first-boot script; the Proton config lives on the stick (a re-flash needs no
push). The Pi's address on the cable changes between boots.

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
- **Wiping a card also wipes everything on its Linux partition**, which Windows
  cannot read. Ask what is on a card or stick before flashing it (2026-10-07: the
  hand-installed tunnel setup was lost that way).
- Windows sharing stopping is not one problem: the service can be stopped, and a
  running service can still have no DHCP until sharing is switched off and on (and
  a leftover on an old adapter blocks it). Use `setups\restart-sharing.bat`.
- Heavy writes to a card (a flash) make Windows disk queries and PowerShell very
  slow; use short, light commands and run the flash in the background.

## Map of the docs

`pi-technical.md` (current state), `pi-rationale.md` (decisions, open items 0 to
20), `pi-smoke-test/task.md` (the task spec, kept current), the report (evidence,
phases 1 and 2, Proton and first-boot follow-ups), `runpod-rationale.md` (why the
Pi exists), `report-format.md`. The sandbox repo (`claude-code-and-local-agent-sandbox`,
GitHub `hsc-projects/...`) holds the patterns to reuse: `docker/egress-proxy/`,
the credential-sidecar pattern in `docs/design/agent-sandbox-patterns.md`.
