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
KEYSTORE_LABEL=PIKEYS
KEYSTORE_MOUNT=/mnt/pi-keys
KEYSTORE_MANIFEST=$KEYSTORE_MOUNT/links.conf

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

# A general credential store on a USB stick labelled KEYSTORE_LABEL, so a
# re-flash of the SD card never loses what is on it. The stick is mounted by
# label (nofail: a Pi booted without it still starts). Its top-level file
# links.conf says what to link where, one entry per line:
#     <folder on the stick>  <absolute target path on the Pi>
# e.g. "wireguard /etc/wireguard". Nothing in this script knows what the
# folders hold, so new credentials need only a new line (and folder) on the
# stick. A missing stick or manifest is not an error: it is logged and skipped,
# and `pi-firstboot.sh keystore` can be run later.

# One manifest entry. Never overwrites anything on the Pi that has content: an
# existing real directory moves onto the stick only if the stick's folder is
# empty, and a populated one on both sides is left for a human to decide.
keystore_link() {
    local sub=$1 target=$2 dir="$KEYSTORE_MOUNT/$1"
    if ! [[ "$sub" =~ ^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$ ]] || [[ "$sub/" == *"../"* ]]; then
        log "FAILED keystore: bad folder name '$sub' in $KEYSTORE_MANIFEST"; return 1
    fi
    if ! [[ "$target" =~ ^(/[A-Za-z0-9._-]+){2,}$ ]] || [[ "$target/" == *"/../"* ]] \
        || [[ "$target" =~ ^/(boot|proc|sys|dev|run|usr|bin|sbin|lib|lib64|var/lib/dpkg)(/|$) ]]; then
        log "FAILED keystore: target '$target' is not a safe absolute path (at least two levels, not a system directory)"; return 1
    fi
    install -d -m 700 -o root -g root "$dir"
    if [ -L "$target" ]; then
        if [ "$(readlink "$target")" != "$dir" ]; then
            log "FAILED keystore: $target is a link to $(readlink "$target"), expected $dir"; return 1
        fi
    elif [ -d "$target" ]; then
        if [ -n "$(ls -A "$target")" ]; then
            if [ -n "$(ls -A "$dir")" ]; then
                log "FAILED keystore: $target and the stick folder '$sub' both hold files; not touching either"; return 1
            fi
            cp -a "$target"/. "$dir"/ || { log "FAILED keystore: could not copy $target onto the stick"; return 1; }
            log "keystore: moved the existing files of $target onto the stick"
        fi
        rm -rf "$target"
        ln -s "$dir" "$target"
    elif [ -e "$target" ]; then
        log "FAILED keystore: $target exists and is not a directory or the expected link"; return 1
    else
        mkdir -p "$(dirname "$target")"
        ln -s "$dir" "$target"
    fi
    if [ ! -d "$target" ]; then
        log "FAILED keystore: $target does not resolve to a directory after linking"; return 1
    fi
    log "keystore: $target -> $dir ($(find "$dir" -maxdepth 1 -type f | wc -l) file(s))"
}

module_keystore() {
    local dev sub target _rest rc=0
    dev=$(blkid -L "$KEYSTORE_LABEL" 2> /dev/null || true)
    if [ -z "$dev" ]; then
        log "keystore: no stick labelled $KEYSTORE_LABEL, skipping"; return 0
    fi
    mkdir -p "$KEYSTORE_MOUNT"
    if ! grep -qE "^LABEL=$KEYSTORE_LABEL[[:space:]]" /etc/fstab; then
        echo "LABEL=$KEYSTORE_LABEL $KEYSTORE_MOUNT ext4 defaults,nofail,x-systemd.device-timeout=10 0 2" >> /etc/fstab
        systemctl daemon-reload
    fi
    if ! mountpoint -q "$KEYSTORE_MOUNT"; then
        mount "$KEYSTORE_MOUNT" || { log "FAILED keystore: could not mount $dev on $KEYSTORE_MOUNT"; return 1; }
    fi
    if [ ! -f "$KEYSTORE_MANIFEST" ]; then
        log "keystore: $dev mounted, but no $KEYSTORE_MANIFEST, nothing to link"; return 0
    fi
    while read -r sub target _rest; do
        case "$sub" in ''|'#'*) continue ;; esac
        keystore_link "$sub" "$target" || rc=1
    done < "$KEYSTORE_MANIFEST"
    return "$rc"
}

# Explicit, never automatic: put an ext4 filesystem labelled KEYSTORE_LABEL on
# a whole device (old signatures wiped first) and seed links.conf with the
# WireGuard entry. Refuses a mounted device and (unless FORCE=1) one that
# already carries a filesystem.
format_keystore() {
    local dev=${1:-} tmp
    if [ -z "$dev" ] || [ ! -b "$dev" ]; then
        log "FAILED format: give a block device, e.g. /dev/sda"; return 1
    fi
    if lsblk -nro MOUNTPOINTS "$dev" | grep -q .; then
        log "FAILED format: $dev (or a partition of it) is mounted"; return 1
    fi
    if [ "${FORCE:-0}" != "1" ] && [ -n "$(lsblk -nro FSTYPE "$dev" | tr -d '[:space:]')" ]; then
        log "FAILED format: $dev already carries a filesystem; set FORCE=1 to overwrite it"; return 1
    fi
    wipefs -a "$dev"
    mkfs.ext4 -F -L "$KEYSTORE_LABEL" "$dev"
    tmp=$(mktemp -d)
    mount "$dev" "$tmp"
    printf '%s\n' '# <folder on this stick>  <absolute target path on the Pi>' 'wireguard /etc/wireguard' > "$tmp/links.conf"
    chmod 600 "$tmp/links.conf"
    umount "$tmp"
    rmdir "$tmp"
    log "format: $dev is now ext4, label $KEYSTORE_LABEL, links.conf seeded"
}

main() {
    umask 027
    exec >>"$LOG" 2>&1
    case "${1:-}" in
        keystore) log "=== keystore only ==="; preflight; module_keystore; return ;;
        format-keystore) log "=== format keystore ==="; preflight; format_keystore "${2:-}"; return ;;
    esac
    log "=== pi-provision start ==="
    if [ -e "$MARK" ]; then
        log "marker $MARK present, nothing to do"
        exit 0
    fi
    preflight
    wait_for_clock
    module_wireguard
    module_keystore
    scrub_wifi_password
    touch "$MARK"
    log "=== pi-provision done ==="
}

# Sourcing the file (for tests) defines the functions without running them.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
