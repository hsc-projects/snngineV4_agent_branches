# Restart Windows Internet Connection Sharing so the Pi gets DHCP on the cable.
# Needs admin rights (restart-sharing.bat asks for them). Safe to run any time.
#
# It starts the SharedAccess service if it is stopped, then switches sharing off
# everywhere and on again for the internet-side adapter and the Pi-side adapter,
# checks that DHCP (UDP 67) is listening, and waits a short, bounded time for the Pi
# to show up. The internet side is detected (every real adapter that has internet,
# best route first, each tried in turn until one works); -Public NAME forces one.
# A failure is reported in seconds, with what was tried and what to do next.
# Names are the Windows adapter names.
param(
    [string]$Public = '',      # empty: detected
    [string]$Private = 'Ethernet'
)

$ErrorActionPreference = 'Stop'
$virtual = 'WireGuard|VPN|Tunnel|TAP|Wintun|Virtual|Hyper-V|Loopback|Bluetooth|Miniport'
$piMacs = '^(D8-3A-DD|DC-A6-32|E4-5F-01|B8-27-EB|2C-CF-67|28-CD-C1)'

# --- candidates for the internet side ---------------------------------------------
$candidates = @()
if ($Public) {
    $candidates = @($Public)
} else {
    $candidates = @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix 0.0.0.0/0 -ErrorAction SilentlyContinue | ForEach-Object {
        $a = Get-NetAdapter -InterfaceIndex $_.ifIndex -ErrorAction SilentlyContinue
        $i = Get-NetIPInterface -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        if ($a -and $a.Status -eq 'Up') { [pscustomobject]@{ Alias = $_.InterfaceAlias; Metric = $_.RouteMetric + $i.InterfaceMetric; Desc = $a.InterfaceDescription } }
    } | Where-Object { $_.Alias -ne $Private -and $_.Desc -notmatch $virtual } | Sort-Object Metric | ForEach-Object { $_.Alias } | Select-Object -Unique)
    if ($candidates.Count -eq 0) { $candidates = @('WiFi') }
    # A connected adapter can still have no internet (Wi-Fi without a route out, say);
    # try the ones Windows reports as having internet first.
    $online = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.IPv4Connectivity -eq 'Internet' } | ForEach-Object { $_.InterfaceAlias })
    $candidates = @($candidates | Where-Object { $online -contains $_ }) + @($candidates | Where-Object { $online -notcontains $_ })
}

# --- quick look at what usually gets in the way ------------------------------------
$vpn = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -match 'WireGuard|VPN|Tunnel|TAP|Wintun' -and $_.InterfaceDescription -notmatch 'Tailscale' })
foreach ($v in $vpn) {
    Write-Host "WARNING: VPN adapter '$($v.Name)' is up. A connected VPN owns the default route and breaks sharing for the Pi; disconnect it."
}
$stopped = @('SharedAccess', 'NlaSvc', 'COMSysApp') | Where-Object { (Get-Service $_ -ErrorAction SilentlyContinue).Status -ne 'Running' }
if ($stopped) { Write-Host "Services not running: $($stopped -join ', ')" }

$svc = Get-Service SharedAccess
if ($svc.Status -ne 'Running') {
    Start-Service SharedAccess
    Write-Host "Started the SharedAccess service."
}

$m = New-Object -ComObject HNetCfg.HNetShare
function Find-Config($name) {
    foreach ($c in $m.EnumEveryConnection) {
        if ($m.NetConnectionProps($c).Name -eq $name) { return $m.INetSharingConfigurationForINetConnection($c) }
    }
    return $null
}
$priv = Find-Config $Private
if (-not $priv) {
    Write-Host "Pi-side adapter '$Private' not found. Present adapters:"
    foreach ($c in $m.EnumEveryConnection) { Write-Host "  $($m.NetConnectionProps($c).Name)" }
    exit 1
}

# Windows allows only one shared (public) connection, so sharing is switched off on
# every adapter that has it (a leftover otherwise makes EnableSharing fail with 0x80040201).
function Reset-Sharing {
    foreach ($c in $m.EnumEveryConnection) {
        $cfg = $m.INetSharingConfigurationForINetConnection($c)
        if ($cfg.SharingEnabled) { $cfg.DisableSharing() }
    }
    Start-Sleep -Seconds 2
}

# --- try each candidate until one works ---------------------------------------------
$failures = @()
$ok = $null
foreach ($name in $candidates) {
    $pub = Find-Config $name
    if (-not $pub) { $failures += "$name : no such connection"; continue }
    Write-Host "Trying '$name' as the internet side ..."
    try {
        Reset-Sharing
        $pub.EnableSharing(0)    # public: the side with the internet
        $priv.EnableSharing(1)   # private: the side with the Pi
        $ok = $name
        break
    } catch {
        $failures += "$name : $($_.Exception.Message)"
        Write-Host "  failed: $($_.Exception.Message)"
    }
}

if (-not $ok) {
    Write-Host ""
    Write-Host "Sharing could not be enabled. Tried: $($candidates -join ', ')."
    if ($failures -match '0x80040201') {
        Write-Host "0x80040201 is a COM+ event error: Windows could not deliver the sharing change to a subscriber."
        Write-Host "On 2026-10-11 it hit Wi-Fi as the internet side and not phone USB tethering; starting NlaSvc and"
        Write-Host "COMSysApp and resetting the Pi-side adapter did not cure it."
    }
    Write-Host "Next: connect phone USB tethering and run this again; or use the hotspot path (the Pi joins the"
    Write-Host "phone's hotspot, the laptop joins it too); or reboot the laptop and run this again."
    exit 1
}

# --- DHCP and the Pi ----------------------------------------------------------------
$listening = $false
for ($i = 0; $i -lt 10 -and -not $listening; $i++) {
    $listening = @(Get-NetUDPEndpoint -LocalPort 67 -ErrorAction SilentlyContinue).Count -gt 0
    if (-not $listening) { Start-Sleep -Seconds 1 }
}
if (-not $listening) {
    Write-Host "WARNING: sharing is on ('$ok') but nothing is listening on UDP 67 yet. Run this again, or check the adapter's Sharing tab."
    exit 1
}
Write-Host "OK: sharing is on with '$ok' as the internet side, DHCP is listening."
$conn = (Get-NetConnectionProfile -InterfaceAlias $ok -ErrorAction SilentlyContinue).IPv4Connectivity
if ($conn -ne 'Internet') {
    Write-Host "WARNING: Windows reports no internet on '$ok' (IPv4 connectivity: $(if ($conn) { $conn } else { 'no network profile' })), so the Pi will have none either."
    Write-Host "Connect it, or run this again with -Public NAME for an adapter that has internet (for example phone USB tethering)."
}

# A Pi that sat without DHCP for minutes has given up on the cable; give it a bounded moment.
$seen = $null
for ($i = 0; $i -lt 20 -and -not $seen; $i++) {
    $seen = Get-NetNeighbor -InterfaceAlias $Private -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.LinkLayerAddress -match $piMacs -and $_.State -ne 'Unreachable' } | Select-Object -First 1
    if (-not $seen) { Start-Sleep -Seconds 2 }
}
if ($seen) {
    Write-Host "The Pi is on the cable at $($seen.IPAddress)."
} else {
    Write-Host "No Pi seen yet. If it has been without DHCP for a few minutes it has given up on the cable:"
    Write-Host "unplug the Pi's Ethernet cable, plug it back in (or power-cycle it), then look for it again."
}
exit 0
