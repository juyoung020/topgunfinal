# tools/league_run.ps1 — 챔피언 1종 vs 로스터 전체, 슬롯 교대 2판씩
#   powershell -File tools\league_run.ps1 -Champ <번들경로> -Roster <목록파일> -Prefix <태그접두>
#   각 상대마다 (챔프=Blue) 1판 + (챔프=Red) 1판. 결과는 match_<태그>_hp.csv 로 남는다.
param([Parameter(Mandatory=$true)][string]$Champ,
      [Parameter(Mandatory=$true)][string]$Roster,
      [string]$Prefix = "lg",
      [string]$Preset = "2000ft",
      [int]$MaxSec = 215)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$names = Get-Content $Roster | Where-Object { $_.Trim() -ne "" }
"[리그] 상대 $($names.Count)종 x 2판 = $($names.Count * 2)판 시작 $(Get-Date -Format HH:mm)"
$i = 0
foreach ($n in $names) {
  $i++
  $opp = if ($n -eq "cutoff") { "cutoff" } else { "artifacts\models\AeroFlyer\$n" }
  $tagB = "${Prefix}_${n}_champB"
  $tagR = "${Prefix}_${n}_champR"
  "[리그 $i/$($names.Count)] $n  (champ=Blue)"
  & powershell -NoProfile -File "$root\tools\match_run.ps1" -A $Champ -B $opp -Tag $tagB -Preset $Preset -MaxSec $MaxSec | Select-String 'done|ABORT|not confirmed'
  "[리그 $i/$($names.Count)] $n  (champ=Red)"
  & powershell -NoProfile -File "$root\tools\match_run.ps1" -A $opp -B $Champ -Tag $tagR -Preset $Preset -MaxSec $MaxSec | Select-String 'done|ABORT|not confirmed'
}
"[리그] 완료 $(Get-Date -Format HH:mm)"
