# Pi lost or stolen: what to revoke

Use this when the Pi, its SD card or its credential stick (`PIKEYS`) is lost, stolen,
returned or thrown away. The design (`pi-rationale.md`, item 20) keeps the credentials
on the Pi revocable, and the high-value ones only encrypted on the stick or in RAM, so
a loss costs a few revocations, not a rebuild. Do the first four at once (from a phone
is fine); the rest can wait a day. Nothing below needs the Pi.

| What | Where it lives | Revoke at | Notes |
|---|---|---|---|
| Tailscale node | the Pi (`/var/lib/tailscale`) | admin console, Machines, the Pi's row, Delete | cuts the Pi off the tailnet; it was tagged `tag:pi` with no key expiry, so a thief would otherwise stay on it |
| Proton WireGuard config | the stick (`wireguard/`), plain | Proton account, Downloads, WireGuard configurations: delete the config for this device | then generate a new one and run `push_wireguard_config.py` |
| Hotspot password | the card's root partition (root-only netplan copy, plain) | change it on the phone | it is scrubbed from the boot partition, not from the root partition |
| Encrypted secrets (RunPod key, any GitHub token) | the stick (`secrets/*.gpg`) | rotate each at its service | only ciphertext is on the stick; how long it holds depends on the passphrase, so rotate anyway if the stick is gone |
| Unlock passphrase | in your head, your password manager and your phone | choose a new one and re-add every secret (`pi_keyholder.py add`) | only if you think it was seen |
| Phone and other unlock keys | the stick (`unlock/authorized_keys`, public keys) | remove the line for a lost device | a lost phone: also change the passphrase, since the phone may hold it |
| Your admin SSH key | the laptop only (the Pi holds the public half) | nothing to revoke on the Pi's loss | |

After the revocations: rebuild on a new card (`pi-technical.md`, "Operating the Pi"), join
the tailnet again with `--advertise-tags=tag:pi`, push the new WireGuard config, and
add the secrets again.
