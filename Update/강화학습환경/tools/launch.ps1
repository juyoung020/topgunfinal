# tools/launch.ps1 — 학습 창 기동 (절대경로 없음: 자기 위치에서 8.3 경로를 계산)
#   powershell -File tools\launch.ps1 sidecar   [-Tag final_sp2]   # 1) 스냅샷 sidecar (반드시 1개)
#   powershell -File tools\launch.ps1 trainer                       # 2) 1라운드 첫 기동 (v1 iter_1120 복원, 태그 final_sp)
#   powershell -File tools\launch.ps1 round2    [-Tag final_sp2]   # 2) 새 라운드 첫 기동 (launch_final_round2.bat 의 ROUND2_FROM 체크포인트 복원, 새 태그)
#   powershell -File tools\launch.ps1 resume    [-Tag final_sp2]   # 2') 이어받기 (해당 태그의 최신 체크포인트)
#   powershell -File tools\launch.ps1 dashboard                     # 3) 대시보드 (cmd 창, 모든 태그의 리플레이·지표)
#   -Tag 는 FINAL_SP_TAG 환경변수로 배트/커리큘럼/도구에 전달된다 (기본 final_sp).
#   sidecar/trainer/round2/resume 앞에서 tools/preflight.py 가 경로 일치(태그 파생·번들 존재·절대경로 없음·대시보드 logdir)를 검사하고 FAIL 이면 띄우지 않는다.
param([Parameter(Mandatory=$true)][string]$what, [string]$Tag = "", [switch]$SkipPreflight)
$root = Split-Path -Parent $PSScriptRoot
if ($Tag -ne "") { $env:FINAL_SP_TAG = $Tag }
$tag = if ($env:FINAL_SP_TAG) { $env:FINAL_SP_TAG } else { "final_sp" }
$py = "C:\Users\user one\anaconda3\envs\aip\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$fso = New-Object -ComObject Scripting.FileSystemObject
function Short($name) { $fso.GetFile((Join-Path $root $name)).ShortPath }
function Preflight($firstRun) {
  $env:PYTHONIOENCODING = "utf-8"
  $args = @((Join-Path $root "tools\preflight.py"), "--tag", $tag)
  if ($firstRun) { $args += "--first-run" }
  Push-Location $root
  $out = & $py @args 2>&1 | Where-Object { $_ -match '^\[preflight\]|FAIL|note' }
  $code = $LASTEXITCODE
  Pop-Location
  $out | ForEach-Object { "  $_" }
  if ($code -ne 0) { throw "preflight FAIL (tag=$tag) — 위 원인을 고친 뒤 다시 실행. 강제로 띄우려면 -SkipPreflight" }
}
function Launch($role) {
  switch ($role) {
    'sidecar'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_sidecar.bat')) }
    'trainer'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_selfplay.bat')) }
    'round2'    { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_round2.bat')) }
    'resume'    { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_resume.bat')) }
    'dashboard' { Start-Process cmd '/k',(Short 'launch_dashboard.bat') }
    default     { throw "unknown: $role (sidecar|trainer|round2|resume|dashboard)" }
  }
  "launched $role (FINAL_SP_TAG=$tag)"
}
if (-not $SkipPreflight -and $what -in 'sidecar','trainer','round2','resume') { Preflight ($what -in 'trainer','round2') }
Launch $what
