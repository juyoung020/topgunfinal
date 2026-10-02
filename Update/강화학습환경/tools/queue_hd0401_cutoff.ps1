# tools/queue_hd0401_cutoff.ps1
#   peak_daeilheadon_iter0401 vs cutoff, 10 matches, head-on IC.
#   ASCII comments only: this file is read as CP949 without a BOM and Korean
#   comments break the parser ("Unexpected token" incident, 9/13).
#
#   Slots swap 5/5 - the Blue slot is worth a few HP against cutoff (measured
#   6/6 Blue wins), so a one-sided run would be unreadable.
#   Alt/Speed are randomized per match but written to BOTH slots: the server
#   Speed(m/s) field is a single input, one side cannot be made faster.
#   Judgement is the HP margin, not win/loss counts.
param([int]$Games = 10)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$A = "artifacts\models\AeroFlyer\peak_daeilheadon_iter0401"
$stamp = Get-Date -Format "MMdd_HHmm"
$res = "artifacts\eval_visual\queue_hd0401_cutoff_$stamp.csv"
"game,slot_blue,slot_red,alt_ft,speed_ms,tag" | Out-File $res -Encoding utf8

# Kill by ROLE NAME only. Never by parent PID or a broad LAUNCH~ filter -
# that killed the trainer once (8/28).
function KillRoles {
  foreach ($n in @("DogFightViewer-Win64-Shipping", "unreal_bt_client")) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  }
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*attach_client*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
# Wait until the field is actually clear. A leftover client from the previous
# match made cutoff fight cutoff once - the user caught it, not the script.
function CleanWait {
  for ($w = 0; $w -lt 60; $w++) {
    $v = @(Get-Process -Name "DogFightViewer-Win64-Shipping" -ErrorAction SilentlyContinue).Count
    $c = @(Get-Process -Name "unreal_bt_client" -ErrorAction SilentlyContinue).Count
    $p = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like '*attach_client*' }).Count
    if ($v -eq 0 -and $c -eq 0 -and $p -eq 0) { return $true }
    Start-Sleep -Seconds 2
  }
  return $false
}

KillRoles
if (-not (CleanWait)) { "ABORT: field not clear before start"; exit 2 }

for ($g = 1; $g -le $Games; $g++) {
  $alt = Get-Random -Minimum 2000 -Maximum 10001
  $spd = Get-Random -Minimum 150 -Maximum 251
  if ($g % 2 -eq 1) { $blue = $A;      $red = "cutoff" }
  else              { $blue = "cutoff"; $red = $A }
  $tag = "hd0401cut_{0}_g{1:d2}" -f $stamp, $g
  $bn = if ($blue -eq "cutoff") { "cutoff" } else { "hd0401" }
  $rn = if ($red  -eq "cutoff") { "cutoff" } else { "hd0401" }
  "=== game $g/$Games  Blue=$bn Red=$rn  alt=${alt}ft spd=${spd}ms  $(Get-Date -Format HH:mm:ss) ==="
  & powershell -ExecutionPolicy Bypass -File "$root\tools\match_run.ps1" `
      -A $blue -B $red -Tag $tag -Preset habfm -AltFt $alt -SpeedMs $spd -MaxSec 215
  "$g,$bn,$rn,$alt,$spd,$tag" | Out-File $res -Append -Encoding utf8
  KillRoles
  if (-not (CleanWait)) { "ABORT at game ${g}: field not clear"; break }
}
"=== queue done $(Get-Date -Format HH:mm:ss) -> $res ==="
