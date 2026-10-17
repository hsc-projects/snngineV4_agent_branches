#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget stub (~/.shortcuts/pi-cloud-login.sh): runs the current login script from the Pi
# (installed there at first boot, source in setups/pi-provision/pi-firstboot.sh, module_cloud),
# so this stub never needs updating or pasting again.
exec bash <(ssh -i "$HOME/.ssh/claude_ed25519" -o IdentitiesOnly=yes claude@pi-host 'cat /usr/local/share/pi-phone/pi-cloud-login.sh')
