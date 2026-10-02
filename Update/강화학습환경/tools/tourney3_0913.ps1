# tools/tourney3_0913.ps1 - 2026-09-13 received-model 3-way round robin (cutoff excluded)
#   powershell -ExecutionPolicy Bypass -NoProfile -File tools\tourney3_0913.ps1
#
# NOTE: ASCII-only comments on purpose. A .ps1 saved as UTF-8 without BOM is decoded as CP949
#       by Windows PowerShell 5.1; mangled Korean comments broke the parser (2026-09-13,
#       "Unexpected token ')'"). Same trap as the .bat files. Keep this file ASCII.
#
# Design
#   - Head-on (habfm) and tail-chase (obfm_red) excluded per user instruction. Distance presets only.
#   - Repeats DO carry information: the same config (ash2 Blue vs daeil Red, 2000ft) came out
#     22s 0.0/0.0 mutual kill once and 19s 25.9/26.1 both-alive another time. Server matches
#     do not reproduce, so repeated samples are real samples.
#   - 5 conditions x 2 slots = 10 matches per pair. 3 pairs = 30 matches.
#   - Altitude 2000..10000 ft and speed 150..250 m/s randomized per condition (user instruction).
#     The SAME alt/speed is used for BOTH slots of a pair, otherwise slot-swap averaging no
#     longer cancels the slot bias. Server Speed is a single input field = identical for both
#     aircraft, so speed can never favor one side.
#   - Chosen values are printed AND appended to artifacts\eval_visual\t15_conditions.csv.
#   - Fixed RNG seed, so the whole schedule is reproducible.
#
#   Output: artifacts\eval_visual\match_<Tag>_hp.csv / _end.png
#   A match counts only if match_run.ps1 verified the spawn distance from packets (`spawn dist OK`).
#   Matches whose hp.csv already exists are skipped, so an interrupted run can be resumed.
#
#   WARNING: launching this twice puts 4 clients on the same viewer/port and ruins the matches.
param([int]$MaxSec = 215, [int]$Seed = 913)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$mr  = Join-Path $root 'tools\match_run.ps1'
$out = Join-Path $root 'artifacts\eval_visual'
$cond_log = Join-Path $out 't15_conditions.csv'
if (-not (Test-Path $cond_log)) { "tag_base,ic,rep,alt_ft,speed_ms" | Out-File $cond_log -Encoding utf8 }

$rng = New-Object System.Random($Seed)

$M = @{
  'ash2'  = 'artifacts\models\AeroFlyer\recv_ash_0913_2'
  'daeil' = 'artifacts\models\AeroFlyer\recv_daeil_iter8820'
  'myng'  = 'artifacts\models\AeroFlyer\recv_myng_iter12021'
}
$PAIRS = @(@('ash2','daeil'), @('ash2','myng'), @('daeil','myng'))
$CONDS = @(
  @('2000ft','r1'), @('2000ft','r2'),
  @('2500ft','r1'),
  @('3000ft','r1'), @('3000ft','r2')
)

$total = $PAIRS.Count * $CONDS.Count * 2
"TOURNEY3 START  pairs=$($PAIRS.Count) conds=$($CONDS.Count) total=$total seed=$Seed  $(Get-Date -Format HH:mm:ss)"
$n = 0
foreach ($p in $PAIRS) {
  $a = $p[0]; $b = $p[1]
  foreach ($c in $CONDS) {
    $ic = $c[0]; $rep = $c[1]
    $alt = $rng.Next(2000, 10001)
    $spd = $rng.Next(150, 251)
    $base = "t15_${a}_vs_${b}_${ic}_${rep}"
    "$base,$ic,$rep,$alt,$spd" | Out-File $cond_log -Append -Encoding utf8
    foreach ($slot in @('A','B')) {
      $n++
      $x = if ($slot -eq 'A') { $a } else { $b }
      $y = if ($slot -eq 'A') { $b } else { $a }
      $tag = "${base}_${slot}"
      if (Test-Path (Join-Path $out "match_${tag}_hp.csv")) {
        "[$n/$total] SKIP (already done) $tag"
        continue
      }
      "[$n/$total] $x (Blue) vs $y (Red)  ic=$ic $rep alt=${alt}ft spd=${spd}ms  $(Get-Date -Format HH:mm:ss)"
      & powershell -NoProfile -File $mr -A $M[$x] -B $M[$y] -Tag $tag -Preset $ic -AltFt $alt -SpeedMs $spd -MaxSec $MaxSec
    }
  }
}
"TOURNEY3 DONE  $(Get-Date -Format HH:mm:ss)"
