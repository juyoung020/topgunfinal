# tools/league_run1.ps1 — 챔피언 vs 로스터, **상대당 1판**(챔프=Blue)
param([Parameter(Mandatory=$true)][string]$Champ,
      [Parameter(Mandatory=$true)][string]$Roster,
      [string]$Prefix = "lg1s", [string]$Preset = "2000ft", [int]$MaxSec = 215)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$names = Get-Content $Roster | Where-Object { $_.Trim() -ne "" }
"[리그-단판] 상대 $($names.Count)종 시작 $(Get-Date -Format HH:mm)"
$i = 0
foreach ($n in $names) {
  $i++
  $opp = if ($n -eq "cutoff") { "cutoff" } else { "artifacts\models\AeroFlyer\$n" }
  "[리그 $i/$($names.Count)] $n"
  & powershell -NoProfile -File "$root\tools\match_run.ps1" -A $Champ -B $opp -Tag "${Prefix}_${n}" -Preset $Preset -MaxSec $MaxSec | Select-String 'done|ABORT|not confirmed'
}
"[리그-단판] 완료 $(Get-Date -Format HH:mm)"
