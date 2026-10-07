#!/bin/bash
# First-boot provisioning for the Pi, delivered through cloud-init user-data
# by setups/pi-smoke-test/pi_smoke_test_flash.py --provision-script.
#
# Structure borrowed from the sandbox repo's Dockerfile/entrypoint habits:
# preflight checks that refuse to run on an untested system, one function per
# module with one result line each, an active check after every install (it
# fails loudly, with the likely cause, instead of trusting an exit code), and
# a verified scrub of a credential from a file other users can read.
#
# Steps in here were tested by hand on the Pi (2026-10-04). Deliberately NOT
# here: any VPN config or key (the Pi is meant to hold credentials; they are
# pushed over SSH into root-only files, never carried on the card), DNS through
# the tunnel, starting the tunnel at boot, Docker (all untested or undecided).
#
# Safe to re-run: a marker file, written only when every step succeeded
# (including the scrub), ends later runs. Every wait is bounded, and a failure
# is logged and exits non-zero without touching anything else. The systemd unit
# that the flash script installs (pi-provision.service) restarts a failed run
# every 5 minutes, a bounded number of times per boot, and again on each boot,
# until the marker exists.

set -euo pipefail

LOG=/var/log/pi-provision.log
MARK=/var/lib/pi-provision.done
BOOT_NET=/boot/firmware/network-config
NETPLAN_DIR=/etc/netplan
EXPECT_ARCH=aarch64
EXPECT_DEBIAN=13
SCRUB_PLACEHOLDER="scrubbed-after-first-boot"

log() { echo "$(date -Is) $*"; }

# Refuse an untested system, like the sandbox Dockerfile refusing a wrong UID.
preflight() {
    if [ "$(id -u)" -ne 0 ]; then
        log "FAILED preflight: must run as root"; return 1
    fi
    local arch
    arch=$(uname -m)
    if [ "$arch" != "$EXPECT_ARCH" ]; then
        log "FAILED preflight: architecture is $arch, only $EXPECT_ARCH was tested"; return 1
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    if [ "${ID:-}" != "debian" ] || [ "${VERSION_ID:-}" != "$EXPECT_DEBIAN" ]; then
        log "FAILED preflight: OS is ${ID:-?} ${VERSION_ID:-?}, only debian $EXPECT_DEBIAN was tested"; return 1
    fi
    log "preflight ok: $arch, debian $VERSION_ID"
}

# The Pi's clock is wrong for a few seconds after boot; apt rejects a Release
# file that is "not valid yet", so wait (bounded) for time sync.
wait_for_clock() {
    local _
    for _ in $(seq 1 60); do
        [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ] && break
        sleep 3
    done
    log "clock synced: $(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown)"
}

# wireguard-tools from the Debian archive (it floats by choice, like the
# sandbox's apt packages; the installed version is logged). No recommended
# packages: resolvconf could fight NetworkManager over /etc/resolv.conf.
module_wireguard() {
    export DEBIAN_FRONTEND=noninteractive
    local ok=0 attempt
    # A retry after a later step failed must not need the network again.
    if wg --version > /dev/null 2>&1 && modprobe -n wireguard 2> /dev/null; then
        log "module wireguard: already installed ($(dpkg-query -W -f='${Version}' wireguard-tools))"
        return 0
    fi
    for attempt in 1 2 3 4 5; do
        if timeout 300 apt-get update \
            && timeout 600 apt-get install -y --no-install-recommends wireguard-tools; then
            ok=1
            break
        fi
        log "apt attempt $attempt failed; retrying in 20 s"
        sleep 20
    done
    if [ "$ok" -ne 1 ]; then
        log "FAILED module wireguard: apt could not install wireguard-tools after 5 attempts (no internet, or the archive is unreachable?)"
        return 1
    fi
    if ! wg --version > /dev/null; then
        log "FAILED module wireguard: installed, but 'wg' does not run"; return 1
    fi
    # Dry run: shows whether the kernel module would load, without loading it.
    if ! modprobe -n wireguard; then
        log "FAILED module wireguard: the kernel has no wireguard module"; return 1
    fi
    log "module wireguard: ok ($(dpkg-query -W -f='${Version}' wireguard-tools))"
}

# The Wi-Fi password is needed on the FAT boot partition only until cloud-init
# has applied it (anyone holding the card can read that partition). NetworkManager
# keeps its own copy in a root-only netplan file, so after cloud-init is done the
# plain-text copy is replaced and then checked, the way the sandbox's repo-loader
# rewrites and greps for a leaked token. Skipped, with a warning, if the persistent
# root-only copy is not there, so Wi-Fi is never left without any copy.
scrub_wifi_password() {
    if [ ! -f "$BOOT_NET" ]; then
        log "scrub: no $BOOT_NET, nothing to do"; return 0
    fi
    if ! grep -qE '^[[:space:]]+password:' "$BOOT_NET"; then
        log "scrub: no Wi-Fi password in $BOOT_NET"; return 0
    fi
    # Exit 0 is "done"; exit 2 is "done, with recoverable warnings" (Pi OS always
    # reports one: the missing cc_netplan_nm_patch module), which is fine here.
    # Anything else (1 = error, 124 = timeout) skips the scrub.
    local rc=0
    timeout 300 cloud-init status --wait > /dev/null 2>&1 || rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then
        log "WARNING scrub: cloud-init status exited $rc (not done or failed); scrub not done, will be retried"; return 1
    fi
    if ! grep -qs 'wlan0' "$NETPLAN_DIR"/90-NM-*.yaml 2> /dev/null; then
        log "WARNING scrub: no root-only netplan copy of the Wi-Fi profile found; leaving the password in $BOOT_NET, will be retried"
        return 1
    fi
    sed -i -E "s/^([[:space:]]+password:).*/\\1 \"$SCRUB_PLACEHOLDER\"/" "$BOOT_NET"
    if grep -E '^[[:space:]]+password:' "$BOOT_NET" | grep -vq "$SCRUB_PLACEHOLDER"; then
        log "FAILED scrub: a password line other than the placeholder is still in $BOOT_NET"; return 1
    fi
    log "scrub: Wi-Fi password replaced in $BOOT_NET (root-only copy kept in $NETPLAN_DIR)"
}

main() {
    umask 027
    exec >>"$LOG" 2>&1
    log "=== pi-provision start ==="
    if [ -e "$MARK" ]; then
        log "marker $MARK present, nothing to do"
        exit 0
    fi
    preflight
    wait_for_clock
    module_wireguard
    scrub_wifi_password
    touch "$MARK"
    log "=== pi-provision done ==="
}

# Sourcing the file (for tests) defines the functions without running them.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
