# tools/tourney_daeil_vs_model0913.ps1 - 2026-09-13 daeil_iter8820 vs C:\topgunfinal\model\* (1 match each)
#   powershell -ExecutionPolicy Bypass -NoProfile -File tools\tourney_daeil_vs_model0913.ps1
#
# NOTE: ASCII-only comments on purpose. A .ps1 saved as UTF-8 without BOM is decoded as CP949
#       by Windows PowerShell 5.1 and mangled Korean comments break the parser (2026-09-13).
#
# Design
#   - 20 opponents x 1 match = 20 matches, per user instruction ("한판씩").
#   - FIXED condition (2000ft, viewer default alt/speed) on purpose: with only one match per
#     opponent, randomizing alt/speed would give every opponent a different condition and the
#     20 results would not be comparable to each other. Fixed condition = a screen, not a verdict.
#     (Caveat: fixed conditions produce false draws - see the 3-way league on 2026-09-13 where
#      ash2/daeil mutual-killed under every fixed condition but separated once conditions varied.
#      If this run comes back as a wall of mutual kills, that is the same effect, not a tie.)
#   - daeil is Blue in every match so the opponents stay comparable. The Blue slot carries a
#     bias that varies by matchup (measured 0.4 .. 62.5 HP), so a narrow daeil win is not proof.
#   - All 20 opponent bundles verified 16-dim student16, same contract as daeil.
#
#   Output: artifacts\eval_visual\match_t16_daeil_vs_<opp>_hp.csv / _end.png
#   Valid only if match_run.ps1 confirmed the spawn distance from packets (`spawn dist OK`).
#   Matches whose hp.csv exists are skipped, so an interrupted run can be resumed.
#
#   WARNING: launching this twice puts 4 clients on the same viewer/port and ruins the matches.
param([int]$MaxSec = 215, [string]$Preset = '2000ft')
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$mr  = Join-Path $root 'tools\match_run.ps1'
$out = Join-Path $root 'artifacts\eval_visual'
$daeil = 'artifacts\models\AeroFlyer\recv_daeil_iter8820'

$OPP = @(
  'recv_snap9980', 's52_ladder5220_beaten', 'sub_cand_peak3100', 'sub_cand_snap12241',
  'symmetric_iter1540', 'symmetric_iter1720', 'symmetric_iter1920', 'v1_s48_snap12241',
  'v2_ladder5220', 'cand_c13280_s45', 'cand_v2r8_iter10400', 'champion_v2r6_iter7200',
  'champion_v2r7_iter25100', 'final_sp_iter0160', 'prev_champion_v2r5_iter1000',
  'recv_aimangle_v4_0824', 'recv_aimcur_0823', 'recv_league_v3_gen1_iter5',
  'recv_league_v4_best60', 'recv_scrim_exp025'
)

$total = $OPP.Count
"DAEIL-SCREEN START  opponents=$total preset=$Preset  $(Get-Date -Format HH:mm:ss)"
$n = 0
foreach ($o in $OPP) {
  $n++
  $tag = "t16_daeil_vs_$o"
  if (Test-Path (Join-Path $out "match_${tag}_hp.csv")) { "[$n/$total] SKIP (already done) $tag"; continue }
  $bp = "..\..\model\$o"
  "[$n/$total] daeil (Blue) vs $o (Red)  $(Get-Date -Format HH:mm:ss)"
  & powershell -NoProfile -File $mr -A $daeil -B $bp -Tag $tag -Preset $Preset -MaxSec $MaxSec
}
"DAEIL-SCREEN DONE  $(Get-Date -Format HH:mm:ss)"
