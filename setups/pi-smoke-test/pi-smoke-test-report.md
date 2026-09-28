# Pi smoke test — report

Structure per `setups/report-format.md`: one top-level section per phase,
each with a short summary followed by detail subsections.

## Phase 1 — write, configure, and flash the image

**Summary: blocked, not done. Paused 2026-09-28 (maintainer).** The image
was downloaded and customized correctly, but the actual `dd` write to
the SD card failed with a hardware-level medium error partway through.
Confirmed with a second, independent tool (`f3write`) that this is a
real hardware fault on the device, not a bug in the flash script — two
different tools failed at two different sectors with the same kernel-level
Medium Error. Not yet isolated: whether it's the SD card itself or the
USB card reader that's actually bad. Paused here pending the maintainer
trying a different reader.

### What was built

- `pi_smoke_test_flash.py` (this directory): auto-detects the SD card
  (USB, removable, ~120G — refuses to guess if zero or more than one
  match, offers an interactive numbered pick or `--device` override),
  prints a compact device-identity table (size, used%, model, serial,
  bus) and requires typed/Enter confirmation before writing anything,
  generates the task-local `pi_smoke_test_key`/`.pub` keypair, streams
  the downloaded image through `dd` with no unencrypted intermediate
  copy, then mounts the new boot partition to write `custom.toml`
  (hostname `pi-host`, account `htm`, the task-local pubkey, SSH
  password auth disabled) and add the `init=` boot param `cmdline.txt`
  needs to actually apply it on first boot. The `custom.toml`/`cmdline.txt`
  mechanism was verified against `RPi-Distro/raspberrypi-sys-mods`' actual
  `firstboot`/`init_config` source (not guessed) — `rpi-imager --cli`
  only does a raw write + checksum verify, no customization flags exist
  there.
- Image source: Raspberry Pi OS Lite, 64-bit (Debian 13 "trixie", kernel
  6.18, released 2026-09-15), downloaded via direct host `wget` from
  Raspberry Pi's stable "latest" redirect (the fetch tool can't carry a
  file this size, and `downloads.raspberrypi.com` blocks the fetch tool's
  `robots.txt` entirely regardless).
- `.gitignore` entry added so the task-local private key can never be
  committed.

### What went wrong

Run from a real terminal (PyCharm's Run console isn't a real pty, so
`sudo` couldn't prompt there — fixed by using PyCharm's Terminal tab
instead). Auto-detection correctly found `/dev/sda` (119.4G, USB,
removable, matches the card described by the maintainer). The image
decompressed and streamed into `dd` fine, but `dd` failed with `fsync
failed for '/dev/sda': Input/output error` after writing ~3.06GB (close
to the full ~2.9GB decompressed image size).

`journalctl -k` showed the real cause — a hardware-level medium error,
not a script bug:
```
I/O error, dev sda, sector 240 op WRITE ... Medium Error / Peripheral device write fault
sda: detected capacity change from 250347520 to 0
sd 10:0:0:0: [sda] access beyond end of device
critical medium error, dev sda, sector 250347392 op READ ... Unrecovered read error
sda: detected capacity change from 0 to 250347520
```
The failure sector (250347392) sits only ~128 sectors (65KB) before the
device's own reported total (250347520 sectors), and the reported
capacity itself blipped to 0 and back — an initial read suggested a
**counterfeit/capacity-spoofed card** (firmware claims 128GB, real NAND
much smaller, so writes past the real capacity fail exactly like this).

### Confirmed with a second tool: real hardware fault, not a capacity-boundary artifact

`f3` installed (`sudo apt install f3`, maintainer confirmed 2026-09-28).
`f3write /media/htm/9C33-6BBD` (non-destructive, on the still-mounted
original exfat filesystem — the kernel hadn't re-scanned the partition
table since `dd` failed, so the old exfat partition was still what was
mounted) failed **immediately on the first test file**:
```
Creating file 1.h2w ... Write failure: Input/output error
Creating file 2.h2w ... f3write: Can't create file /media/htm/9C33-6BBD/2.h2w: Input/output error
```
`journalctl -k` at the same time showed the identical kind of real kernel
error, now at a *different* sector (66048, ~33MB in — nowhere near the
previous failure's location near the capacity boundary), plus the same
recurring read error near the reported end:
```
I/O error, dev sda, sector 66048 op WRITE ... Buffer I/O error ... lost sync page write
critical medium error, dev sda, sector 66048 op READ ... Unrecovered read error
critical medium error, dev sda, sector 250347392 op READ ... Unrecovered read error
```
Two unrelated tools (`dd`, `f3write`), two different failing sectors, same
real kernel-level Medium Error both times — this rules out a bug in
`pi_smoke_test_flash.py` itself. It also weakens the "boundary-only,
therefore spoofed capacity" read from the first failure (this new failure
isn't near the boundary at all) — now looks more like the device just
can't reliably write, full stop, whether that's the card or the reader.

### Next step (not yet done — paused here)

Isolate card vs. reader: try the same card in a different USB card
reader (or a device with a built-in SD slot) and re-run
`pi_smoke_test_flash.py` (or just `f3write`/`f3read` again, faster) to
see whether the same errors recur. `f3probe` (faster than
`f3write`/`f3read`, but writes to the raw device) is the other option
once a working reader is confirmed.
