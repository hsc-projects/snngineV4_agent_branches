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
# pushed over SSH into root-only files, never carried on the card). Docker
# (module_docker) was added and tested by hand on the Pi on 2026-10-11, then
# turned into the module below; the module itself is tested only by running
# `pi-firstboot.sh docker` on that Pi and on a fresh flash.
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
# Docker's apt signing key, checked against its published fingerprint before it is
# trusted (https://docs.docker.com/engine/install/debian/).
DOCKER_KEY_FPR=9DC858229FC7DD38854AE2D88D81803C0EBFCD88
DOCKER_KEY=/etc/apt/keyrings/docker.asc
DOCKER_SOURCES=/etc/apt/sources.list.d/docker.sources
DOCKER_PACKAGES=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
# Tailscale's apt signing key. Its docs publish no fingerprint, so this one is the
# primary-key fingerprint seen on 2026-10-11 (trust on first use over TLS); a mismatch
# later means the key changed and needs a look, not a silent edit of this line.
TAILSCALE_KEY_FPR=2596A99EAAB33821893C0A79458CA832957F5868
TAILSCALE_KEY=/usr/share/keyrings/tailscale-archive-keyring.gpg
TAILSCALE_LIST=/etc/apt/sources.list.d/tailscale.list
# The node's identity (its state file) is copied onto the stick after the join and put
# back on a fresh flash, so a re-flash comes back as the same node without a new login.
# The card stays the primary copy: a Pi without the stick still joins the tailnet.
TAILSCALE_STATE=/var/lib/tailscale/tailscaled.state
TAILSCALE_BACKUP=$KEYSTORE_MOUNT/tailscale/tailscaled.state
# Keyholder (setups/pi-rationale.md, item 20): high-value secrets live on the stick only
# as passphrase-encrypted files and are decrypted into RAM (/run/pi-secrets) on request.
KEYHOLDER_USER=pikeys
KEYHOLDER_UNLOCK=/usr/local/sbin/pi-unlock
KEYHOLDER_ADD=/usr/local/sbin/pi-secret-add
KEYHOLDER_SUDOERS=/etc/sudoers.d/pikeys
KEYHOLDER_SSHD=/etc/ssh/sshd_config.d/10-pikeys.conf

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

# git from the Debian archive (floats by choice; the installed version is logged), so the
# Pi can hold working copies (commit, pull, push). No recommended packages.
module_git() {
    export DEBIAN_FRONTEND=noninteractive
    local ok=0 attempt
    if git --version > /dev/null 2>&1; then
        log "module git: already installed ($(git --version))"
        return 0
    fi
    for attempt in 1 2 3 4 5; do
        if timeout 300 apt-get update \
            && timeout 600 apt-get install -y --no-install-recommends git; then
            ok=1
            break
        fi
        log "apt attempt $attempt failed; retrying in 20 s"
        sleep 20
    done
    if [ "$ok" -ne 1 ]; then
        log "FAILED module git: apt could not install git after 5 attempts (no internet, or the archive is unreachable?)"
        return 1
    fi
    if ! git --version > /dev/null; then
        log "FAILED module git: installed, but 'git' does not run"; return 1
    fi
    log "module git: ok ($(git --version))"
}

# Bring the WireGuard tunnel up at every boot, with wg-quick's own systemd
# unit. The config lives on the stick, so the unit requires the stick's mount
# (no stick: the unit fails cleanly and the Pi still boots and stays reachable,
# which is also the way out if a tunnel ever blocks access) and retries every 30 s
# while the network is not ready. Only acts when exactly one config is present.
# A failure to start the tunnel is logged but never fails provisioning.
module_wireguard_autostart() {
    local confs name
    confs=$(find /etc/wireguard/ -maxdepth 1 -name '*.conf' 2> /dev/null | sort)
    if [ -z "$confs" ]; then
        log "wireguard autostart: no config in /etc/wireguard, skipping"; return 0
    fi
    if [ "$(echo "$confs" | wc -l)" -ne 1 ]; then
        log "WARNING wireguard autostart: more than one config in /etc/wireguard, not choosing one"; return 0
    fi
    name=$(basename "$confs" .conf)
    if ! [[ "$name" =~ ^[A-Za-z0-9_-]{1,15}$ ]]; then
        log "WARNING wireguard autostart: '$name' is not a valid interface name, skipping"; return 0
    fi
    install -d /etc/systemd/system/wg-quick@.service.d
    cat > /etc/systemd/system/wg-quick@.service.d/pi-provision.conf <<DROPIN
[Unit]
RequiresMountsFor=$KEYSTORE_MOUNT

[Service]
Restart=on-failure
RestartSec=30
# wg-quick's policy rules sit at the front when the tunnel comes up after
# tailscaled (the kernel numbers them just below the existing rules), which sends
# unmarked replies to tailnet addresses into the tunnel (so SSH over the tailnet
# times out). These rules put tailnet-bound traffic first whatever the order. They stay
# after a stop on purpose: a stop that cannot read the config (the stick is gone) leaves
# the interface and its routing behind, and the rules are harmless without a tunnel.
# They must NOT exist when the tunnel comes up: the kernel numbers wg-quick's rules just
# below the lowest existing rule, so a leftover 5200 would put them ahead of it. Hence
# the removal before the start and the add after it.
ExecStartPre=-/usr/sbin/ip rule del pref 5200 to 100.64.0.0/10 lookup 52
ExecStartPre=-/usr/sbin/ip -6 rule del pref 5200 to fd7a:115c:a1e0::/48 lookup 52
ExecStartPost=-/usr/sbin/ip rule add pref 5200 to 100.64.0.0/10 lookup 52
ExecStartPost=-/usr/sbin/ip -6 rule add pref 5200 to fd7a:115c:a1e0::/48 lookup 52
DROPIN
    chmod 644 /etc/systemd/system/wg-quick@.service.d/pi-provision.conf
    # A device that connects or reconnects after the tunnel is up (a cable
    # replug, a lease failure, a Wi-Fi rejoin) gets its network's own DNS from
    # NetworkManager, outside the tunnel. The tunnel's PostUp hook writes its
    # resolver to /run/pi-wg-dns/<interface> (PostDown removes it); this
    # dispatcher script re-applies that resolver to any such device, and does
    # nothing when no tunnel file exists.
    install -d /etc/NetworkManager/dispatcher.d
    cat > /etc/NetworkManager/dispatcher.d/90-pi-wg-dns <<'DISPATCH'
#!/bin/bash
dev=$1
case "${2:-}" in up|dhcp4-change|dhcp6-change|reapply) ;; *) exit 0 ;; esac
[[ "$dev" =~ ^(eth|wlan) ]] || exit 0
for f in /run/pi-wg-dns/*; do
    [ -f "$f" ] || continue
    dns=$(head -n 1 "$f")
    applied=$(nmcli -t -f IP4.DNS device show "$dev" | cut -d: -f2- | paste -sd,)
    [ "$applied" = "$dns" ] && continue
    nmcli device modify "$dev" ipv4.dns "$dns" ipv4.ignore-auto-dns yes ipv6.ignore-auto-dns yes
done
exit 0
DISPATCH
    chmod 755 /etc/NetworkManager/dispatcher.d/90-pi-wg-dns
    chown root:root /etc/NetworkManager/dispatcher.d/90-pi-wg-dns
    systemctl daemon-reload
    systemctl enable "wg-quick@$name.service" || { log "FAILED wireguard autostart: could not enable wg-quick@$name"; return 1; }
    systemctl start --no-block "wg-quick@$name.service" || true
    log "wireguard autostart: wg-quick@$name enabled at boot"
}

# Docker Engine from Docker's own apt repository (the Debian docker.io package is
# older and has no buildx or Compose v2 plugin; the sandbox repo uses both).
# Floats within the repo, like the other apt packages; the installed versions are
# logged. No user is added to the docker group (membership is root-equivalent).
# Installing iptables as a dependency was tested alongside the WireGuard tunnel:
# tunnel, DNS and container egress through the tunnel all kept working.
module_docker() {
    export DEBIAN_FRONTEND=noninteractive
    local tmp fpr attempt ok=0 codename
    # A retry after a later step failed must not need the network again.
    if [ -f "$DOCKER_SOURCES" ] && dpkg-query -W "${DOCKER_PACKAGES[@]}" > /dev/null 2>&1; then
        log "module docker: already installed ($(dpkg-query -W -f='${Version}' docker-ce))"
    else
        for attempt in 1 2 3 4 5; do
            if timeout 600 apt-get install -y --no-install-recommends ca-certificates curl gnupg; then
                ok=1; break
            fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        if [ "$ok" -ne 1 ]; then
            log "FAILED module docker: could not install ca-certificates, curl and gnupg (no internet?)"; return 1
        fi
        install -m 0755 -d /etc/apt/keyrings
        tmp=$(mktemp)
        if ! curl -fsSL --max-time 60 https://download.docker.com/linux/debian/gpg -o "$tmp"; then
            rm -f "$tmp"; log "FAILED module docker: could not download Docker's signing key"; return 1
        fi
        fpr=$(gpg --homedir "$(mktemp -d)" --show-keys --with-colons "$tmp" 2> /dev/null | awk -F: '$1=="fpr"{print $10; exit}')
        if [ "$fpr" != "$DOCKER_KEY_FPR" ]; then
            rm -f "$tmp"; log "FAILED module docker: signing key fingerprint is '${fpr:-none}', expected $DOCKER_KEY_FPR; not trusting it"; return 1
        fi
        install -m 0644 "$tmp" "$DOCKER_KEY"
        rm -f "$tmp"
        # shellcheck disable=SC1091
        codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
        printf 'Types: deb\nURIs: https://download.docker.com/linux/debian\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: %s\n' \
            "$codename" "$(dpkg --print-architecture)" "$DOCKER_KEY" > "$DOCKER_SOURCES"
        ok=0
        for attempt in 1 2 3 4 5; do
            if timeout 300 apt-get update \
                && timeout 900 apt-get install -y --no-install-recommends "${DOCKER_PACKAGES[@]}"; then
                ok=1; break
            fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        if [ "$ok" -ne 1 ]; then
            log "FAILED module docker: apt could not install ${DOCKER_PACKAGES[*]} after 5 attempts (no internet, or Docker's repository is unreachable?)"; return 1
        fi
    fi
    # Active checks: the daemon answers, and both plugins run. (No image is pulled.)
    systemctl enable --now docker.service > /dev/null 2>&1 || true
    if ! timeout 60 docker info > /dev/null 2>&1; then
        log "FAILED module docker: installed, but the daemon does not answer 'docker info'"; return 1
    fi
    if ! docker compose version > /dev/null 2>&1 || ! docker buildx version > /dev/null 2>&1; then
        log "FAILED module docker: the compose or buildx plugin does not run"; return 1
    fi
    log "module docker: ok (engine $(docker version -f '{{.Server.Version}}' 2> /dev/null), $(docker compose version --short), buildx $(docker buildx version | awk '{print $2}'))"
}

# Copy the joined node's state onto the stick (root only, mode 600). Needs the stick
# mounted and the node joined; does nothing otherwise. Run it after the interactive
# join (`pi-firstboot.sh tailscale-backup`); the tailscale module also runs it.
tailscale_identity_backup() {
    if ! mountpoint -q "$KEYSTORE_MOUNT"; then
        log "tailscale identity: stick not mounted, no backup made"; return 0
    fi
    if ! tailscale ip -4 > /dev/null 2>&1 || [ ! -f "$TAILSCALE_STATE" ]; then
        log "tailscale identity: node not joined, no backup made"; return 0
    fi
    if cmp -s "$TAILSCALE_STATE" "$TAILSCALE_BACKUP"; then
        log "tailscale identity: the backup on the stick is current"; return 0
    fi
    install -d -m 0700 -o root -g root "$(dirname "$TAILSCALE_BACKUP")"
    install -m 0600 -o root -g root "$TAILSCALE_STATE" "$TAILSCALE_BACKUP" \
        || { log "FAILED tailscale identity: could not write $TAILSCALE_BACKUP"; return 1; }
    log "tailscale identity: node state backed up to the stick"
}

# On a fresh flash (daemon running, node not joined) with a backup on the stick: put the
# state back and restart the daemon, so the Pi returns as the same node. Never touches a
# node that is already joined. The old card must not run at the same time.
tailscale_identity_restore() {
    local i st=
    for i in $(seq 1 10); do
        st=$(tailscale status --json 2> /dev/null | sed -n 's/.*"BackendState": *"\([A-Za-z]*\)".*/\1/p' | head -n 1)
        [ -n "$st" ] && [ "$st" != NoState ] && break
        sleep 2
    done
    [ "$st" = NeedsLogin ] || return 0
    if ! mountpoint -q "$KEYSTORE_MOUNT" || [ ! -f "$TAILSCALE_BACKUP" ]; then return 0; fi
    log "tailscale identity: not joined, restoring the node state from the stick"
    systemctl stop tailscaled.service
    install -d -m 0700 -o root -g root "$(dirname "$TAILSCALE_STATE")"
    install -m 0600 -o root -g root "$TAILSCALE_BACKUP" "$TAILSCALE_STATE" \
        || { systemctl start tailscaled.service; log "FAILED tailscale identity: could not restore the state"; return 1; }
    systemctl start tailscaled.service
    for i in $(seq 1 30); do
        tailscale ip -4 > /dev/null 2>&1 && { log "tailscale identity: restored, joined as $(tailscale ip -4 | head -n 1)"; return 0; }
        sleep 2
    done
    log "WARNING tailscale identity: restored the state but the node did not join (removed in the admin console? then delete $TAILSCALE_STATE, restart tailscaled and join again)"
}

# Tailscale from its own apt repository. Installs and enables the daemon only: joining
# the tailnet is interactive (`sudo tailscale up --accept-dns=false --hostname=pi-host
# --advertise-tags=tag:pi`, approved in the maintainer's browser; the tag must be owned
# in the tailnet policy, see tailscale-policy.hujson, and a device that authenticates
# with a tag has no key expiry), so no auth key ever sits on the card. A node
# that is not joined is logged, not an error. `--accept-dns=false` keeps DNS with the
# tunnel's resolver and the NetworkManager dispatcher. Tested beside the Proton tunnel
# on 2026-10-11 (tunnel, DNS and routes unchanged; Tailscale's own traffic is marked
# and leaves by the main routing table, so it does not depend on the tunnel).
module_tailscale() {
    export DEBIAN_FRONTEND=noninteractive
    local tmp lst fpr attempt ok=0
    if [ -f "$TAILSCALE_LIST" ] && dpkg-query -W tailscale > /dev/null 2>&1; then
        log "module tailscale: already installed ($(dpkg-query -W -f='${Version}' tailscale))"
    else
        for attempt in 1 2 3 4 5; do
            if timeout 600 apt-get install -y --no-install-recommends ca-certificates curl gnupg; then
                ok=1; break
            fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        if [ "$ok" -ne 1 ]; then
            log "FAILED module tailscale: could not install ca-certificates, curl and gnupg (no internet?)"; return 1
        fi
        tmp=$(mktemp); lst=$(mktemp)
        if ! curl -fsSL --max-time 60 https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg -o "$tmp" \
            || ! curl -fsSL --max-time 60 https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list -o "$lst"; then
            rm -f "$tmp" "$lst"; log "FAILED module tailscale: could not download Tailscale's signing key or source list"; return 1
        fi
        fpr=$(gpg --homedir "$(mktemp -d)" --show-keys --with-colons "$tmp" 2> /dev/null | awk -F: '$1=="fpr"{print $10; exit}')
        if [ "$fpr" != "$TAILSCALE_KEY_FPR" ]; then
            rm -f "$tmp" "$lst"; log "FAILED module tailscale: signing key fingerprint is '${fpr:-none}', expected $TAILSCALE_KEY_FPR; not trusting it"; return 1
        fi
        # The list file must only point apt at Tailscale's repository with this keyring.
        if [ "$(grep -vcE '^[[:space:]]*(#|$)' "$lst")" -ne 1 ] \
            || ! grep -qE "^deb \[signed-by=$TAILSCALE_KEY\] https://pkgs\.tailscale\.com/stable/debian trixie main$" "$lst"; then
            rm -f "$tmp" "$lst"; log "FAILED module tailscale: the source list is not the expected single line; not installing it"; return 1
        fi
        install -d -m 0755 /usr/share/keyrings
        install -m 0644 "$tmp" "$TAILSCALE_KEY"
        install -m 0644 "$lst" "$TAILSCALE_LIST"
        rm -f "$tmp" "$lst"
        ok=0
        for attempt in 1 2 3 4 5; do
            if timeout 300 apt-get update \
                && timeout 600 apt-get install -y --no-install-recommends tailscale; then
                ok=1; break
            fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        if [ "$ok" -ne 1 ]; then
            log "FAILED module tailscale: apt could not install tailscale after 5 attempts"; return 1
        fi
    fi
    systemctl enable --now tailscaled.service > /dev/null 2>&1 || true
    tailscale_identity_restore || true
    if ! tailscale version > /dev/null 2>&1 || [ "$(systemctl is-active tailscaled)" != "active" ]; then
        log "FAILED module tailscale: installed, but the tailscale CLI or tailscaled does not run"; return 1
    fi
    if tailscale ip -4 > /dev/null 2>&1; then
        log "module tailscale: ok ($(tailscale version | head -n 1)), joined as $(tailscale ip -4 | head -n 1)"
        tailscale_identity_backup || true
    else
        log "module tailscale: ok ($(tailscale version | head -n 1)), NOT JOINED: run 'sudo tailscale up --accept-dns=false --hostname=pi-host --advertise-tags=tag:pi' and approve the link"
    fi
}

# Recover from a stick that was pulled and plugged back in, without a reboot. systemd
# unmounts the stick when it disappears and stops what depends on it (the tunnel), but it
# does not mount it again when it comes back. A udev rule starts a small service when a
# device labelled $KEYSTORE_LABEL appears; the service mounts it and starts the enabled
# tunnel units. Idempotent (a second event finds everything running), and rate-limited so
# a stick that keeps bouncing cannot restart the tunnel in a loop.
module_keystore_hotplug() {
    install -d /usr/local/sbin
    cat > /usr/local/sbin/pi-keystore-recover <<'RECOVER'
#!/bin/bash
# Mount the credential stick if it is not mounted, then start the enabled tunnel units.
MNT=/mnt/pi-keys
sleep 2
if ! mountpoint -q "$MNT"; then
    systemctl reset-failed "$(systemd-escape -p --suffix=mount "$MNT")" 2> /dev/null || true
    mount "$MNT" || { logger -t pi-keystore "could not mount $MNT"; exit 1; }
fi
for f in /etc/systemd/system/multi-user.target.wants/wg-quick@*.service; do
    [ -e "$f" ] || continue
    u=$(basename "$f")
    name=${u#wg-quick@}; name=${name%.service}
    # Already up (the rule also fires when the stick is found at boot): leave it alone.
    systemctl is-active --quiet "$u" && continue
    # A stop that could not read the config (the stick was gone) leaves the interface and
    # its routing behind, and wg-quick up refuses to run over it. With the config readable
    # again, take it down properly first.
    if ip link show "$name" > /dev/null 2>&1; then
        wg-quick down "$name" > /dev/null 2>&1 || ip link delete dev "$name" 2> /dev/null || true
    fi
    systemctl reset-failed "$u" 2> /dev/null || true
    systemctl restart "$u" || logger -t pi-keystore "could not start $u"
done
ip rule add pref 5200 to 100.64.0.0/10 lookup 52 2> /dev/null || true
ip -6 rule add pref 5200 to fd7a:115c:a1e0::/48 lookup 52 2> /dev/null || true
logger -t pi-keystore "stick mounted, tunnel start requested"
RECOVER
    chmod 755 /usr/local/sbin/pi-keystore-recover
    cat > /etc/systemd/system/pi-keystore-recover.service <<UNIT
[Unit]
Description=Mount the credential stick and start its tunnel when it is plugged in
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/pi-keystore-recover
UNIT
    cat > /etc/udev/rules.d/90-pi-keystore.rules <<RULE
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="$KEYSTORE_LABEL", TAG+="systemd", ENV{SYSTEMD_WANTS}+="pi-keystore-recover.service"
RULE
    chmod 644 /etc/systemd/system/pi-keystore-recover.service /etc/udev/rules.d/90-pi-keystore.rules
    systemctl daemon-reload
    udevadm control --reload
    log "module keystore hotplug: ok (a stick labelled $KEYSTORE_LABEL mounts and starts the tunnel when plugged in)"
}

# The user for Claude Code: unprivileged (no sudo, no password), so a phone key that opens it
# never opens the admin account. What it needs from the stick:
#   claude/authorized_keys   the public keys allowed to log in as it (sshd reads this file
#                            for that user only, like the keyholder user; no stick, no login)
#   claude/config            CLAUDE_CONFIG_DIR: the login, settings and .claude.json, so a
#                            re-flash keeps the login (set in the user's .bashrc only while the
#                            stick is mounted; without it `claude` refuses to start rather than
#                            log in a second time on the card)
#   claude/bin/claude-<version>   a cached copy of the binary (see claude_install_binary)
# The binary (~255 MB) is installed on the card by Anthropic's installer, run as this user; if
# the download fails (no network, region block), the cached copy on the stick is installed
# instead. tmux and the project clones stay on the card. `/login` stays manual, once per stick.
CLAUDE_USER=claude
CLAUDE_SSHD=/etc/ssh/sshd_config.d/20-claude.conf
# Puts a working ~/.local/bin/claude on the card. First choice: the official installer (up to 3
# attempts); fallback: the newest binary cached on the stick. After an installer success, the
# installed binary is cached on the stick (older cached versions removed).
claude_install_binary() {
    local home="$1" bin attempt cache ver=""
    bin="$home/.local/bin/claude"
    cache="$KEYSTORE_MOUNT/claude/bin"
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$bin" --version > /dev/null 2>&1; then
        for attempt in 1 2 3; do
            if timeout 600 runuser -u "$CLAUDE_USER" -- env HOME="$home" bash -c \
                'curl -fsSL https://claude.ai/install.sh | bash' > /dev/null 2>&1; then
                break
            fi
            log "claude installer attempt $attempt failed; retrying in 20 s"; sleep 20
        done
    fi
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$bin" --version > /dev/null 2>&1; then
        local cached
        cached=$(ls -1 "$cache"/claude-* 2> /dev/null | sort -V | tail -n 1)
        if [ -n "$cached" ] && mountpoint -q "$KEYSTORE_MOUNT"; then
            ver=${cached##*/claude-}
            install -d -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" \
                "$home/.local/share/claude/versions" "$home/.local/bin"
            install -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$cached" \
                "$home/.local/share/claude/versions/$ver"
            ln -sfn "$home/.local/share/claude/versions/$ver" "$bin"
            chown -h "$CLAUDE_USER":"$CLAUDE_USER" "$bin"
            log "claude binary: installer failed; installed $ver from the stick's cache"
        else
            log "FAILED claude binary: installer failed and the stick has no cached copy"; return 1
        fi
    fi
    # Cache the installed binary on the stick when it is not there yet.
    if mountpoint -q "$KEYSTORE_MOUNT"; then
        ver=$(readlink -f "$bin"); ver=${ver##*/}
        if [ -n "$ver" ] && [ ! -f "$cache/claude-$ver" ]; then
            install -d -m 0755 -o root -g root "$cache"
            if install -m 0755 -o root -g root "$(readlink -f "$bin")" "$cache/claude-$ver.tmp"; then
                mv -f "$cache/claude-$ver.tmp" "$cache/claude-$ver"
                find "$cache" -maxdepth 1 -name 'claude-*' ! -name "claude-$ver" -delete
                log "claude binary: cached $ver on the stick"
            else
                rm -f "$cache/claude-$ver.tmp"; log "claude binary: could not cache $ver on the stick"
            fi
        fi
    fi
}
module_claude_user() {
    export DEBIAN_FRONTEND=noninteractive
    local home ak applied ok=0 attempt marker=">>> pi-claude (managed by pi-firstboot.sh)"
    if ! id "$CLAUDE_USER" > /dev/null 2>&1; then
        adduser --disabled-password --gecos '' "$CLAUDE_USER" > /dev/null \
            || { log "FAILED module claude user: could not create $CLAUDE_USER"; return 1; }
    fi
    if id -nG "$CLAUDE_USER" | tr ' ' '\n' | grep -qx -e sudo -e docker -e adm; then
        log "FAILED module claude user: $CLAUDE_USER is in a privileged group ($(id -nG "$CLAUDE_USER"))"; return 1
    fi
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    if ! command -v tmux > /dev/null 2>&1; then
        for attempt in 1 2 3 4 5; do
            if timeout 300 apt-get update && timeout 600 apt-get install -y --no-install-recommends tmux; then
                ok=1; break
            fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        if [ "$ok" -ne 1 ]; then
            log "FAILED module claude user: apt could not install tmux after 5 attempts"; return 1
        fi
    fi
    claude_install_binary "$home" || log "module claude user: no Claude Code binary; install it by hand as $CLAUDE_USER"
    if ! mountpoint -q "$KEYSTORE_MOUNT"; then
        log "module claude user: $CLAUDE_USER exists, but the stick is not mounted, so no key file or config directory was set up"
        return 0
    fi
    ak="$KEYSTORE_MOUNT/claude/authorized_keys"
    install -d -m 0755 -o root -g root "$KEYSTORE_MOUNT/claude"
    install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$KEYSTORE_MOUNT/claude/config"
    [ -f "$ak" ] || install -m 0640 -o root -g "$CLAUDE_USER" /dev/null "$ak"
    # A key already authorised on the card (set up by hand) moves to the stick's file.
    if [ ! -s "$ak" ] && [ -s "$home/.ssh/authorized_keys" ]; then
        grep '^ssh-' "$home/.ssh/authorized_keys" >> "$ak" || true
        log "module claude user: moved $(grep -c '^ssh-' "$ak") key(s) from $home/.ssh to the stick"
    fi
    chown root:"$CLAUDE_USER" "$ak"; chmod 0640 "$ak"
    install -d /etc/ssh/sshd_config.d
    cat > "$CLAUDE_SSHD" <<SSHDCONF
Match User $CLAUDE_USER
    AuthorizedKeysFile $ak
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowAgentForwarding no
    X11Forwarding no
SSHDCONF
    chmod 644 "$CLAUDE_SSHD"
    # Captured first: under pipefail, `grep -q` ending the pipe early would fail it with SIGPIPE.
    applied=$(sshd -T -C "user=$CLAUDE_USER,host=localhost,addr=127.0.0.1" 2> /dev/null) || applied=""
    if ! sshd -t 2> /dev/null || ! grep -qi "^authorizedkeysfile $ak" <<< "$applied"; then
        rm -f "$CLAUDE_SSHD"
        log "FAILED module claude user: sshd did not accept the key-file rule; removed it"; return 1
    fi
    systemctl reload ssh > /dev/null 2>&1 || systemctl reload sshd > /dev/null 2>&1 || true
    # The shell profile: PATH for the installer's launcher, and the config directory on the stick.
    touch "$home/.bashrc"; chown "$CLAUDE_USER":"$CLAUDE_USER" "$home/.bashrc"
    if ! grep -q "$marker" "$home/.bashrc"; then
        cat >> "$home/.bashrc" <<'PROFILE'

# >>> pi-claude (managed by pi-firstboot.sh)
export PATH="$HOME/.local/bin:$PATH"
if mountpoint -q /mnt/pi-keys; then
    export CLAUDE_CONFIG_DIR=/mnt/pi-keys/claude/config
else
    claude() { echo "The credential stick is not mounted: claude would start without its login. Plug it in (it mounts by itself)." >&2; return 1; }
fi
# <<< pi-claude
PROFILE
        chown "$CLAUDE_USER":"$CLAUDE_USER" "$home/.bashrc"
    fi
    log "module claude user: ok (user $CLAUDE_USER, $(grep -c '^ssh-' "$ak") key(s) in claude/authorized_keys, config dir on the stick)"
}

# Google Antigravity CLI (`agy`) for the same unprivileged user. It has no setting to relocate
# its state, so ~/.gemini is a symlink to claude/gemini on the stick (settings, MCP config,
# plugins, whatever login state it keeps there); with no stick the link dangles and agy cannot
# write state on the card. Binary: Google's installer (3 attempts), else the copy cached on the
# stick (claude/bin/agy; agy updates itself in the background, so the cache can be stale).
module_agy() {
    local home bin cache attempt gem
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module agy: no user $CLAUDE_USER (run claude-user first)"; return 1; }
    mountpoint -q "$KEYSTORE_MOUNT" || { log "module agy: the stick is not mounted; skipped"; return 0; }
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    bin="$home/.local/bin/agy"; cache="$KEYSTORE_MOUNT/claude/bin"; gem="$KEYSTORE_MOUNT/claude/gemini"
    install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$gem"
    if [ -d "$home/.gemini" ] && [ ! -L "$home/.gemini" ]; then
        cp -a "$home/.gemini/." "$gem/" && rm -rf "$home/.gemini"
    fi
    ln -sfn "$gem" "$home/.gemini"; chown -h "$CLAUDE_USER":"$CLAUDE_USER" "$home/.gemini"
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$bin" --version > /dev/null 2>&1; then
        for attempt in 1 2 3; do
            if timeout 600 runuser -u "$CLAUDE_USER" -- env HOME="$home" bash -c \
                'curl -fsSL https://antigravity.google/cli/install.sh | bash' > /dev/null 2>&1; then
                break
            fi
            log "agy installer attempt $attempt failed; retrying in 20 s"; sleep 20
        done
    fi
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$bin" --version > /dev/null 2>&1; then
        if [ -f "$cache/agy" ]; then
            install -d -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$home/.local/bin"
            install -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$cache/agy" "$bin"
            log "module agy: installer failed; installed agy from the stick's cache"
        else
            log "FAILED module agy: installer failed and the stick has no cached copy"; return 1
        fi
    elif [ ! -f "$cache/agy" ]; then
        install -d -m 0755 -o root -g root "$cache"
        install -m 0755 -o root -g root "$bin" "$cache/agy.tmp" && mv -f "$cache/agy.tmp" "$cache/agy"
    fi
    # The maintainer's laptop runs agy on the snngineV4 project in accept-edits mode with tool
    # permissions on always-proceed, access outside the workspace allowed, and that repo as its
    # only trusted workspace. agy's settings are global (the CLI has no per-project settings), so
    # on the Pi the global settings only trust the two repos and allow non-workspace access (agents
    # need ~/dump and /run/pi-secrets), while accept-edits and always-proceed (the flag
    # --dangerously-skip-permissions, decided by the maintainer on 2026-10-17) belong to
    # `agy-snngine`, the launcher for that project (SNNgine3D is added with --add-dir, as on the
    # laptop). Plain `agy` keeps asking before it runs a command.
    local proj="$home/dev/snngineV4_agent_branches" extra="$home/dev/SNNgine3D_agent_branches"
    runuser -u "$CLAUDE_USER" -- env HOME="$home" python3 - "$home/.gemini/antigravity-cli/settings.json" "$home" "$proj" "$extra" <<'PY' \
        || log "module agy: could not set the trusted workspaces"
import json, os, sys
p, home, *ws = sys.argv[1:]
os.makedirs(os.path.dirname(p), exist_ok=True)
d = json.load(open(p)) if os.path.exists(p) else {}
# agy trusts the home directory by itself on its first run; project-specific means it does not
t = [w for w in d.get("trustedWorkspaces", []) if w != home]
d["trustedWorkspaces"] = t
d["allowNonWorkspaceAccess"] = True
for w in ws:
    if w not in t:
        t.append(w)
tmp = p + ".tmp"
with open(tmp, "w") as f:
    json.dump(d, f, indent=2)
os.chmod(tmp, 0o600)
os.replace(tmp, p)
PY
    cat > /usr/local/bin/agy-snngine <<AGYSNN
#!/bin/bash
# Starts agy for the snngineV4 project the way the maintainer's laptop does: accept-edits mode,
# tool permissions always proceed (the maintainer's decision, 2026-10-17), SNNgine3D added.
# Written by pi-firstboot.sh (module_agy).
export PATH="\$HOME/.local/bin:\$PATH"
cd "$proj" || { echo "agy-snngine: $proj is missing (not cloned yet)" >&2; exit 1; }
exec agy --mode accept-edits --dangerously-skip-permissions --add-dir "$extra" "\$@"
AGYSNN
    chmod 755 /usr/local/bin/agy-snngine
    log "module agy: ok ($(runuser -u "$CLAUDE_USER" -- env HOME="$home" "$bin" --version 2> /dev/null | head -n 1); state in $gem; launcher agy-snngine)"
}

# Claude Code Remote Control as a service: `claude remote-control` (server mode) restarted by a
# small supervisor, so it survives reboots and network drops (server mode exits by itself after
# about 10 minutes without network). Modelled on the sandbox project's rc-supervisor.sh. It waits
# for the stick (the login and config live there) and backs off while there is no login. The
# permission mode is Claude Code's own default unless /etc/default/claude-rc sets
# CLAUDE_RC_PERMISSION_MODE.
module_claude_rc() {
    local home
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module claude rc: no user $CLAUDE_USER"; return 1; }
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    install -d -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$home/work"
    if mountpoint -q "$KEYSTORE_MOUNT" && [ ! -f "$KEYSTORE_MOUNT/claude/trusted-dirs" ]; then
        printf '# folders Claude Code trusts without asking, one per line (edit as root)\n%s\n' \
            "$home/work" > "$KEYSTORE_MOUNT/claude/trusted-dirs"
        chmod 644 "$KEYSTORE_MOUNT/claude/trusted-dirs"
    fi
    cat > /usr/local/sbin/claude-rc-supervisor <<'SUP'
#!/bin/bash
set -u
export CLAUDE_CONFIG_DIR=/mnt/pi-keys/claude/config
export PATH="$HOME/.local/bin:$PATH"
[ -f /etc/default/claude-rc ] && . /etc/default/claude-rc
log() { printf '[claude-rc] %s\n' "$*"; }
args=(remote-control --name "${CLAUDE_RC_NAME:-pi}" --capacity "${CLAUDE_RC_CAPACITY:-2}")
[ -n "${CLAUDE_RC_PERMISSION_MODE:-}" ] && args+=(--permission-mode "$CLAUDE_RC_PERMISSION_MODE")
while ! mountpoint -q /mnt/pi-keys; do sleep 10; done
# Workspace trust for the folders listed in the stick's claude/trusted-dirs (root-owned, so the
# agent cannot widen it): mark each existing one as trusted in the config's .claude.json.
if [ -r /mnt/pi-keys/claude/trusted-dirs ]; then
    python3 - "$CLAUDE_CONFIG_DIR/.claude.json" /mnt/pi-keys/claude/trusted-dirs <<'PY'
import json, os, sys
cfg, lst = sys.argv[1:3]
data = json.load(open(cfg)) if os.path.exists(cfg) else {}
proj = data.setdefault("projects", {})
for line in open(lst):
    p = line.strip()
    if p and not p.startswith("#") and os.path.isdir(p):
        proj.setdefault(p, {})["hasTrustDialogAccepted"] = True
tmp = cfg + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, cfg)
PY
fi
cd "$HOME/work" || exit 1
child=
trap 'log stopping; [ -n "$child" ] && kill "$child" 2>/dev/null; exit 0' TERM INT
delay=5
while :; do
    started=$SECONDS
    log "starting: claude ${args[*]}"
    claude "${args[@]}" < /dev/null &
    child=$!
    wait "$child"; rc=$?; child=
    ran=$((SECONDS - started))
    [ "$ran" -ge 60 ] && delay=5
    log "claude exited with status $rc after ${ran}s; restarting in ${delay}s"
    sleep "$delay" & child=$!; wait "$child"; child=
    delay=$((delay * 2)); [ "$delay" -gt 300 ] && delay=300
done
SUP
    chmod 755 /usr/local/sbin/claude-rc-supervisor
    cat > /etc/systemd/system/claude-rc.service <<UNIT
[Unit]
Description=Claude Code Remote Control (server mode) for $CLAUDE_USER
After=network-online.target
Wants=network-online.target

[Service]
User=$CLAUDE_USER
Environment=HOME=$home
ExecStart=/usr/local/sbin/claude-rc-supervisor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
    chmod 644 /etc/systemd/system/claude-rc.service
    systemctl daemon-reload
    systemctl enable --now claude-rc.service > /dev/null 2>&1 || { log "FAILED module claude rc: could not enable the service"; return 1; }
    log "module claude rc: ok (claude-rc.service enabled and started)"
}

# GitHub for the claude user: the `gh` CLI, with its login on the stick (GH_CONFIG_DIR is
# claude/gh there, so a re-flash keeps it and nothing is written to the card), and git using that
# login for https://github.com (a credential helper on the claude user). The git identity comes
# from the stick's claude/git-identity (line 1 name, line 2 email), so it is not in this script.
# The login itself is one browser sign-in from the phone or laptop (gh's device code); the scope
# is the maintainer's choice at that moment (full for now, narrower later: a fine-grained token
# or a deploy key would go in the keyholder). With the stick missing, `gh` refuses to run.
module_github() {
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module github: no user $CLAUDE_USER"; return 1; }
    mountpoint -q "$KEYSTORE_MOUNT" || { log "module github: the stick is not mounted; skipped"; return 0; }
    local home gh="$KEYSTORE_MOUNT/claude/gh" attempt ok=0 marker=">>> pi-github (managed by pi-firstboot.sh)" idf name email
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    if ! command -v gh > /dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        for attempt in 1 2 3 4 5; do
            if timeout 300 apt-get update && timeout 600 apt-get install -y --no-install-recommends gh; then ok=1; break; fi
            log "apt attempt $attempt failed; retrying in 20 s"; sleep 20
        done
        [ "$ok" -eq 1 ] || { log "FAILED module github: apt could not install gh after 5 attempts"; return 1; }
    fi
    install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$gh"
    touch "$home/.bashrc"; chown "$CLAUDE_USER":"$CLAUDE_USER" "$home/.bashrc"
    if ! grep -q "$marker" "$home/.bashrc"; then
        cat >> "$home/.bashrc" <<'PROFILE'

# >>> pi-github (managed by pi-firstboot.sh)
if mountpoint -q /mnt/pi-keys; then
    export GH_CONFIG_DIR=/mnt/pi-keys/claude/gh
else
    gh() { echo "The credential stick is not mounted: gh would write its login to the card. Plug it in (it mounts by itself)." >&2; return 1; }
fi
# <<< pi-github
PROFILE
        chown "$CLAUDE_USER":"$CLAUDE_USER" "$home/.bashrc"
    fi
    local git_as=(runuser -u "$CLAUDE_USER" -- env HOME="$home" git config --global)
    idf="$KEYSTORE_MOUNT/claude/git-identity"
    if [ -r "$idf" ]; then
        name=$(sed -n 1p "$idf"); email=$(sed -n 2p "$idf")
        [ -n "$name" ] && "${git_as[@]}" user.name "$name"
        [ -n "$email" ] && "${git_as[@]}" user.email "$email"
    fi
    "${git_as[@]}" --unset-all credential.https://github.com.helper 2> /dev/null || true
    "${git_as[@]}" --add credential.https://github.com.helper ""
    "${git_as[@]}" --add credential.https://github.com.helper "!GH_CONFIG_DIR=$gh /usr/bin/gh auth git-credential"
    log "module github: ok ($(gh --version | head -n 1); login and config on the stick in claude/gh; sign in with: gh auth login)"
}

# The SSH key agents use to reach RunPod pods, on the stick (claude/ssh/runpod_ed25519, plain, mode
# 600). It is its own key pair, made on the Pi, NOT the laptop's runpod-snngine key: that one is
# also the Pi's admin login (htm, passwordless sudo), so on the stick it would give every agent
# root. The public half has to be added to the RunPod account (RunPod console, Settings, SSH
# keys) before a new pod accepts it. The task scripts look for setups/.secrets/id_ed25519 in the
# repo, so that path (gitignored) is a symlink to the stick's key once the repo is cloned.
module_runpod_ssh() {
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module runpod ssh: no user $CLAUDE_USER"; return 1; }
    mountpoint -q "$KEYSTORE_MOUNT" || { log "module runpod ssh: the stick is not mounted; skipped"; return 0; }
    local home k d repo
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    d="$KEYSTORE_MOUNT/claude/ssh"; k="$d/runpod_ed25519"; repo="$home/dev/snngineV4_agent_branches"
    install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$d"
    if [ ! -f "$k" ]; then
        runuser -u "$CLAUDE_USER" -- ssh-keygen -q -t ed25519 -N '' -C "pi-claude-runpod" -f "$k" \
            || { log "FAILED module runpod ssh: ssh-keygen failed"; return 1; }
        log "module runpod ssh: made a new key pair on the stick; add $k.pub to the RunPod account"
    fi
    chmod 600 "$k"; chmod 644 "$k.pub"
    if [ -d "$repo/setups" ]; then
        install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$repo/setups/.secrets"
        for f in id_ed25519 id_ed25519.pub; do
            src="$k"; [ "$f" = id_ed25519.pub ] && src="$k.pub"
            if [ -e "$repo/setups/.secrets/$f" ] && [ ! -L "$repo/setups/.secrets/$f" ]; then
                log "module runpod ssh: $repo/setups/.secrets/$f is a real file; left alone"
            else
                ln -sfn "$src" "$repo/setups/.secrets/$f"; chown -h "$CLAUDE_USER":"$CLAUDE_USER" "$repo/setups/.secrets/$f"
            fi
        done
    fi
    log "module runpod ssh: ok ($(ssh-keygen -lf "$k.pub" | cut -d' ' -f2); on the stick in claude/ssh)"
}

# Cloud drives (rclone), one way of working for Google Drive, Dropbox, OneDrive, Mega and Proton
# Drive (setups/pi-rationale.md, item 23). `pi-cloud` (below) only ever copies, only inside the
# Pi's own folder (snngine-pi) on each drive, and each login is confined as far as the provider
# allows (Drive: scope drive.file; Dropbox: an App-folder app of the maintainer's own; OneDrive,
# Mega and Proton have no such scope, so they use dedicated accounts). The logins live in an
# rclone-encrypted config on the stick (cloud/rclone.conf); its passphrase is the keyholder
# secret rclone_config_pass (read by the claude user after an unlock from the phone), or, when
# `pi-cloud auto on` was run, a file on the stick (cloud/config-pass: then the stick alone opens
# the logins). The first-boot part installs rclone (official build, checksum verified; else the
# copy cached on the stick) and the two scripts; the logins are made from the phone.
cloud_install_rclone() {
    local cache="$KEYSTORE_MOUNT/claude/bin/rclone" attempt tmp
    if ! rclone version > /dev/null 2>&1; then
        for attempt in 1 2 3; do
            tmp=$(mktemp -d)
            if ( cd "$tmp" \
                && ver=$(curl -fsSL https://downloads.rclone.org/version.txt | awk '{print $2}') \
                && [[ "$ver" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] \
                && f="rclone-$ver-linux-arm64.zip" \
                && curl -fsSL -o "$f" "https://downloads.rclone.org/$ver/$f" \
                && curl -fsSL -o SHA256SUMS "https://downloads.rclone.org/$ver/SHA256SUMS" \
                && grep " $f\$" SHA256SUMS | sha256sum -c - > /dev/null \
                && python3 -c 'import sys,zipfile,os; z=zipfile.ZipFile(sys.argv[1]); n=[i for i in z.namelist() if i.endswith("/rclone")][0]; open("/usr/local/bin/rclone.new","wb").write(z.read(n)); os.chmod("/usr/local/bin/rclone.new",0o755); os.replace("/usr/local/bin/rclone.new","/usr/local/bin/rclone")' "$f" ); then
                rm -rf "$tmp"; break
            fi
            rm -rf "$tmp"; log "rclone download attempt $attempt failed; retrying in 20 s"; sleep 20
        done
    fi
    if ! rclone version > /dev/null 2>&1; then
        if [ -f "$cache" ] && mountpoint -q "$KEYSTORE_MOUNT"; then
            install -m 0755 -o root -g root "$cache" /usr/local/bin/rclone
            log "module cloud: the rclone download failed; installed rclone from the stick's cache"
        else
            log "FAILED module cloud: could not install rclone (no download, no cached copy)"; return 1
        fi
    elif mountpoint -q "$KEYSTORE_MOUNT" && ! cmp -s /usr/local/bin/rclone "$cache" 2> /dev/null; then
        install -d -m 0755 -o root -g root "$KEYSTORE_MOUNT/claude/bin"
        install -m 0755 -o root -g root /usr/local/bin/rclone "$cache.tmp" && mv -f "$cache.tmp" "$cache"
    fi
}

module_cloud() {
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module cloud: no user $CLAUDE_USER"; return 1; }
    cloud_install_rclone || return 1
    cat > /usr/local/sbin/pi-cloud-pass <<'PASS'
#!/bin/sh
# The passphrase of the rclone config on the stick (rclone runs this as RCLONE_PASSWORD_COMMAND).
# From RAM when the keyholder is unlocked, else from the stick when `pi-cloud auto on` was run.
for f in /run/pi-secrets/rclone_config_pass /mnt/pi-keys/cloud/config-pass; do
    [ -r "$f" ] && { cat "$f"; exit 0; }
done
echo "locked: unlock from the phone first" >&2
exit 1
PASS
    chmod 755 /usr/local/sbin/pi-cloud-pass
    cat > /usr/local/bin/pi-cloud <<'PICLOUD'
#!/bin/bash
# pi-cloud: copy-only access to the Pi's own folder on cloud drives (setups/pi-rationale.md,
# item 23). Written by pi-firstboot.sh (module_cloud); edit it there.
#   pi-cloud status
#   pi-cloud login PROVIDER          onedrive: browser sign-in (the phone tunnels port 53682);
#                                    gdrive: stdin client id, client secret (both may be blank), scope (blank or
#                                    "full" = the whole Drive), then the sign-in;
#                                    dropbox: stdin app key, app secret, then the same sign-in;
#                                    mega: stdin email, password; proton: stdin email, password [, 2fa code]
#   pi-cloud logout PROVIDER
#   pi-cloud ls PROVIDER [SUBPATH]
#   pi-cloud push [--videos | --only EXT,EXT] [--exclude PATTERN] PROVIDER LOCALDIR [SUBPATH]
#                                    copies LOCALDIR into snngine-pi/SUBPATH (never deletes); with
#                                    --videos or --only, just those files, same folder structure
#   pi-cloud pull [same options as push] PROVIDER SUBPATH LOCALDIR
#                                    copies snngine-pi/SUBPATH to LOCALDIR (never deletes)
#   pi-cloud sync                    run the jobs in claude/sync.conf on the stick (the timer does this)
#   pi-cloud auto on|off             keep the config passphrase on the stick (logins without unlock)
# Providers: gdrive dropbox onedrive mega proton. Transfers stop at PI_CLOUD_MAX_TRANSFER (2G).
set -uo pipefail
STICK=/mnt/pi-keys
CLOUD=$STICK/cloud
FOLDER=snngine-pi
MAXT=${PI_CLOUD_MAX_TRANSFER:-2G}
PROVIDERS="gdrive dropbox onedrive mega proton"
export RCLONE_CONFIG=$CLOUD/rclone.conf
export RCLONE_PASSWORD_COMMAND=/usr/local/sbin/pi-cloud-pass

die() { echo "pi-cloud: $*" >&2; exit 1; }
provider_ok() { case " $PROVIDERS " in *" ${1:-} "*) return 0 ;; esac; die "unknown provider '${1:-}' (one of: $PROVIDERS)"; }
sub_ok() { # a relative path inside the Pi's folder: no leading slash or dash, no "..", no backslash
    case "${1:-}" in
        '') return 0 ;;
        /* | -* | *..* | *\\* | *$'\n'*) die "bad path '$1' (it must stay inside $FOLDER)" ;;
    esac
}
rtype() { case "$1" in gdrive) echo drive ;; dropbox) echo dropbox ;; onedrive) echo onedrive ;; mega) echo mega ;; proton) echo protondrive ;; esac; }
mode() { if [ -r /run/pi-secrets/rclone_config_pass ]; then echo "unlocked from the phone"; else echo "automatic, passphrase on the stick"; fi; }
need_stick() { [ -d "$CLOUD" ] || die "the credential stick is not mounted (or module_cloud has not run)"; }
need_unlocked() {
    need_stick
    /usr/local/sbin/pi-cloud-pass > /dev/null 2>&1 \
        || die "locked: unlock from the phone first (the config passphrase is the keyholder secret rclone_config_pass; once only: pi_keyholder.py add rclone_config_pass --consumer claude --generate)"
}
configured() { rclone listremotes 2> /dev/null | tr -d ':' | grep -qx "$1"; }
need_login() { need_unlocked; configured "$1" || die "$1 is not logged in (pi-cloud login $1)"; }
ensure_conf() {
    need_unlocked
    [ -f "$RCLONE_CONFIG" ] && return 0
    { rclone config touch && rclone config encryption set; } > /dev/null 2>&1 || die "could not create the encrypted config"
}

cmd_status() {
    need_stick
    if ! /usr/local/sbin/pi-cloud-pass > /dev/null 2>&1; then echo "locked (unlock from the phone first)"; return 0; fi
    echo "unlocked ($(mode))"
    local p
    for p in $PROVIDERS; do
        if configured "$p"; then echo "$p: logged in"; else echo "$p: not logged in"; fi
    done
}

cmd_login() {
    local p=${1:-} a b c
    provider_ok "$p"; ensure_conf
    # Never replaces a login by itself: `config create` on an existing remote would keep its old
    # token and skip the sign-in, so an existing login has to be removed on purpose first.
    ! configured "$p" || die "$p is already logged in; to switch account or client id, run: pi-cloud logout $p"
    case "$p" in
        gdrive)   # stdin: the maintainer's own Google client id and secret (both may be blank:
                  # rclone's shared client, which Google is retiring during 2026), then the scope:
                  # blank = drive.file (only what rclone created), "full" = the whole Drive
                  local scope=drive.file; local -a extra=()
                  read -r a || true; read -r b || true; read -r c || true
                  [ "$c" = full ] && scope=drive
                  [ -n "$a" ] && [ -n "$b" ] && extra=(client_id "$a" client_secret "$b")
                  timeout 900 rclone config create gdrive drive scope "$scope" "${extra[@]}" ;;
        onedrive) timeout 900 rclone config create onedrive onedrive ;;
        dropbox)  read -r a; read -r b
                  [ -n "$a" ] && [ -n "$b" ] || die "dropbox needs the app key and the app secret on stdin"
                  timeout 900 rclone config create dropbox dropbox client_id "$a" client_secret "$b" ;;
        mega)     read -r a; read -r b
                  [ -n "$a" ] && [ -n "$b" ] || die "mega needs the email and the password on stdin"
                  rclone config create mega mega user "$a" pass "$b" ;;
        proton)   read -r a; read -r b; read -r c || true
                  [ -n "$a" ] && [ -n "$b" ] || die "proton needs the email and the password on stdin"
                  if [ -n "$c" ]; then rclone config create proton protondrive username "$a" password "$b" 2fa "$c"
                  else rclone config create proton protondrive username "$a" password "$b"; fi ;;
    esac || { rclone config delete "$p" > /dev/null 2>&1; die "the $p sign-in did not complete"; }
    if timeout 180 rclone mkdir "$p:$FOLDER"; then
        echo "$p: logged in; the Pi's folder is $FOLDER"
    else
        rclone config delete "$p" > /dev/null 2>&1
        die "$p: signed in, but could not create $FOLDER (login removed)"
    fi
}

cmd_logout() { local p=${1:-}; provider_ok "$p"; need_unlocked; rclone config delete "$p" && echo "$p: logged out (revoke the token at the provider too)"; }

cmd_ls() { local p=${1:-} s=${2:-}; provider_ok "$p"; sub_ok "$s"; need_login "$p"; rclone lsf "$p:$FOLDER/$s"; }

# Options shared by push and pull: --videos, --only EXT,EXT (just those files, same folder
# structure), --exclude PATTERN (repeatable; a path pattern inside the Pi's folder, e.g. dump/**).
# Sets FILTERS (ordered rules: excludes first, then the includes, then exclude everything else) and POS.
parse_opts() {
    local only="" e ex=() exc=()
    FILTERS=(); POS=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --videos) only="mp4,m4v,mov,mkv,webm,avi" ;;
            --only) only=${2:-}; shift ;;
            --exclude) [[ "${2:-}" =~ ^[A-Za-z0-9._/*-]+$ ]] || die "bad exclude pattern '${2:-}'"; exc+=("$2"); shift ;;
            *) POS+=("$1") ;;
        esac
        shift
    done
    # Ordered --filter rules (the first matching rule wins): rclone does not apply separate
    # --exclude and --include flags in the order given, which let excluded files through.
    for e in "${exc[@]+"${exc[@]}"}"; do FILTERS+=(--filter "- $e"); done
    if [ -n "$only" ]; then
        IFS=, read -ra ex <<< "$only"
        for e in "${ex[@]}"; do
            [[ "$e" =~ ^[A-Za-z0-9]+$ ]] || die "bad extension '$e'"
            FILTERS+=(--filter "+ *.$e")
        done
        FILTERS+=(--filter "- *")
    fi
}

cmd_push() {
    parse_opts "$@"; set -- "${POS[@]+"${POS[@]}"}"
    local p=${1:-} d=${2:-} s=${3:-}
    provider_ok "$p"; sub_ok "$s"; need_login "$p"
    [ -d "$d" ] || die "'$d' is not a directory"
    d=$(realpath -- "$d")
    rclone copy "$d" "$p:$FOLDER/$s" "${FILTERS[@]+"${FILTERS[@]}"}" ${PI_CLOUD_MIN_AGE:+--min-age "$PI_CLOUD_MIN_AGE"} --max-transfer "$MAXT" --cutoff-mode cautious -v 2>&1 | tail -n 5
    return "${PIPESTATUS[0]}"
}

cmd_pull() {
    parse_opts "$@"; set -- "${POS[@]+"${POS[@]}"}"
    local p=${1:-} s=${2:-} d=${3:-}
    provider_ok "$p"; sub_ok "$s"; need_login "$p"
    [ -n "$d" ] || die "pull needs a local directory"
    d=$(realpath -m -- "$d"); [ ! -e "$d" ] || [ -d "$d" ] || die "'$d' exists and is not a directory"
    rclone copy "$p:$FOLDER/$s" "$d" "${FILTERS[@]+"${FILTERS[@]}"}" --max-transfer "$MAXT" --cutoff-mode cautious -v 2>&1 | tail -n 5
    return "${PIPESTATUS[0]}"
}

# The jobs the timer runs: /mnt/pi-keys/claude/sync.conf (root-owned, so the agent cannot add a
# job), one per line: push|pull PROVIDER LOCALDIR SUBPATH|- [options as for push and pull].
# Copy-only like the rest, so a file deleted on one side comes back from the other; a locked
# keyholder skips the round; files younger than a minute are left for the next round.
cmd_sync() {
    local conf=$STICK/claude/sync.conf kind p dir sub rest failed=0
    local -a opts
    [ -r "$conf" ] || die "no job list ($conf)"
    need_stick
    if ! /usr/local/sbin/pi-cloud-pass > /dev/null 2>&1; then echo "sync: locked, nothing done"; return 0; fi
    exec 9> "$CLOUD/.sync.lock"
    flock -n 9 || { echo "sync: a run is already in progress"; return 0; }
    export PI_CLOUD_MIN_AGE=1m
    while read -r kind p dir sub rest <&3; do
        case "$kind" in '' | '#'*) continue ;; esac
        [ "$sub" = "-" ] && sub=""
        read -ra opts <<< "${rest:-}"
        case "$kind" in
            push) echo "sync: push $p $dir -> ${sub:-/} ${rest:-}"; ( cmd_push "${opts[@]+"${opts[@]}"}" "$p" "$dir" "$sub" ) < /dev/null || failed=$((failed + 1)) ;;
            pull) echo "sync: pull $p ${sub:-/} -> $dir ${rest:-}"; ( cmd_pull "${opts[@]+"${opts[@]}"}" "$p" "$sub" "$dir" ) < /dev/null || failed=$((failed + 1)) ;;
            *) echo "sync: unknown job '$kind' (skipped)" ;;
        esac
    done 3< "$conf"
    # A failed job is reported above, not as a failed timer unit (a provider that is not logged
    # in yet, or a folder that is not there yet, is normal).
    [ "$failed" -eq 0 ] || echo "sync: $failed job(s) did not complete (see above)"
    return 0
}

cmd_auto() {
    need_stick
    case "${1:-}" in
        on)  [ -r /run/pi-secrets/rclone_config_pass ] || die "unlock from the phone first, then run this"
             install -m 0600 /run/pi-secrets/rclone_config_pass "$CLOUD/config-pass" && echo "automatic: the config passphrase is now on the stick" ;;
        off) rm -f "$CLOUD/config-pass"; echo "locked by default again (unlock from the phone)" ;;
        *)   die "pi-cloud auto on|off" ;;
    esac
}

verb=${1:-}; [ $# -gt 0 ] && shift
case "$verb" in
    status) cmd_status ;;
    login) cmd_login "$@" ;;
    logout) cmd_logout "$@" ;;
    ls) cmd_ls "$@" ;;
    push) cmd_push "$@" ;;
    pull) cmd_pull "$@" ;;
    auto) cmd_auto "$@" ;;
    sync) cmd_sync ;;
    *) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
PICLOUD
    chmod 755 /usr/local/bin/pi-cloud
    install -d -m 0755 /usr/local/share/pi-phone
    cat > /usr/local/share/pi-phone/pi-cloud-login.sh <<'PHONESCRIPT'
#!/data/data/com.termux/files/usr/bin/bash
# The phone-side login for the Pi's cloud drives (setups/pi-rationale.md, item 23). Installed on
# the Pi by pi-firstboot.sh (module_cloud) and run on the phone by the Termux:Widget stub
# ~/.shortcuts/pi-cloud-login.sh, which fetches this file from the Pi each time (so it is never
# pasted again). It unlocks the keyholder if needed (the passphrase prompt of `pi-keys unlock`),
# then runs `pi-cloud login PROVIDER` on the Pi as the claude user:
#   gdrive, onedrive  browser sign-in: the Pi's rclone listens on 127.0.0.1:53682, this script
#                     tunnels that port to the phone and opens the link in the phone's browser
#                     (gdrive first asks for your own Google client id and secret, blank for
#                     rclone's shared client, and the scope: blank = only files the Pi creates,
#                     "full" = the whole Drive)
#   dropbox           asks for the app key and secret of the maintainer's own App-folder app
#                     (redirect URI http://localhost:53682/), then the same browser sign-in
#   mega, proton      asks for the email and password of the dedicated account (hidden)
#   logout PROVIDER   removes a login (it never replaces one by itself)
# Nothing is stored on the phone, and no secret is put in an argument or the output.
SSH=(ssh -i "$HOME/.ssh/claude_ed25519" -o IdentitiesOnly=yes)
HOST=claude@pi-host
TUNNEL=(-o ExitOnForwardFailure=yes -L 53682:127.0.0.1:53682)

stop() { echo; read -r -p "Press Enter to close" _; exit "${1:-0}"; }

echo "Provider: gdrive dropbox onedrive mega proton   (or: logout PROVIDER)"
read -r -p "> " P
case "$P" in
    "logout "*) L="${P#logout }" ;;
    gdrive | dropbox | onedrive | mega | proton) ;;
    *) echo "unknown provider"; stop 1 ;;
esac

if ! "${SSH[@]}" "$HOST" pi-cloud status 2> /dev/null | grep -q '^unlocked'; then
    echo "Locked: unlocking the keyholder first"
    pi-keys unlock || { echo "unlock failed"; stop 1; }
    "${SSH[@]}" "$HOST" pi-cloud status 2> /dev/null | grep -q '^unlocked' \
        || { echo "still locked: the keyholder has no rclone_config_pass yet"; stop 1; }
fi

if [ -n "${L:-}" ]; then
    "${SSH[@]}" "$HOST" "pi-cloud logout $L" 2>&1
    stop 0
fi

# Prints the Pi's output and opens the sign-in link in the phone's browser when it appears.
open_links() {
    local line url
    while IFS= read -r line; do
        printf '%s\n' "$line"
        url=$(printf '%s' "$line" | grep -o 'http://127.0.0.1:53682/auth[^ ]*')
        [ -n "$url" ] && termux-open-url "$url"
    done
}

case "$P" in
    gdrive)
        echo "Your own Google client id and secret (blank = rclone's shared client, which Google is retiring during 2026)."
        read -r -p "Google client id: " K
        read -r -s -p "Google client secret (hidden): " S; echo
        read -r -p "Scope (blank = only files the Pi creates, 'full' = the whole Drive): " SC
        printf '%s\n%s\n%s\n' "$K" "$S" "$SC" | "${SSH[@]}" "${TUNNEL[@]}" "$HOST" "pi-cloud login gdrive" 2>&1 | open_links ;;
    onedrive)
        "${SSH[@]}" "${TUNNEL[@]}" "$HOST" "pi-cloud login onedrive" 2>&1 | open_links ;;
    dropbox)
        read -r -p "Dropbox app key: " K
        read -r -s -p "Dropbox app secret (hidden): " S; echo
        printf '%s\n%s\n' "$K" "$S" | "${SSH[@]}" "${TUNNEL[@]}" "$HOST" "pi-cloud login dropbox" 2>&1 | open_links ;;
    mega)
        read -r -p "Mega account email: " U
        read -r -s -p "Password (hidden): " W; echo
        printf '%s\n%s\n' "$U" "$W" | "${SSH[@]}" "$HOST" "pi-cloud login mega" 2>&1 ;;
    proton)
        read -r -p "Proton account email: " U
        read -r -s -p "Password (hidden): " W; echo
        read -r -p "2FA code (blank if the account has none): " C
        printf '%s\n%s\n%s\n' "$U" "$W" "$C" | "${SSH[@]}" "$HOST" "pi-cloud login proton" 2>&1 ;;
esac
stop 0
PHONESCRIPT
    chmod 644 /usr/local/share/pi-phone/pi-cloud-login.sh
    if mountpoint -q "$KEYSTORE_MOUNT"; then
        install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$KEYSTORE_MOUNT/cloud"
    fi
    # The timer: every five minutes, `pi-cloud sync` runs the jobs in the stick's claude/sync.conf
    # (root-owned). The default jobs: each task's whole output folder is copied to the Pi's folder
    # on Google Drive and anything found there comes down (both copy-only), and everything in
    # its dump folder comes down to ~/dump for any agent to pick up. It does nothing while locked.
    local home; home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    install -d -m 0755 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$home/dump"
    if mountpoint -q "$KEYSTORE_MOUNT" && [ ! -f "$KEYSTORE_MOUNT/claude/sync.conf" ]; then
        cat > "$KEYSTORE_MOUNT/claude/sync.conf" <<CONF
# <push|pull> <provider> <local dir> <subpath in snngine-pi, - for none> [options]  (edit as root)
# A task's whole output folder, both ways (copy-only: nothing is ever deleted on either side).
# A new task with its own output folder needs its two lines here.
push gdrive $home/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/output runpod-chem-diffusion/output
pull gdrive $home/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/output runpod-chem-diffusion/output
push gdrive $home/dev/snngineV4_agent_branches/setups/runpod-engine-smoke-test/output runpod-engine-smoke-test/output
pull gdrive $home/dev/snngineV4_agent_branches/setups/runpod-engine-smoke-test/output runpod-engine-smoke-test/output
# Everything uploaded into the dump folder on Drive lands in ~/dump for any agent.
pull gdrive $home/dump dump
CONF
        chown root:root "$KEYSTORE_MOUNT/claude/sync.conf"; chmod 644 "$KEYSTORE_MOUNT/claude/sync.conf"
    fi
    cat > /etc/systemd/system/pi-cloud-sync.service <<UNIT
[Unit]
Description=Copy videos and the dump folder between the Pi and the cloud drives (pi-cloud sync)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$CLAUDE_USER
Environment=HOME=$home
ExecStart=/usr/local/bin/pi-cloud sync
UNIT
    cat > /etc/systemd/system/pi-cloud-sync.timer <<UNIT
[Unit]
Description=Run pi-cloud sync every five minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT
    chmod 644 /etc/systemd/system/pi-cloud-sync.service /etc/systemd/system/pi-cloud-sync.timer
    systemctl daemon-reload
    systemctl enable --now pi-cloud-sync.timer > /dev/null 2>&1 || { log "FAILED module cloud: could not enable the sync timer"; return 1; }
    log "module cloud: ok ($(rclone version | head -n 1); pi-cloud installed; logins are made from the phone)"
}

# VS Code in the browser (for the phone): the official CLI's `code serve-web` as a service under
# the unprivileged user, listening on loopback only and published to the tailnet over HTTPS by
# `tailscale serve` (so it is not exposed on the router's LAN; needs HTTPS certificates enabled
# for the tailnet). A connection token is kept on the stick (claude/vscode-web-token, readable
# by the claude user: a secret of the same standing as the rest of its files) so the URL stays
# the same across re-flashes; settings and extensions are kept on the stick (claude/vscode-web).
# The URL: https://<pi tailnet name>/?tkn=<token>&folder=<folder>
module_vscode_web() {
    local home attempt s
    id "$CLAUDE_USER" > /dev/null 2>&1 || { log "FAILED module vscode web: no user $CLAUDE_USER"; return 1; }
    mountpoint -q "$KEYSTORE_MOUNT" || { log "module vscode web: the stick is not mounted; skipped"; return 0; }
    home=$(getent passwd "$CLAUDE_USER" | cut -d: -f6)
    s="$KEYSTORE_MOUNT/claude"
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$home/.local/bin/code" --version > /dev/null 2>&1; then
        for attempt in 1 2 3; do
            if timeout 600 runuser -u "$CLAUDE_USER" -- env HOME="$home" bash -c \
                'mkdir -p ~/.local/bin && cd "$(mktemp -d)" && curl -fsSL "https://update.code.visualstudio.com/latest/cli-linux-arm64/stable" -o cli.tgz && tar -xzf cli.tgz -C ~/.local/bin code'; then
                break
            fi
            log "vscode cli download attempt $attempt failed; retrying in 20 s"; sleep 20
        done
    fi
    if ! timeout 60 runuser -u "$CLAUDE_USER" -- env HOME="$home" "$home/.local/bin/code" --version > /dev/null 2>&1; then
        log "FAILED module vscode web: could not install the VS Code CLI"; return 1
    fi
    install -d -m 0700 -o "$CLAUDE_USER" -g "$CLAUDE_USER" "$s/vscode-web"
    if [ ! -s "$s/vscode-web-token" ]; then
        (umask 077; head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$s/vscode-web-token")
        chown "$CLAUDE_USER":"$CLAUDE_USER" "$s/vscode-web-token"; chmod 600 "$s/vscode-web-token"
    fi
    cat > /etc/systemd/system/vscode-web.service <<UNIT
[Unit]
Description=VS Code in the browser (serve-web), loopback only; published over the tailnet by tailscale serve
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
User=$CLAUDE_USER
Environment=HOME=$home
TimeoutStartSec=infinity
ExecStartPre=/bin/sh -c 'until mountpoint -q $KEYSTORE_MOUNT; do sleep 5; done'
ExecStart=$home/.local/bin/code serve-web --host 127.0.0.1 --port 8000 --connection-token-file $s/vscode-web-token --server-data-dir $s/vscode-web --default-folder $home/work --accept-server-license-terms --disable-telemetry
ExecStartPost=+-/bin/sh -c 'for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do /usr/bin/tailscale serve --bg --https=443 http://127.0.0.1:8000 && exit 0; sleep 10; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
    chmod 644 /etc/systemd/system/vscode-web.service
    systemctl daemon-reload
    systemctl enable --now vscode-web.service > /dev/null 2>&1 || { log "FAILED module vscode web: could not enable the service"; return 1; }
    # The first request makes serve-web download its server build (a few hundred MB; 202 until it
    # is ready). Make it now, so the first use from the phone is instant.
    timeout 900 sh -c 'until c=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/); [ "$c" != 000 ] && [ "$c" != 202 ]; do sleep 10; done' \
        || log "module vscode web: the warm-up did not finish; the first request will download the server"
    log "module vscode web: ok (vscode-web.service; the token is in $s/vscode-web-token)"
}

# The Pi's SSH host keys live on the stick (ssh-host/, root-only), so a re-flash keeps the same
# fingerprint and no client has to forget the old one. With keys on the stick they replace the
# freshly generated ones (sshd restarted); without, the current keys are saved there.
module_ssh_hostkeys() {
    local d="$KEYSTORE_MOUNT/ssh-host" f
    mountpoint -q "$KEYSTORE_MOUNT" || { log "module ssh hostkeys: the stick is not mounted; skipped"; return 0; }
    if ls "$d"/ssh_host_*_key > /dev/null 2>&1; then
        for f in "$d"/ssh_host_*; do
            case "$f" in
                *.pub) install -m 0644 -o root -g root "$f" "/etc/ssh/${f##*/}" ;;
                *) install -m 0600 -o root -g root "$f" "/etc/ssh/${f##*/}" ;;
            esac
        done
        if ! sshd -t 2> /dev/null; then log "FAILED module ssh hostkeys: sshd rejects the restored keys"; return 1; fi
        systemctl restart ssh > /dev/null 2>&1 || systemctl restart sshd > /dev/null 2>&1 || true
        log "module ssh hostkeys: restored the host keys from the stick"
    else
        install -d -m 0700 -o root -g root "$d"
        cp -p /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub "$d"/
        log "module ssh hostkeys: saved the host keys on the stick"
    fi
}

# The keyholder: encrypted secrets on the credential stick, unlocked into RAM on request.
#   On the stick:  secrets/<name>.gpg   passphrase-encrypted values (gpg, AES256)
#                  secrets.conf         one "<name> <consumer user>" per line
#                  unlock/authorized_keys   public keys allowed to ask for an unlock
#   On the Pi:     /run/pi-secrets/<name>   the decrypted value, RAM only, owned by the
#                  consumer, mode 0400; gone on power loss or after a lock.
# Two root-owned helpers, written below. pi-unlock reads its request on stdin (verb
# unlock, lock or status; the passphrase on the next line) and is the only command the
# pikeys user may run: sshd forces it for that user, and sudoers allows nothing else.
# pi-secret-add (admin only, not in pikeys' sudoers) encrypts a new value onto the
# stick. Any device holding a key listed in unlock/authorized_keys can ask for an
# unlock; the admin can also run pi-unlock through sudo. Nothing here is needed to boot:
# without an unlock the Pi runs normally, only consumers of a secret wait.
module_keyholder() {
    local tmp applied keys=0
    if ! command -v gpg > /dev/null 2>&1; then
        if ! DEBIAN_FRONTEND=noninteractive timeout 600 apt-get install -y --no-install-recommends gnupg; then
            log "FAILED module keyholder: could not install gnupg"; return 1
        fi
    fi
    if ! id "$KEYHOLDER_USER" > /dev/null 2>&1; then
        if ! useradd --system --create-home --home-dir "/home/$KEYHOLDER_USER" --shell /bin/bash "$KEYHOLDER_USER"; then
            log "FAILED module keyholder: could not create user $KEYHOLDER_USER"; return 1
        fi
    fi
    # '*' = no valid password, but not "locked" (a locked account refuses key logins too).
    usermod -p '*' "$KEYHOLDER_USER"

    # The stick's side, only if it is mounted (a Pi booted without it still gets the helpers).
    if mountpoint -q "$KEYSTORE_MOUNT"; then
        install -d -m 0700 -o root -g root "$KEYSTORE_MOUNT/secrets"
        install -d -m 0750 -o root -g "$KEYHOLDER_USER" "$KEYSTORE_MOUNT/unlock"
        [ -f "$KEYSTORE_MOUNT/unlock/authorized_keys" ] \
            || install -m 0640 -o root -g "$KEYHOLDER_USER" /dev/null "$KEYSTORE_MOUNT/unlock/authorized_keys"
        [ -f "$KEYSTORE_MOUNT/secrets.conf" ] \
            || printf '%s\n' '# <secret name>  <user that reads it>   (value: secrets/<name>.gpg)' > "$KEYSTORE_MOUNT/secrets.conf"
        chmod 600 "$KEYSTORE_MOUNT/secrets.conf"
        keys=$(grep -c '^ssh-' "$KEYSTORE_MOUNT/unlock/authorized_keys" || true)
    else
        log "keyholder: no stick mounted at $KEYSTORE_MOUNT; helpers installed, stick folders not prepared"
    fi

    { printf '#!/bin/bash\nSTICK=%q\n' "$KEYSTORE_MOUNT"; cat <<'UNLOCK'
# Written by pi-firstboot.sh (module_keyholder); edit it there. Root-owned. Run through sudo
# by the pikeys user's forced SSH command, or by the admin. It trusts no argument and no
# environment: the request is on stdin. Line 1: unlock | lock | status. For unlock, line 2
# is the passphrase. Output carries secret names and counts, never a value.
set -uo pipefail
umask 077
export TMPDIR=/run PATH=/usr/sbin:/usr/bin:/sbin:/bin
RUN=/run/pi-secrets
MANIFEST=$STICK/secrets.conf
SECDIR=$STICK/secrets
note() { logger -t pi-unlock -- "$*" 2> /dev/null || true; }

exec 9> /run/pi-unlock.lock
flock -w 10 9 || { echo "busy"; exit 1; }
read -r verb || { echo "no request"; exit 2; }

# One "name user" line per valid manifest entry; fails on an invalid one.
manifest_entries() {
    local name user rest
    [ -f "$MANIFEST" ] || return 0
    while read -r name user rest; do
        case "$name" in ''|'#'*) continue ;; esac
        [[ "$name" =~ ^[a-z0-9_]{1,40}$ ]] || { echo "bad name in the manifest" >&2; return 1; }
        [[ "${user:-root}" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo "bad user in the manifest" >&2; return 1; }
        echo "$name ${user:-root}"
    done < "$MANIFEST"
}

case "$verb" in
status)
    if mountpoint -q "$STICK"; then echo "stick: mounted"; else echo "stick: absent"; fi
    entries=$(manifest_entries) || { echo "manifest: invalid"; exit 1; }
    while read -r name user; do
        [ -n "$name" ] || continue
        s="locked"; [ -f "$RUN/$name" ] && s="in RAM"
        c="no ciphertext"; [ -f "$SECDIR/$name.gpg" ] && c="ciphertext present"
        echo "$name: $s, $c"
    done <<< "$entries"
    ;;
lock)
    if [ -d "$RUN" ]; then
        find "$RUN" -type f -exec shred -u {} + 2> /dev/null
        rmdir "$RUN" 2> /dev/null || true
    fi
    note "locked"; echo "locked"
    ;;
unlock)
    read -r pass || { echo "no passphrase"; exit 2; }
    [ -n "$pass" ] || { echo "empty passphrase"; exit 2; }
    mountpoint -q "$STICK" || { echo "key stick not mounted"; exit 1; }
    entries=$(manifest_entries) || { echo "manifest: invalid"; exit 1; }
    [ -n "$entries" ] || { echo "no secrets listed in the manifest"; exit 1; }
    work=$(mktemp -d /run/pi-unlock.XXXXXX); gh=$(mktemp -d /run/pi-unlock-gpg.XXXXXX)
    trap 'find "$work" -type f -exec shred -u {} + 2> /dev/null; rm -rf "$work" "$gh"' EXIT
    # Decrypt everything into a scratch folder first: all or nothing.
    while read -r name user; do
        [ -f "$SECDIR/$name.gpg" ] || { echo "missing ciphertext: $name"; exit 1; }
        if ! gpg --homedir "$gh" --batch --quiet --no-tty --pinentry-mode loopback \
                --passphrase-fd 3 --no-symkey-cache -o "$work/$name" -d "$SECDIR/$name.gpg" \
                3<<< "$pass" < /dev/null > /dev/null 2>&1; then
            sleep 2; note "unlock failed"; echo "unlock failed"; exit 1
        fi
    done <<< "$entries"
    install -d -m 0711 -o root -g root "$RUN"
    names=""
    while read -r name user; do
        owner=root; id -u "$user" > /dev/null 2>&1 && owner=$user
        install -m 0400 -o "$owner" -g "$(id -gn "$owner")" "$work/$name" "$RUN/.$name.new" \
            && mv -f "$RUN/.$name.new" "$RUN/$name" || { echo "could not place $name"; exit 1; }
        [ "$owner" = "$user" ] || echo "note: user $user does not exist, $name is owned by root"
        names="$names $name"
    done <<< "$entries"
    # Drop anything from an earlier unlock that the manifest no longer lists.
    for f in "$RUN"/*; do
        [ -e "$f" ] || continue
        b=$(basename "$f"); case " $names " in *" $b "*) ;; *) shred -u "$f" ;; esac
    done
    note "unlocked:$names"; echo "unlocked:$names"
    ;;
*)
    echo "unknown request"; exit 2
    ;;
esac
UNLOCK
    } > "$KEYHOLDER_UNLOCK"
    chown root:root "$KEYHOLDER_UNLOCK"; chmod 755 "$KEYHOLDER_UNLOCK"

    { printf '#!/bin/bash\nSTICK=%q\n' "$KEYSTORE_MOUNT"; cat <<'ADDSECRET'
# Written by pi-firstboot.sh (module_keyholder); edit it there. Root-only: run through sudo
# by the admin (it is NOT in the pikeys user's sudoers). Usage: pi-secret-add <name> [<user>].
# stdin: line 1 the passphrase, line 2 the secret value (one line). Encrypts it onto the
# stick as secrets/<name>.gpg, checks that it decrypts back to the same value, and lists
# it in secrets.conf for <user> (default root). Prints names and sizes only.
set -uo pipefail
umask 077
export TMPDIR=/run PATH=/usr/sbin:/usr/bin:/sbin:/bin
MANIFEST=$STICK/secrets.conf
SECDIR=$STICK/secrets
name=${1:-}; user=${2:-root}
[[ "$name" =~ ^[a-z0-9_]{1,40}$ ]] || { echo "the name must be a-z, 0-9 and _ (at most 40)"; exit 2; }
[[ "$user" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo "bad consumer user name"; exit 2; }
read -r pass || { echo "no passphrase"; exit 2; }
read -r value || true
[ -n "$pass" ] && [ -n "$value" ] || { echo "empty passphrase or value"; exit 2; }
mountpoint -q "$STICK" || { echo "key stick not mounted"; exit 1; }
install -d -m 0700 -o root -g root "$SECDIR"
gh=$(mktemp -d /run/pi-secret-gpg.XXXXXX); tmp=$SECDIR/.$name.new
trap 'rm -rf "$gh"; rm -f "$tmp"' EXIT
# One passphrase protects every secret (unlock is all-or-nothing), so when a secret already
# exists, the typed passphrase must open it: a different one would make the next unlock fail.
# (To change the passphrase on purpose, move the secrets/ folder away first and add them all again.)
first=$(ls -1 "$SECDIR"/*.gpg 2> /dev/null | head -n 1)
if [ -n "$first" ]; then
    gpg --homedir "$gh" --batch --quiet --no-tty --pinentry-mode loopback --passphrase-fd 3 \
        --no-symkey-cache -d "$first" 3<<< "$pass" > /dev/null 2>&1 < /dev/null \
        || { echo "that passphrase does not open the secrets already stored; nothing stored (use the passphrase you unlock with)"; exit 1; }
fi
printf '%s' "$value" | gpg --homedir "$gh" --batch --quiet --no-tty --pinentry-mode loopback \
        --passphrase-fd 3 --no-symkey-cache --symmetric --cipher-algo AES256 \
        --s2k-mode 3 --s2k-digest-algo SHA512 --s2k-count 65011712 --compress-algo none \
        -o "$tmp" 3<<< "$pass" > /dev/null 2>&1 || { echo "encryption failed"; exit 1; }
back=$(gpg --homedir "$gh" --batch --quiet --no-tty --pinentry-mode loopback \
        --passphrase-fd 3 --no-symkey-cache -d "$tmp" 3<<< "$pass" 2> /dev/null < /dev/null) || back=""
[ "$back" = "$value" ] || { echo "round-trip check failed; nothing stored"; exit 1; }
mv -f "$tmp" "$SECDIR/$name.gpg"
[ -f "$MANIFEST" ] || printf '%s\n' '# <secret name>  <user that reads it>   (value: secrets/<name>.gpg)' > "$MANIFEST"
{ grep -v -E "^$name[[:space:]]" "$MANIFEST" || true; printf '%s %s\n' "$name" "$user"; } > "$MANIFEST.new"
mv -f "$MANIFEST.new" "$MANIFEST"; chmod 600 "$MANIFEST"
echo "stored $name for $user ($(stat -c %s "$SECDIR/$name.gpg") bytes encrypted); verified by decrypting it back"
ADDSECRET
    } > "$KEYHOLDER_ADD"
    chown root:root "$KEYHOLDER_ADD"; chmod 755 "$KEYHOLDER_ADD"

    # sudo: the pikeys user may run the unlock helper and nothing else.
    tmp=$(mktemp)
    printf '%s ALL=(root) NOPASSWD: %s\n' "$KEYHOLDER_USER" "$KEYHOLDER_UNLOCK" > "$tmp"
    if ! visudo -cf "$tmp" > /dev/null; then
        rm -f "$tmp"; log "FAILED module keyholder: the sudoers rule did not validate"; return 1
    fi
    install -m 0440 -o root -g root "$tmp" "$KEYHOLDER_SUDOERS"; rm -f "$tmp"

    # sshd: for that user only, the unlock helper is forced, with no shell, tty or forwarding.
    # The key file is on the stick (so it survives a re-flash). Validated before reloading;
    # a failed check removes the file again, so a bad rule can never lock the admin out.
    install -d -m 0755 /etc/ssh/sshd_config.d
    cat > "$KEYHOLDER_SSHD" <<SSHDCONF
Match User $KEYHOLDER_USER
    AuthorizedKeysFile $KEYSTORE_MOUNT/unlock/authorized_keys
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowTcpForwarding no
    AllowAgentForwarding no
    X11Forwarding no
    PermitTTY no
    PermitUserRC no
    ForceCommand /usr/bin/sudo -n $KEYHOLDER_UNLOCK
SSHDCONF
    chmod 644 "$KEYHOLDER_SSHD"
    if ! sshd -t 2> /dev/null; then
        rm -f "$KEYHOLDER_SSHD"; log "FAILED module keyholder: sshd rejects the keyholder config; removed it"; return 1
    fi
    # Captured first: under pipefail, `grep -q` ending the pipe early would fail it with SIGPIPE.
    applied=$(sshd -T -C "user=$KEYHOLDER_USER,host=localhost,addr=127.0.0.1" 2> /dev/null) || applied=""
    if ! grep -qi "^forcecommand .*$KEYHOLDER_UNLOCK" <<< "$applied"; then
        rm -f "$KEYHOLDER_SSHD"; log "FAILED module keyholder: sshd does not apply the forced command to $KEYHOLDER_USER; removed the config"; return 1
    fi
    systemctl reload ssh 2> /dev/null || systemctl reload sshd 2> /dev/null || true
    if [ "$(sudo -l -U "$KEYHOLDER_USER" 2> /dev/null | grep -c 'NOPASSWD:')" -ne 1 ]; then
        log "FAILED module keyholder: $KEYHOLDER_USER has more or fewer sudo rights than the one rule"; return 1
    fi
    log "module keyholder: ok (user $KEYHOLDER_USER, forced unlock, $keys key(s) in unlock/authorized_keys)"
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
        autostart) log "=== wireguard autostart only ==="; preflight; module_wireguard_autostart; return ;;
        hotplug) log "=== keystore hotplug only ==="; preflight; module_keystore_hotplug; return ;;
        docker) log "=== docker only ==="; preflight; wait_for_clock; module_docker; return ;;
        git) log "=== git only ==="; preflight; wait_for_clock; module_git; return ;;
        claude-user) log "=== claude user only ==="; preflight; module_claude_user; return ;;
        agy) log "=== agy only ==="; preflight; module_agy; return ;;
        cloud) log "=== cloud drives only ==="; preflight; module_cloud; return ;;
        github) log "=== github only ==="; preflight; module_github; return ;;
        runpod-ssh) log "=== runpod ssh key only ==="; preflight; module_runpod_ssh; return ;;
        claude-rc) log "=== claude remote control only ==="; preflight; module_claude_rc; return ;;
        vscode-web) log "=== vscode web only ==="; preflight; module_vscode_web; return ;;
        ssh-hostkeys) log "=== ssh host keys only ==="; preflight; module_ssh_hostkeys; return ;;
        tailscale) log "=== tailscale only ==="; preflight; wait_for_clock; module_tailscale; return ;;
        tailscale-backup) log "=== tailscale identity backup only ==="; preflight; tailscale_identity_backup; return ;;
        keyholder) log "=== keyholder only ==="; preflight; module_keyholder; return ;;
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
    module_wireguard_autostart
    module_keystore_hotplug
    # The extras (downloads from third-party servers) must never block the core setup: a failure
    # is logged, the run goes on, and at the end it exits non-zero without the marker, so the
    # unit retries the whole (idempotent) run until they succeed.
    optional_failed=0
    optional() { "$@" || { log "optional step $1 failed; continuing, will retry the run"; optional_failed=1; }; }
    optional module_ssh_hostkeys
    module_docker
    module_git
    module_claude_user
    optional module_agy
    optional module_claude_rc
    optional module_cloud
    optional module_github
    optional module_runpod_ssh
    module_tailscale
    optional module_vscode_web
    module_keyholder
    scrub_wifi_password
    if [ "$optional_failed" -ne 0 ]; then
        log "=== pi-provision incomplete: an optional step failed; no marker, will retry ==="
        exit 1
    fi
    touch "$MARK"
    log "=== pi-provision done ==="
}

# Sourcing the file (for tests) defines the functions without running them.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
