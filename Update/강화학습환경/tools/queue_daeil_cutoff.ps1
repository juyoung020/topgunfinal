# tools/queue_daeil_cutoff.ps1
#   Main submission model (recv_daeil_iter8820) vs cutoff, 10 matches, head-on IC.
#   ASCII comments only (CP949 parser trap, 9/13).
#
#   This is the SAME weights the submitted AeroFlyer.exe loads (BUNDLE_REL in
#   aeroflyer_main.py). The bundle is used instead of the exe because
#   match_run.ps1 validates spawn distance from a python client log, and
#   exe+cutoff leaves no such log on either side. exe/bundle equivalence was
#   already verified to the HP decimal (30.6 : 0.0).
#
#   Baseline for the head-on question: does the head-on fine-tune (iter0401)
#   actually beat the submission at head-on, or is the submission already fine?
#   Same 5/5 slot swap and same randomized alt/speed rules as the 0401 queue.
param([int]$Games = 10)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$A = "artifacts\models\AeroFlyer\recv_daeil_iter8820"
$stamp = Get-Date -Format "MMdd_HHmm"
$res = "artifacts\eval_visual\queue_daeil_cutoff_$stamp.csv"
"game,slot_blue,slot_red,alt_ft,speed_ms,tag" | Out-File $res -Encoding utf8

function KillRoles {
  foreach ($n in @("DogFightViewer-Win64-Shipping", "unreal_bt_client")) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  }
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*attach_client*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
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
  $tag = "daeilcut_{0}_g{1:d2}" -f $stamp, $g
  $bn = if ($blue -eq "cutoff") { "cutoff" } else { "daeil" }
  $rn = if ($red  -eq "cutoff") { "cutoff" } else { "daeil" }
  "=== game $g/$Games  Blue=$bn Red=$rn  alt=${alt}ft spd=${spd}ms  $(Get-Date -Format HH:mm:ss) ==="
  & powershell -ExecutionPolicy Bypass -File "$root\tools\match_run.ps1" `
      -A $blue -B $red -Tag $tag -Preset habfm -AltFt $alt -SpeedMs $spd -MaxSec 215
  "$g,$bn,$rn,$alt,$spd,$tag" | Out-File $res -Append -Encoding utf8
  KillRoles
  if (-not (CleanWait)) { "ABORT at game ${g}: field not clear"; break }
}
"=== queue done $(Get-Date -Format HH:mm:ss) -> $res ==="
