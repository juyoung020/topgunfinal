# tools/tourney_recv0913.ps1 — 2026-09-13 카카오톡 수신 모델끼리만 풀리그 (받은 파일 전부)
#   powershell -ExecutionPolicy Bypass -NoProfile -File tools\tourney_recv0913.ps1 [-Preset 2000ft] [-MaxSec 215]
#   참가 4종을 모든 조합으로 붙이고, 슬롯 편향(2000ft 정면은 Red 가 유리한 경향)을 상쇄하려고 자리를 바꿔 2판씩.
#   4종 -> 6쌍 x 2판 = 12판. 결과는 artifacts\eval_visual\match_<Tag>_hp.csv / _end.png.
#   유효판 판정: 클라이언트 로그에 `spawn dist OK 609.x m` 줄이 있는 판만 센다(match_run.ps1 이 패킷으로 검증).
#   주의: 이 스크립트를 두 번 띄우면 같은 뷰어·포트에 클라이언트가 4개 붙어 판이 엉킨다(2026-09-13 실측). 반드시 한 번만.
param([string]$Preset = "2000ft", [int]$MaxSec = 215)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$M = @("recv_myng_iter12021", "recv_sharedv8_iter0035", "recv_ash_0913", "recv_ash_0913_2")
$pairs = @()
for ($i = 0; $i -lt $M.Count; $i++) {
  for ($j = $i + 1; $j -lt $M.Count; $j++) { $pairs += ,@($M[$i], $M[$j]) }
}
$total = $pairs.Count * 2
"[토너먼트] 참가 $($M.Count)종 · $($pairs.Count)쌍 x 2판 = $total 판 시작 $(Get-Date -Format HH:mm)"
$n = 0
foreach ($p in $pairs) {
  $a = $p[0]; $b = $p[1]
  $pa = "artifacts\models\AeroFlyer\$a"
  $pb = "artifacts\models\AeroFlyer\$b"
  $sa = $a -replace 'recv_',''
  $sb = $b -replace 'recv_',''
  $n++
  "[$n/$total] $a (Blue) vs $b (Red)  $(Get-Date -Format HH:mm:ss)"
  # [2026-09-13] Select-String 으로 걸러 내던 것을 전량 출력으로 바꿨다. 걸러 내면 판이 어디서 멈췄는지가 안 보인다
  #   (게다가 실행을 `| tail` 로 받으면 파이프가 닫힐 때까지 버퍼링돼 진행 상황이 한 줄도 안 나왔다 — 그렇게 쓰지 말 것).
  & powershell -NoProfile -File "$root\tools\match_run.ps1" -A $pa -B $pb -Tag "t13_${sa}_vs_${sb}_A" -Preset $Preset -MaxSec $MaxSec
  $n++
  "[$n/$total] $b (Blue) vs $a (Red)  자리 교대  $(Get-Date -Format HH:mm:ss)"
  & powershell -NoProfile -File "$root\tools\match_run.ps1" -A $pb -B $pa -Tag "t13_${sa}_vs_${sb}_B" -Preset $Preset -MaxSec $MaxSec
}
"[토너먼트] 완료 $(Get-Date -Format HH:mm)"
