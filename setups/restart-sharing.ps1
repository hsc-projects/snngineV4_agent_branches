# Restart Windows Internet Connection Sharing so the Pi gets DHCP on the cable.
# Needs admin rights (restart-sharing.bat asks for them). Safe to run any time:
# it starts the SharedAccess service if it is stopped, switches sharing off and
# on again for the public (internet-side) and private (Pi-side) adapters, and
# checks that DHCP (UDP 67) is listening. Names are the Windows adapter names.
param(
    [string]$Public = 'WiFi',
    [string]$Private = 'Ethernet'
)

$ErrorActionPreference = 'Stop'

$svc = Get-Service SharedAccess
if ($svc.Status -ne 'Running') {
    Start-Service SharedAccess
    Write-Host "Started the SharedAccess service."
}

$m = New-Object -ComObject HNetCfg.HNetShare
$pub = $null; $priv = $null
foreach ($c in $m.EnumEveryConnection) {
    $p = $m.NetConnectionProps($c)
    if ($p.Name -eq $Public)  { $pub  = $m.INetSharingConfigurationForINetConnection($c) }
    if ($p.Name -eq $Private) { $priv = $m.INetSharingConfigurationForINetConnection($c) }
}
if (-not $pub -or -not $priv) {
    Write-Host "Adapter not found (public '$Public', private '$Private'). Present adapters:"
    foreach ($c in $m.EnumEveryConnection) { Write-Host "  $($m.NetConnectionProps($c).Name)" }
    exit 1
}

# Windows allows only one shared (public) connection, so switch sharing off on
# every adapter that has it, not just the two used now (a leftover from an earlier
# setup, e.g. Wi-Fi, otherwise makes EnableSharing fail with 0x80040201).
foreach ($c in $m.EnumEveryConnection) {
    $cfg = $m.INetSharingConfigurationForINetConnection($c)
    if ($cfg.SharingEnabled) { $cfg.DisableSharing() }
}
Start-Sleep -Seconds 3
$pub.EnableSharing(0)    # public: the side with the internet
$priv.EnableSharing(1)   # private: the side with the Pi
Start-Sleep -Seconds 3

$listening = $false
for ($i = 0; $i -lt 10 -and -not $listening; $i++) {
    $listening = @(Get-NetUDPEndpoint -LocalPort 67 -ErrorAction SilentlyContinue).Count -gt 0
    if (-not $listening) { Start-Sleep -Seconds 1 }
}
if ($listening) {
    Write-Host "OK: sharing restarted, DHCP is listening. The Pi gets an address within a few seconds."
    exit 0
}
Write-Host "WARNING: sharing was toggled but nothing is listening on UDP 67 yet. Run this again, or check the adapter's Sharing tab."
exit 1
