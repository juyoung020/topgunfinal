# tools/launch.ps1 — 학습 창 기동 (절대경로 없음: 자기 위치에서 8.3 경로를 계산)
#   powershell -File tools\launch.ps1 sidecar     # 1) 스냅샷 sidecar (반드시 1개)
#   powershell -File tools\launch.ps1 trainer     # 2) 트레이너 첫 기동 (v1 iter_1120 복원)
#   powershell -File tools\launch.ps1 resume      # 2') 트레이너 이어받기 (최신 체크포인트)
#   powershell -File tools\launch.ps1 dashboard   # 3) 대시보드 (cmd 창)
#   powershell -File tools\launch.ps1 all         # sidecar -> trainer -> dashboard 순서대로
param([Parameter(Mandatory=$true)][string]$what)
$root = Split-Path -Parent $PSScriptRoot
$fso = New-Object -ComObject Scripting.FileSystemObject
function Short($name) { $fso.GetFile((Join-Path $root $name)).ShortPath }
function Launch($role) {
  switch ($role) {
    'sidecar'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_sidecar.bat')) }
    'trainer'   { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_selfplay.bat')) }
    'resume'    { Start-Process powershell '-NoExit','-Command',("& " + (Short 'launch_final_resume.bat')) }
    'dashboard' { Start-Process cmd '/k',(Short 'launch_dashboard.bat') }
    default     { throw "unknown: $role (sidecar|trainer|resume|dashboard|all)" }
  }
  "launched $role"
}
if ($what -eq 'all') { Launch 'sidecar'; Start-Sleep 8; Launch 'trainer'; Start-Sleep 5; Launch 'dashboard' } else { Launch $what }
