# Pi host — rationale

Decisions, reasoning, alternatives rejected, and open items for the
dedicated always-on host. Current configuration: `pi-technical.md`.
Origin of this need: `runpod-rationale.md`'s egress-restriction decision
(2026-09-28) — summarized here, not repeated in full.

**Standing principle (2026-09-28, shared with `runpod-rationale.md`):
keep pieces modular/reusable rather than one-off** — applies here to how
the Pi's services (egress-proxy, bridge expansion, whatever else lands
on it) are structured: separable pieces, not one monolith.

## Decisions

**2026-09-28 — Pi helper scripts live in this repo's `setups/`, alongside
these docs.** Flashing the SD card, finding the Pi on the local network,
and running commands on it over SSH will all need repeatable tooling
(same reasoning as the sandbox project's own scripted-command convention)
rather than fleshing out each command from scratch every time. Not yet
scoped or built — needs its own explicit proposal before any script is
written, per this repo's rule against unprompted workaround scripts.

**2026-09-28 — Use a dedicated, always-on separate machine (a PoE
Raspberry Pi), not a same-pod process or a second RunPod pod.** The
RunPod agent pod has no equivalent to the local sandbox's `egress-proxy`
container split (separate network/PID namespace protecting the proxy
from the agent) — see `runpod-rationale.md` for the full comparison of
options considered (same-pod Squid+Landlock, a second RunPod pod over
public ports, routing through the maintainer's dev host) and why each
was rejected. The maintainer wants the same containment guarantees as
the local Docker sandbox in every mode (dev session or phone-only), not
a fallback that quietly weakens for the harder-to-supervise case. A
dedicated Pi restores genuine separate-machine isolation and is
maintainer-owned hardware, not a platform-dependent free tier or a
second cloud bill.

**2026-09-28 — Reached over Tailscale, not a raw public address.**
Tailscale is already used in this sandbox project for `bridge-relay`'s
inbound path, so it's an already-trusted mechanism rather than a new
one. Gives real device-level authentication instead of "public URL plus
our own bolted-on auth," which a raw exposed RunPod pod-to-pod port
would have needed.

**2026-09-28 — Scope: a general-purpose always-on host, not a
single-purpose proxy appliance.** The Pi is a real machine with normal
Docker/`CAP_NET_ADMIN`/nftables access — unlike a RunPod pod, which
can't run nested Docker at all (see `runpod-rationale.md`'s
Docker-in-Docker evidence). So it's capable of running this repo's full
local sandbox stack, not just a bare Squid instance, and is expected to
host other small always-on services (other MCP servers, etc.) alongside
the egress-proxy role that triggered building it. Renamed the component
from "Pi egress proxy" to "Pi host" to reflect this — the proxy is one
job it does, not its sole purpose.

**2026-10-05 — The Pi is also meant to be a keyholder (maintainer,
stated in conversation; not in the earlier docs).** Besides the egress
proxy and the bridge expansion, it is the machine that holds the
credentials, so the sandbox and the pods never do. This is the sandbox
repo's credential-holding pattern (`agent-sandbox-patterns.md`, Pattern 1):
one single-purpose service per credential, the secret in a root-only file
(mode 0400/0600) read once by the one process that needs it, never in
the environment of anything the agent runs, and the service reached only
over Tailscale. It moves "the orchestration layer" in
`runpod-rationale.md` (where RunPod's own API key stays) from the host
session to the Pi, and would hold the RunPod key for the phone-triggered
spin-up. Consequences already in force: no secret travels in the
first-boot config on the card (keys are pushed over SSH into root-only files),
and the provisioning script scrubs the Wi-Fi password from the FAT boot
partition once cloud-init has used it. Open (item 20): which credentials,
and what protects them if the SD card is physically taken.

**2026-10-11 — The Pi gets its own MCP server, and the host is meant to be
portable (maintainer, in conversation).** Day-to-day operation (overview of
running services, detail-free error notification, start/stop of optional
services) goes through an MCP server on the Pi, so routine work needs no SSH or
root; design in item 21. A Pi hardware failure is acceptable as a single point
of failure on the condition that the SD card or image can be moved to a new Pi,
and later to a cloud server. Safety comes first: the design reuses the sandbox
repo's established patterns (Patterns 1 to 3) and improves them where needed.

**2026-09-28 — A cheap always-on VPS (e.g. Hetzner) was raised as a
possible alternative/fallback host and dismissed as too expensive for
just a proxy.** Not researched further, and this reasoning predates the
broader-host framing above — may be worth revisiting once the Pi's full
job list is clearer. The maintainer has an independent, unrelated
Oracle Cloud account in progress that could be revisited if a fallback
host is ever needed — not adopted here, not vetted for this purpose.
Two free-tier alternatives noted the same day, for occasional
browser-only admin access rather than an always-on host role (not a
substitute for the Oracle VM idea, a different use case): **GitHub
Codespaces** (free tier, ~60 core-hours/month on a free GitHub account —
full browser-based VS Code + terminal) and **Google Cloud Shell** (free,
browser-based terminal, generous quota, no billing account required).
Either could run a Tailscale client for a one-off SSH hop from a
browser-only device — largely superseded for that specific purpose by
Tailscale SSH Console (see `runpod-rationale.md`'s resolved admin/jump-pod
item), which needs no separate service at all, but still worth knowing
about as fallbacks.

**2026-10-04 — Smoke test result (corrected the same day): a Pi can be
flashed and reached over SSH headlessly from a Windows laptop, but a plain
cable to the laptop does not stay up; the cable needs the laptop to share
its connection, or the Pi needs Wi-Fi.** Details, evidence and tooling:
`pi-smoke-test/pi-smoke-test-report.md`. What it settled for this host's
design, and what it did not:

- *No router is planned for this host/Pi combination (maintainer,
  2026-10-04).* So the Pi's links are: the cable to the laptop, and/or
  Wi-Fi to a phone hotspot. A router/DHCP network is not a case to test.
- **Decision (maintainer, 2026-10-04): use Windows Internet Connection
  Sharing on the laptop's Ethernet adapter for the cable.** Measured:
  without a DHCP source, NetworkManager's DHCP on `eth0` fails every 45 s
  and the Pi goes silent about 3 minutes after every boot (two cards, with
  the link up the whole time); a runtime `ipv6.method link-local`
  change kept it up, and with sharing it stayed `connected` for 8 minutes
  on the default `dhcp4: true` config. The Pi then also has internet through
  the laptop's connection. An earlier version of this entry blamed the
  silence on "first boot still running"; that was wrong.
- *Netplan's `link-local: [ipv4, ipv6]` did not help:* it does not change
  the generated NetworkManager profile (`ipv6.method ignore`), and a card
  with it dropped the same way. It is not used.
- *IPv6 is not the requirement it looked like.* On a plain cable IPv6
  link-local was the only reachable address (so IPv6 had to be on at the
  laptop), but that case is not usable anyway; with sharing the Pi is
  reached over IPv4. IPv6 was observed off on the laptop's physical
  adapters, including while ProtonVPN was connected; whether the VPN client
  causes it is not established (the first occurrence was reported with the
  VPN not connected).
- *VPN:* with ProtonVPN connected on the laptop, the Pi's traffic does not
  go through it (sharing is on the Wi-Fi adapter); the Pi's public IP stayed
  the laptop's underlying one. Whether a VPN on the Pi itself, or sharing the
  tunnel adapter, would be wanted is open. Windows sharing makes the Pi's
  traffic appear to come from the laptop; any network's rules about sharing
  or extra devices are the maintainer's to check.
- *Wi-Fi to a phone hotspot works:* joined, internet through `wlan0` alone,
  stable with `eth0` also up; credentials come from the gitignored
  `setups/.secrets/.env`. The regulatory code is set in `network-config`
  (`JP`); it should be the country the Pi is used in. Whether it took
  effect on the Pi was not read back.
- *First-boot configuration is cloud-init on this OS release*
  (`user-data`, `network-config`, `meta-data` on the boot partition), not
  `custom.toml`/`firstrun.sh`. Any later re-provisioning of the Pi (or a
  second one) should be written against cloud-init. A card that has
  already booted needs a new `instance_id` in `meta-data` for edited files
  to apply. First-boot installs can ride along in `user-data`
  (`packages:`, `write_files:`, `runcmd:`); they need internet at that moment.
- *`enable_ssh` in `user-data` did not start sshd by itself on an early
  card*; an empty `ssh` file on the boot partition is the documented
  workaround (raspberrypi/rpi-imager issue 1612), and the Pi deleted it
  after use. Whether either alone suffices on a fresh flash is not
  established (every working card had both).
- *Flashing from Windows:* writes into a mounted volume's sectors are
  blocked, so the partition table (first 1 MiB) must be written last.
- *The earlier "faulty card" reading looks like the first card reader,*
  not the card (inferred; the same card took a full write and booted the
  Pi on a second reader).
- *A VPN on the Pi itself is possible, through WireGuard (2026-10-04).*
  Proton's official Linux CLI does not support headless setups and does not
  document ARM, so the route is a WireGuard config from the Proton account
  (one server per file). Tested on the Pi: install with
  `--no-install-recommends` (no `resolvconf`), `wg-quick up` behind a
  150 s safety timer, a Japanese public IP, IPv4 and IPv6 through the
  tunnel, SSH unaffected. This is independent of the laptop's VPN, which does
  not cover the Pi's traffic. Open at the time (since done, see item 9): DNS through the tunnel, start at
  boot. Still open: behavior if the tunnel drops (no kill switch) and how it
  combines with the egress-proxy role (it coexists with Tailscale).
- **Decision (maintainer, 2026-10-04): prefer the hotspot over the cable,
  with the cable as the fallback, and keep the Wi-Fi settings.** The Pi's
  default route went to `eth0` (NetworkManager metric 100) over `wlan0`
  (600) on the card tested. The flash script now sets `wlan0`'s route metric
  to 50 through netplan `dhcp4-overrides: route-metric` (documented for the
  NetworkManager renderer), so the preference is in the first-boot config.
  Verified on the Pi 2026-10-07 to 2026-10-11 (item 12). A cable that is up but has no internet (laptop
  offline, sharing off) would still hold the default route only if it were
  preferred; with Wi-Fi preferred that case matters less, but a connectivity
  check was not built. Using the phone hotspot as the main path costs phone
  data.
- **Requirement (maintainer, 2026-10-04): the Pi must work without the
  hotspot, with only the LAN.** Tested for the case the cable plus Windows
  sharing: a cold boot with the hotspot off came up and was reachable in
  about 40 s, had internet over `eth0` alone, and stayed connected for about
  6 minutes with `wlan0` idle. The case of a cable with no sharing or DHCP at
  all still fails (about 3 minutes); candidate fixes not yet tried: infinite
  NetworkManager retries on `eth0` so it recovers when sharing returns, and a
  link-local fallback for `eth0`.
- *The Pi and the laptop can exit through the same Proton server.* With the
  laptop's Proton app and the Pi's WireGuard tunnel both on the Japan
  server, both showed the same public IP and country (measured). They are
  two separate tunnels to one server; the Pi's traffic is not routed through
  the laptop's.
- *Wi-Fi reconnect when the hotspot is off or absent:* with the hotspot off,
  `wlan0` failed activation (`ssid-not-found`) and sat `disconnected`.
  When the hotspot was turned back on, `wlan0` reconnected by itself within
  about 90 s of the watch starting, with no action on the Pi (it got an
  address and reached the internet through the phone). Tested only after a
  short absence (one failed attempt in the log); a long absence with many
  failed attempts, or a cold boot with the hotspot off, was not tested, and
  NetworkManager can stop retrying a profile after repeated failures
  (`connection.autoconnect-retries`; how it resets was not checked). On that
  card the routes still showed `eth0` at metric 100 and `wlan0` at 600, i.e.
  the new metric of 50 is not on the Pi yet.
- *Diagnosing a Pi that goes quiet:* the journal is volatile, so watch
  live over SSH; Windows cannot read the root partition, and `wsl --mount`
  does not support SD card readers (Microsoft documentation).
- Not tested: a router/DHCP network (not planned), Docker, Tailscale,
  sharing after a laptop reboot or sleep, a VPN on the Pi.

## Open items

Ordered by dependency. This list is a starting point — confirm or add to
it, it isn't guaranteed complete.

0. **Highest priority — research against our actual goals and existing
   solutions**, before any hardware/OS commitment: how people already
   run an always-on Pi as a Tailscale-reachable gateway/relay for a
   cloud workload (common homelab patterns, existing project templates),
   checked against what this specific setup actually needs (egress
   proxy + bridge-server expansion + whatever else lands on it). Point
   of this step is to avoid designing items 1+ from scratch when a
   known-good pattern already covers some or all of it.
1. **Record the existing Pi's specs.** Not a purchase decision — already
   owned, not expected to be a limiting factor. Partly recorded now (see
   `pi-technical.md`: card size, kernel, architecture). Still open: the
   PoE hat/injector and how the Pi is powered.
2. Choose OS for the Pi. (Still open: the smoke test used Raspberry Pi OS
   Lite 64-bit only as a scoped test OS, not as the answer to this item.)
3. Enumerate the Pi's full job list — egress-proxy and the bridge
   expansion are named; "other small services like MCP servers" isn't
   further specified. Related: whether the Pi ends up running a second
   full instance of this repo's sandbox stack, or just the specific
   services it turns out to need.
   **Candidate added 2026-09-28 (maintainer): a Claude Code instance on
   the Pi itself, for debugging/dev.** Not decided. Open sub-question:
   sandboxed vs. bare/host-level — the maintainer's initial lean is that
   running a full instance of this repo's own stack on the Pi ("host-pi-claude")
   would be the easiest path, since it gives that instance the sandbox
   project's containment and context in one move rather than a bare
   Claude Code install needing its own separate credential/containment
   design. Also touches the login-expiry open item below (a subscription
   login on the Pi would hit the same OAuth-expiry problem as the
   sandbox container unless `claude setup-token`'s one-year token proves
   out).
4. Decide dedicated vs. shared egress-proxy instance (a new instance on
   the Pi vs. reusing the local sandbox's existing `egress-proxy`) — the
   trade-off (blast radius if the RunPod-side agent is compromised, vs.
   operational simplicity of one shared instance) hasn't been discussed.
5. Set up Tailscale on the Pi, and the auth-key provisioning path into
   the RunPod pod via `create-secret`.
6. Design the bridge-server expansion itself (which tool(s) it exposes
   for phone-triggered pod spin-up, what it needs to store) — needs its
   own explicit proposal before any code is written, per this repo's
   rule against unprompted custom scripts.
7. Physical network/location details (which LAN, PoE switch/injector
   availability) — largely answered for this combination (maintainer,
   2026-10-04): no router; the cable to the laptop with Windows connection
   sharing, and/or Wi-Fi to a phone hotspot. Still open: PoE switch/injector
   availability and how the Pi is powered.

Follow-ups from the 2026-10-04 smoke test (all low priority unless the
maintainer says otherwise; details in `pi-smoke-test/pi-smoke-test-report.md`):

8. **DNS through the Proton tunnel on the Pi.** Done 2026-10-07 to 2026-10-11
   without `resolvconf`: see item 9 and `pi-technical.md` (tunnel hooks plus a
   NetworkManager dispatcher). Untested: the effect of IPv6 resolvers (this
   network offers none).
9. **Proton tunnel as a service.** Done 2026-10-07 to 2026-10-11: starts at
   boot (`wg-quick@`), DNS goes through it, also for devices that connect later
   (see `pi-technical.md`). Still open: behavior when the tunnel drops (no kill
   switch), and how it combines with Tailscale and the egress-proxy role.
   Related: whether the Pi should run its own VPN or the laptop's tunnel adapter
   should be shared (the Pi's traffic through the laptop's sharing bypasses the
   laptop's VPN, which is why the Pi has its own).
10. **Cable with no sharing and no DHCP** still drops after about 3 minutes.
    Candidates, untried: infinite NetworkManager retries on `eth0` so it
    recovers when sharing returns; a link-local fallback for `eth0`.
11. **Connectivity-based failover.** The metrics only react to link state: a
    cable or hotspot that is up but has no internet keeps the default route.
    No connectivity check exists; what NetworkManager supports for this is
    unresearched.
12. **Hotspot-first metric (50) on the Pi:** verified on the Pi (2026-10-07 to
    2026-10-11: `wlan0` default at 50, `eth0` at 100, a cold boot with the
    hotspot off, reconnect when it returns). Still open: a long hotspot absence
    (the `autoconnect-retries` limit), the Wi-Fi regulatory code read back (`iw`
    is not installed), and a hotspot on channels 12/13.
13. **First-boot installs.** `pi-provision/pi-firstboot.sh` runs for real (modules:
    WireGuard tools; the credential stick; the tunnel at boot with its DNS
    dispatcher; Docker; Tailscale; scrub of the Wi-Fi password from the boot
    partition; built on the sandbox repo's Dockerfile/entrypoint habits: preflight,
    an active check after each install, a verified scrub) and is retried by
    `pi-provision.service` until it succeeds. Docker (2026-10-11): from Docker's own
    apt repository, not Debian's `docker.io` (older; no buildx or Compose v2
    plugin, which the sandbox repo uses), the signing key checked against its
    published fingerprint, no user in the `docker` group; tested by hand beside the
    tunnel, then through the script's own install path on fresh flashes of both
    cards. Tailscale: item 14. Still to add, one tested module at a time: the
    sandbox's egress-proxy container (a proxy is the Pi's core job), the Pi's
    own MCP server (item 21); pinned or logged versions; no long-lived secrets
    on the card. Known weakness: after about half an hour without network the
    service uses up its start limit (6 per hour) and stays failed until the next
    boot or a manual `reset-failed` and `start`.
14. **Tailscale on the Pi.** Done 2026-10-11 (details in `pi-technical.md`):
    installed by the first-boot script (daemon only), joined interactively over
    SSH with `--advertise-tags=tag:pi` (no auth key on the card; the flag gives a
    node without key expiry, whereas tagging an already-joined node did not remove
    it), `--accept-dns=false`. Coexistence with the Proton tunnel was checked and
    is fine. The access policy is saved (`pi-provision/tailscale-policy.hujson`):
    the maintainer's devices reach it on port 22 only, and the Pi cannot start
    connections to them. The phone's SSH attempts reached sshd and were refused for
    lack of a key, as expected. A non-expiring node is covered by the stolen-Pi
    checklist (item 20). The RunPod pod's auth key is separate (item 5). Open: link
    `/var/lib/tailscale` onto the stick so a re-flash keeps the Pi's identity (not
    decided); card 2's older node `pi-host-test` still expires 2027-04-09; the remote
    unlock from the phone on mobile data (item 20) is not built.
15. **Reading the Pi's logs when it stops responding.** Windows cannot read
    the root partition and `wsl --mount` does not support SD card readers;
    WSL plus usbipd-win would, but is not set up. The journal is volatile;
    persistent logging would be a change on the Pi.
16. **`ssh` file versus `enable_ssh`:** which suffices on a fresh flash (the
    flash script has `--no-ssh-file` and `--no-enable-ssh` to test it).
17. **`setups/decrypt_credential_bundle.py`** (unpacks a gpg bundle into a
    private folder) was written, never run, and is not committed: keep,
    commit or remove.
18. **`RUNPOD_API_KEY`** is now in `setups/.secrets/.env` with no use decided;
    any use needs the exact calls proposed first.
19. **Windows connection sharing can reset** after a laptop reboot, sleep or
    network change (seen again 2026-10-11: the `SharedAccess` service had stopped,
    and starting it was not enough). `setups/restart-sharing.bat` now fixes it in
    one call (`-Public 'Ethernet 2'` when the internet comes from phone USB
    tethering). Setting the service to automatic start would prevent the stop; it
    is a laptop setting, so it is the maintainer's call.
20. **Keyholder design** (see the 2026-10-05 decision above). Decide which
    credentials the Pi holds (RunPod API key for the spin-up trigger, the
    Tailscale auth key for the pod, possibly the GitHub token the sandbox
    sidecars use), how each is stored (root-only file secrets, read once by
    one process) and delivered (over SSH, never on the card), and what
    protects them at rest: the SD card is removable and its root partition is
    not encrypted, so anyone holding the card could read the keys. Options to
    weigh, none researched: disk encryption, loading keys into RAM over SSH
    after each boot (lost on power loss), narrowly scoped and rotatable keys.
    Until then `RUNPOD_API_KEY` stays on the laptop in `setups/.secrets/.env`
    (item 18). Any tool that uses a held credential (item 21) waits for this.
    **Direction chosen 2026-10-11 (maintainer: unattended, in a semi-secure
    location, so theft of the whole Pi is in scope; not yet built):** the Pi has
    no TPM, so nothing is bound to hardware. Two tiers instead.
    - *Unattended tier* (the WireGuard config, the Tailscale node state): stays
      plain on the stick so the Pi recovers from a power cut alone. Each is
      revocable, which is the protection: a written **stolen-Pi checklist** (to
      write, in `setups/`) names each credential and where to revoke it (new
      Proton config, remove the Tailscale node, and so on); the Tailscale ACL
      gives the Pi's node the minimum reach; the Pi holds no outbound SSH keys.
    - *High-value tier* (the RunPod key, any GitHub token): stored on the stick
      only encrypted with a passphrase (`age` or gpg; this is also the idea behind
      item 17), decrypted into a root-only tmpfs under `/run` after each boot,
      never written to disk in the clear. A power cut or theft means they are gone
      until unlocked. Only credentialed MCP tools (item 21) stop meanwhile. Also:
      a spending cap or small prepaid balance on RunPod, and the narrowest key
      scopes (what RunPod offers: to verify).
    - *Unlock from the phone, one touch, over Tailscale (so from anywhere):* the
      phone holds an SSH key behind biometrics and the passphrase, never the
      credentials. In the Pi's `authorized_keys` that key is limited with a forced
      command (`command="/usr/local/sbin/pi-unlock",no-pty,no-port-forwarding`),
      so it can do only the unlock, not open a shell. App support (Shortcuts,
      Termux:Widget, Termius snippets) is not verified; depends on the phone.
    - *Rejected for now:* LUKS plus Tang on the stick and card (protects against
      reading them elsewhere, but only as well as the speed of revoking the Pi's
      tailnet node, and adds a second always-on machine); revisit if theft at rest
      becomes a concern. Hardware tokens do not fit (WireGuard and API keys cannot
      live in one).
21. **The Pi's own MCP server** (brainstormed 2026-10-11, nothing built).
    Purpose: day-to-day operation of the Pi without SSH or root; root stays for
    provisioning and for changing the MCP's own code. Built as the sandbox repo's
    Pattern 1 (`docs/design/agent-sandbox-patterns.md`): a custom FastMCP server
    in a container with `cap_drop: [ALL]`, `no-new-privileges`, an unprivileged
    user, and any secret read once by the entrypoint; no Docker socket mounted.
    Planned tools:
    - *Overview*: what is running, from one root-owned manifest that lists each
      service as core or optional with its health check (a new service needs a
      manifest line, not MCP code). Fixed typed fields only, never log text
      (logs can carry attacker-controlled content).
    - *Error notification without details*: only "service X is failing"; the
      details stay readable over SSH. Open: delivery (the agent polls `status`,
      or the Pi pushes to the maintainer's phone; the push is probably the real
      need).
    - *Start/stop of optional services*: through a root-owned helper script that
      accepts only `start`/`stop` and a name from the manifest's optional list,
      run by the MCP user through one sudoers rule. Core services (tunnel, proxy,
      the MCP itself) are not stoppable this way. Alternative not chosen: a
      request queue like the sandbox's `tasks.db`.
    Constraints from the sandbox patterns: two tool surfaces (a narrow agent
    surface; an admin surface on a separate port and token, covering allowlist
    and credential changes, where an agent may only propose), each tool builds
    its own target and takes no caller-supplied URL or command (Pattern 1);
    reachable from the sandbox only through one fixed relay port, listening on
    the Tailscale interface only (Pattern 2); check for Unix sockets afterwards.
    Start read-only. Build order: Docker (item 13), Tailscale (item 14), MCP
    skeleton with one `status` tool, the proxy, then credentialed tools. The
    images and manifest are meant to move to a new Pi or a cloud server; the
    first-boot preflight is pinned to aarch64 and Debian 13, so a move to x86
    needs multi-arch images and a preflight change.

Not a to-do, just a standing fact: keeping the Pi available/online when
needed is the maintainer's own responsibility, not something planned
around here — *how* (monitoring, alerting if it drops) is untouched and
may not need to be.
