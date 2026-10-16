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

**2026-09-28 — A cheap always-on VPS (e.g. Hetzner) was raised as an
alternative host and dismissed as too expensive for just a proxy.** Not
researched further; the reasoning predates the broader-host framing and may be
worth revisiting. The maintainer's separate Oracle Cloud account could serve as
a fallback host (not vetted). GitHub Codespaces and Google Cloud Shell (both
free) could host a Tailscale client for one-off browser-only SSH hops, largely
superseded by Tailscale SSH Console (`runpod-rationale.md`).

**2026-10-04 — Smoke test result: a Pi can be flashed and reached over SSH
headlessly from a Windows laptop, but a plain cable to the laptop does not stay
up; the cable needs the laptop to share its connection, or the Pi needs
Wi-Fi.** Details, evidence and tooling: `pi-smoke-test/pi-smoke-test-report.md`.
What it settled:

- No router is planned (maintainer, 2026-10-04): the Pi's links are the cable to
  the laptop and/or Wi-Fi to a phone hotspot.
- **Decision (maintainer): Windows Internet Connection Sharing on the laptop's
  Ethernet adapter for the cable.** Without a DHCP source NetworkManager's DHCP
  on `eth0` fails every 45 s and the Pi goes silent about 3 minutes after boot
  (two cards); with sharing it stayed connected. An earlier entry blamed "first
  boot still running"; that was wrong. Netplan's `link-local` did not help (it
  does not change the NetworkManager profile) and is not used. IPv6 is not
  required: with sharing the Pi is reached over IPv4 (IPv6 was seen off on the
  laptop's physical adapters; cause not established).
- **Decision (maintainer): prefer the hotspot over the cable, the cable as
  fallback.** The default route went to `eth0` (metric 100) over `wlan0` (600);
  the flash script sets `wlan0`'s metric to 50 (netplan `route-metric`), verified
  (item 12). A cable that is up but has no internet would still hold the route if
  preferred; no connectivity check is built. The hotspot costs phone data. The
  regulatory code in `network-config` (`JP`) should be the country of use; it was
  not read back.
- **Requirement (maintainer): the Pi must work without the hotspot, with only the
  LAN.** Cable plus sharing: a cold boot works. A cable with no sharing or DHCP
  at all still fails (about 3 minutes); fixes untried (item 10).
- *VPN.* With ProtonVPN on the laptop the Pi's traffic does not go through it
  (sharing is on the Wi-Fi adapter), and sharing makes the Pi's traffic appear to
  come from the laptop (any network's rules about extra devices are the
  maintainer's to check). A VPN on the Pi itself works through WireGuard: Proton's
  Linux CLI does not support headless setups or document ARM, so the route is a
  WireGuard config from the Proton account (one server per file). Tested: Japanese
  public IP, IPv4 and IPv6 through the tunnel, SSH unaffected. It is independent of
  the laptop's VPN (both can exit through the same server as separate tunnels).
  Open: behavior if the tunnel drops (no kill switch); how it combines with the
  egress-proxy role (it coexists with Tailscale).
- *First-boot configuration is cloud-init on this OS release,* not
  `custom.toml`/`firstrun.sh`; any re-provisioning should be written against it.
  A card that has already booted needs a new `instance_id` in `meta-data` for edits
  to apply. Installs can ride in `user-data` (`packages:`, `write_files:`,
  `runcmd:`) and need internet at that moment.
- *`enable_ssh` alone did not start sshd on an early card;* an empty `ssh` file is
  the documented workaround (raspberrypi/rpi-imager issue 1612). Whether either
  alone suffices is open (item 16).
- *Flashing from Windows:* the partition table (first 1 MiB) must be written last
  (writes into a mounted volume's sectors are blocked). The earlier "faulty card"
  reading looks like the first card reader (inferred).
- *Wi-Fi reconnect:* after a short hotspot absence `wlan0` reconnected by itself;
  a long absence is untested, and NetworkManager can stop retrying after repeated
  failures (`connection.autoconnect-retries`; item 12).
- *Diagnosing a Pi that goes quiet:* the journal is volatile, so watch live over
  SSH; Windows cannot read the root partition, and `wsl --mount` does not support
  SD card readers (Microsoft documentation; item 15).
- Not tested: a router/DHCP network (not planned).

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
5. Set up Tailscale on the Pi (done, item 14), and the auth-key provisioning path into
   the RunPod pod via `create-secret` (open).
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

8. **DNS through the Proton tunnel on the Pi.** Done (`pi-technical.md`). Untested:
   IPv6 resolvers (this network offers none).
9. **Proton tunnel as a service.** Done: starts at boot, DNS through it, also for
   devices that connect later. Open: behavior when the tunnel drops (no kill
   switch); how it combines with Tailscale and the egress-proxy role; whether the Pi
   should run its own VPN or share the laptop's tunnel adapter (the Pi's traffic
   through sharing bypasses the laptop's VPN, which is why it has its own).
10. **Cable with no sharing and no DHCP** still drops after about 3 minutes.
    Candidates, untried: infinite NetworkManager retries on `eth0` so it
    recovers when sharing returns; a link-local fallback for `eth0`. Documentation
    (not tested on the Pi): the 45 s failure matches NetworkManager's default
    `ipv4.dhcp-timeout` (45 s); `infinity` makes it keep requesting until it succeeds,
    and `connection.autoconnect-retries 0` retries activation forever (the default,
    -1, means the global default, 4). Both would go on the `eth0` profile.
11. **Connectivity-based failover.** The metrics only react to link state: a
    cable or hotspot that is up but has no internet keeps the default route.
    No connectivity check is configured. Documentation (not tested): NetworkManager 1.8
    and later run connectivity checks per connection and give a connection that fails the
    check a higher route metric (reports show +20000, the constant is not confirmed), then
    restore it when the check passes. That needs NetworkManager's `[connectivity]`
    configuration (check URI and interval); whether it works on the Pi's profiles is
    untested.
12. **Hotspot-first metric (50):** verified on the Pi. Still open: a long hotspot
    absence (the `autoconnect-retries` limit: the default is 4 activation attempts, `0` removes it), the Wi-Fi regulatory code read back
    (`iw` is not installed), and a hotspot on channels 12/13.
13. **First-boot installs.** `pi-provision/pi-firstboot.sh` runs for real and is
    retried by `pi-provision.service` until it succeeds (modules: `pi-technical.md`);
    built on the sandbox repo's habits (preflight, an active check after each
    install, a verified scrub). Docker comes from Docker's own apt repository, not
    Debian's `docker.io` (older; no buildx or Compose v2 plugin, which the sandbox
    repo uses), with the key checked against its published fingerprint and no user in
    the `docker` group. Still to add, one tested module at a time: the egress-proxy
    container (item 22), the Pi's own MCP server (item 21); pinned or logged versions;
    no long-lived secrets on the card. Known weakness: after about half an hour
    without network the service uses up its start limit (6 per hour) and stays failed
    until the next boot or a manual `reset-failed` and `start`.
14. **Tailscale on the Pi.** Done (`pi-technical.md`): interactive tagged join with
    no auth key on the card, coexists with the Proton tunnel, access policy saved
    (`pi-provision/tailscale-policy.hujson`). A non-expiring node is covered by the
    stolen-Pi checklist (item 20). The RunPod pod's auth key is separate (item 5).
    Identity (decided 2026-10-13, for now): the node state is
    copied onto the stick and restored on a fresh flash, so re-flashing (frequent while the
    script is being tested) needs no new login; the card stays the primary copy, so a Pi
    without the stick still joins. Linking the state onto the stick was rejected (no tailnet
    without the stick). A stolen stick can impersonate `tag:pi` (accept SSH only, per the
    ACL). To be dropped once re-flashes are rare. Open: the
    widget script for the phone unlock (item 20).
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
19. **Windows connection sharing can reset** after a laptop reboot, sleep or network
    change (the `SharedAccess` service stops, and starting it was not enough).
    `setups/windows/restart-sharing.bat` fixes it in one call. Setting the service to
    automatic start would prevent the stop; it is a laptop setting, so the
    maintainer's call. Separately, sharing could not be enabled with Wi-Fi as the
    internet side (`0x80040201`, a COM+ event error) on 2026-10-11 and 2026-10-13: it
    survived a reboot and manual service starts, and phone USB tethering worked each
    time; cause not found (report, last follow-ups).
20. **Keyholder** (designed 2026-10-05; built 2026-10-11, `pi-technical.md`; evidence
    in the report). Context (maintainer): unattended, in a semi-secure location, so
    theft of the whole Pi is in scope; the Pi has no TPM, so nothing is bound to
    hardware. Two tiers:
    - *Unattended tier* (the WireGuard config, the Tailscale node state): plain on the
      stick so the Pi recovers from a power cut alone. Each is revocable, which is the
      protection: `pi-stolen-checklist.md` names each credential and where to revoke
      it; the Tailscale ACL gives the Pi's node minimum reach; the Pi holds no
      outbound SSH keys.
    - *High-value tier* (the RunPod key, any GitHub token): on the stick only
      passphrase-encrypted (gpg), decrypted on request into a root-only tmpfs under
      `/run`, never on disk in the clear; a power cut or theft means they are gone
      until unlocked, and only credentialed MCP tools (item 21) stop meanwhile. Also
      wanted: a spending cap or small prepaid balance on RunPod, and the narrowest key
      scopes (what RunPod offers: to verify).
    - *Unlock from the phone over Tailscale:* a phone SSH key behind biometrics, with a
      forced command that allows only the unlock (no shell); the phone never holds the
      credentials. The design must not depend on the phone: any device with an
      authorised key, or the admin through sudo, can unlock. Passphrase: 5 random words
      (about 64 bits; chosen 2026-10-13 over 7: gpg's S2K is already at its maximum and a
      failed unlock costs 2 s) from the maintainer's password manager, never seen by the
      assistant. Phone
      tool for now: Termux (app support unverified). A separate `pikeys` user.
    - *Rejected for now:* LUKS plus Tang on the stick and card (protects against
      reading them elsewhere only as well as the speed of revoking the node, and adds a
      second always-on machine); hardware tokens do not fit.
    - *Phone:* the Termux key is authorised and `status` works over the tailnet on
      mobile data (2026-10-13).
    - *To do:* the widget script; the first real
      secret (the RunPod key; until then `RUNPOD_API_KEY` stays in
      `setups/.secrets/.env`, item 18); a consumer for it (item 21).
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
22. **Egress proxy on the Pi** (the sandbox repo's `docker/egress-proxy`, Squid; read
    `docs/design/agent-sandbox-patterns.md`, Patterns 1 to 3, first). Proposed 2026-10-11,
    not decided: run it on the Pi, publish on `127.0.0.1`, expose it on the tailnet with
    `tailscale serve`, with a relay container on the sandbox's `internal` network that
    forwards to the Pi (own tag, ACL rule to `tag:pi` port 3128). Open: exit through
    Proton or directly; a kill switch (none exists, item 9); fail-closed when the Pi is
    down; where the allowlist lives (single source in the sandbox repo, pushed by script).
    Build order: Pi side alone, then tailnet and ACL, then the sandbox side and `verify.sh`.

Suggested order (2026-10-13): item 20 (Termux, the first secret), then 22, then 21;
items 10, 11 and the rest of 12 are low priority unless the maintainer says otherwise.

Not a to-do, just a standing fact: keeping the Pi available/online when
needed is the maintainer's own responsibility, not something planned
around here — *how* (monitoring, alerting if it drops) is untouched and
may not need to be.
