# tools/launch.ps1 — 학습 창 기동 (절대경로 없음: 자기 위치에서 8.3 경로를 계산)
#   powershell -File tools\launch.ps1 sidecar   [-Tag final_sp2]   # 1) 스냅샷 sidecar (반드시 1개)
#   powershell -File tools\launch.ps1 trainer                       # 2) 첫 기동 (v1 iter_1120 복원, 태그 final_sp)
#   powershell -File tools\launch.ps1 round2    [-Tag final_sp2]   # 2) 2라운드 첫 기동 (final_sp iter_1400 복원, 새 태그)
#   powershell -File tools\launch.ps1 resume    [-Tag final_sp2]   # 2') 이어받기 (해당 태그의 최신 체크포인트)
#   powershell -File tools\launch.ps1 dashboard                     # 3) 대시보드 (cmd 창)
#   -Tag 는 FINAL_SP_TAG 환경변수로 배트/커리큘럼에 전달된다 (기본 final_sp).
param([Parameter(Mandatory=$true)][string]$what, [string]$Tag = "")
$root = Split-Path -Parent $PSScriptRoot
if ($Tag -ne "") { $env:FINAL_SP_TAG = $Tag }
$fso = New-Object -ComObject Scripting.FileSystemObject
function Short($name) { $fso.GetFile((Join-Path $root $name)).ShortPath }
function Launch($role) {
  switch ($role) {
    'sidecar'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_sidecar.bat')) }
    'trainer'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_selfplay.bat')) }
    'round2'    { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_round2.bat')) }
    'resume'    { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_resume.bat')) }
    'dashboard' { Start-Process cmd '/k',(Short 'launch_dashboard.bat') }
    default     { throw "unknown: $role (sidecar|trainer|round2|resume|dashboard)" }
  }
  "launched $role (FINAL_SP_TAG=" + $(if ($env:FINAL_SP_TAG) { $env:FINAL_SP_TAG } else { "final_sp" }) + ")"
}
Launch $what
