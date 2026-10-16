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
    module_docker
    module_tailscale
    module_keyholder
    scrub_wifi_password
    touch "$MARK"
    log "=== pi-provision done ==="
}

# Sourcing the file (for tests) defines the functions without running them.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
