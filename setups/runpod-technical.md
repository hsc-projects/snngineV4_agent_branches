# RunPod setup — technical

Current configuration for the `snngineV4_cloud` RunPod environment.
Rationale, alternatives, and open items: `runpod-rationale.md`.

## Infrastructure

- **Region**: `EU-RO-1` (all resources below live here).
- **Network volume**: `qze81dpw7q` ("snngine-workspace"), 20GB Standard,
  `EU-RO-1`. Mount path on any pod: `/workspace`.
- **CPU pod**: none currently exists.
- **GPU pod**: none currently exists. Target when created: RTX 2000 Ada,
  `EU-RO-1`.
- **Tooling**: the `runpod` Claude Code plugin (marketplace
  `runpod/runpod-plugins-official`), authenticated MCP connection.

## Credentials

- RunPod's own API key: held by the orchestrating host session's plugin
  connection. Never passed into any pod.
- Agent operating credentials (LLM auth, git, etc.): not yet enumerated.
  Mechanism when they are: RunPod `create-secret`, referenced from a
  pod's `env` as `{{ RUNPOD_SECRET_<name> }}`.

## Security / containment

Not yet built:
- Custom hardened pod image: root-starting entrypoint that self-drops
  capabilities (`prctl(PR_CAPBSET_DROP)`) and sets `no-new-privileges`,
  then hands off to a non-root user; `guard-exec` copied in and wired up
  for the agent's shell-tool calls (filesystem + network-port Landlock
  restriction).
- Egress proxy host: a dedicated always-on machine (a PoE Raspberry Pi)
  running `egress-proxy`, reached from the RunPod pod over Tailscale.
  Not yet set up; dedicated-vs-shared-instance not yet decided.

## Bootstrap

Not yet run. Target toolchain/packages: not yet determined — still
pending a read of `snngineV4_cloud`'s actual dependencies
(requirements/pyproject/README) rather than the blueprint's generic
guessed package list.
