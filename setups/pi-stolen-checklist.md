# Pi lost or stolen: what to revoke

Use this when the Pi, its SD card or its credential stick (`PIKEYS`) is lost, stolen,
returned or thrown away. The design (`pi-rationale.md`, item 20) keeps the credentials
on the Pi revocable, and the high-value ones only encrypted on the stick or in RAM, so
a loss costs a few revocations, not a rebuild. Do the first eight at once (from a phone
is fine); the rest can wait a day. Nothing below needs the Pi.

| What | Where it lives | Revoke at | Notes |
|---|---|---|---|
| Tailscale node | the Pi (`/var/lib/tailscale`) and a backup on the stick (`tailscale/`) | admin console, Machines, the Pi's row, Delete | cuts the Pi off the tailnet; it was tagged `tag:pi` with no key expiry, so a thief would otherwise stay on it |
| Claude Code login (Remote Control) | the stick (`claude/config/.credentials.json` and `.claude.json`, plain, mode 600) | your Claude account: sign out or revoke the Pi's Claude Code session, which also ends its Remote Control session | the stick alone is enough to use it, like the Proton config; do it at once, with the Tailscale node |
| Antigravity login (`agy`) | the stick (`claude/gemini/antigravity-cli/antigravity-oauth-token`, plain, mode 600) | your Google account, Security, third-party access: remove Antigravity (or run `/logout` in `agy` on a rebuilt Pi, which only clears the local copy) | the stick alone is enough to use it; do it at once, with the Claude login |
| GitHub login (`gh`) | the stick (`claude/gh/hosts.yml`, plain, mode 600; the token has the scopes repo, read:org, gist, workflow, so full access to your repositories) | github.com, Settings, Applications, Authorized OAuth Apps: revoke "GitHub CLI" | the stick alone is enough to use it; do it at once, with the Claude login; a narrower token (fine-grained, or a deploy key in the keyholder) is planned |
| RunPod pod SSH key for agents | the stick (`claude/ssh/runpod_ed25519`, plain, mode 600; its own key pair, not the laptop's `runpod-snngine` key) | RunPod console, Settings, SSH keys: delete the key named `pi0` (fingerprint `SHA256:GDbS+fyy…`, comment `pi-claude-runpod`) | the stick alone is enough to reach any pod that still has the key; the pods are short-lived, but do it at once |
| Cloud drive logins (Google Drive, Dropbox, OneDrive, Mega, Proton Drive) | the stick: `cloud/rclone.conf` (encrypted by rclone: tokens, or the dedicated accounts' passwords) and its passphrase, which is the keyholder secret `rclone_config_pass`, or, after `pi-cloud auto on`, the plain file `cloud/config-pass` | at each provider: Google account, Security, third-party access (remove rclone); Dropbox, the app's permissions or delete the app; Microsoft account, Privacy, app access; Mega and Proton: change the dedicated account's password or delete it | with `auto on` the stick alone opens them, so do it at once; otherwise the passphrase protects them like the other keyholder secrets. the Google Drive login is on the full scope (a loss exposes the whole Drive: revoke it at once); a Dropbox token (planned, through your own App-folder app) sees only its app folder; OneDrive, Mega and Proton are dedicated accounts, so a loss exposes only the Pi's files |
| Proton WireGuard config | the stick (`wireguard/`), plain | Proton account, Downloads, WireGuard configurations: delete the config for this device | then generate a new one and run `push_wireguard_config.py` |
| Hotspot password | the card's root partition (root-only netplan copy, plain) | change it on the phone | it is scrubbed from the boot partition, not from the root partition |
| Encrypted secrets (RunPod key, any GitHub token) | the stick (`secrets/*.gpg`) | rotate each at its service | only ciphertext is on the stick; how long it holds depends on the passphrase, so rotate anyway if the stick is gone |
| Unlock passphrase | in your head, your password manager and your phone | choose a new one and re-add every secret (`pi_keyholder.py add`) | only if you think it was seen |
| Phone and other unlock keys | the stick (`unlock/authorized_keys`, public keys) | remove the line for a lost device | a lost phone: also change the passphrase, since the phone may hold it |
| The phone's and the laptop's keys for the `claude` user | the stick (`claude/authorized_keys`, public keys; the laptop's is `~/.ssh/pi_claude_ed25519`) | nothing to revoke if the Pi is gone; with the Pi in hand, remove the line | the private halves are on the phone and the laptop; a lost phone or laptop: remove its line and sign the Claude session out |
| VS Code web token | the stick (`claude/vscode-web-token`, plain, readable by the `claude` user) | delete the file; the next first boot makes a new token (the phone widget reads it from the Pi each time) | usable only from a device on the tailnet (the grant for `tag:pi` allows tcp 443), so deleting the Pi's node already closes it; the editor's terminal is a shell as `claude` |
| The Pi's SSH host keys | the stick (`ssh-host/`, root-only) and the card (`/etc/ssh`) | delete `ssh-host/` on the stick before reusing it; the next first boot makes new ones | only lets someone impersonate the Pi to a client that trusts its old fingerprint; your devices then warn once, until you forget the old fingerprint |
| Your admin SSH key | the laptop only (the Pi holds the public half) | nothing to revoke on the Pi's loss | |

After the revocations: rebuild on a new card (`pi-technical.md`, "Operating the Pi"), join
the tailnet again with `--advertise-tags=tag:pi`, push the new WireGuard config, and
add the secrets again.
