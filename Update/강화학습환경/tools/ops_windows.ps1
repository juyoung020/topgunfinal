# ops_windows.ps1 — 학습 창 정리 (안전판). 기본은 dry-run, -Apply 일 때만 실제로 닫는다.
#   규칙 1) 살아있는 역할 python(트레이너/sidecar/우리 대시보드)을 자손으로 가진 창은 절대 안 닫는다
#   규칙 2) 자손에 역할 python 이 없는 런처 창(배트 종료 -> pause 상태)만 닫는다
#   규칙 3) 우리 대시보드가 2개 이상이면 포트 7860 소유자만 남기고 나머지 python 만 죽인다 (부모는 안 건드림)
#   규칙 4) Ray 내부 대시보드(ray\dashboard\dashboard.py)는 패턴에서 제외 — 그걸 죽이면 raylet 이 노드를 내린다 (2026-08-28 사고)
#   규칙 5) 트레이너/sidecar 는 이 스크립트가 절대 죽이지 않는다
param([switch]$Apply)
$ErrorActionPreference = 'SilentlyContinue'
$all = Get-CimInstance Win32_Process
$me = $PID
$rolePat = @{ trainer = 'train_curriculum\.py'; sidecar = 'snapshot_sidecar\.py'; dashboard = 'tools.dashboard\.py' }
$roleProcs = @{}
foreach ($r in $rolePat.Keys) {
  $roleProcs[$r] = @($all | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match $rolePat[$r] })
}
$liveRolePids = @($roleProcs.Values | ForEach-Object { $_ } | ForEach-Object { $_.ProcessId })
function Get-Descendants([int]$root) {
  $out = New-Object System.Collections.Generic.List[int]
  $queue = New-Object System.Collections.Generic.Queue[int]; $queue.Enqueue($root)
  while ($queue.Count -gt 0) {
    $p = $queue.Dequeue()
    foreach ($c in ($all | Where-Object { $_.ParentProcessId -eq $p })) {
      if (-not $out.Contains([int]$c.ProcessId)) { $out.Add([int]$c.ProcessId); $queue.Enqueue([int]$c.ProcessId) }
    }
  }
  return $out
}
$batPat = 'launch_final_selfplay|launch_final_sidecar|launch_final_resume|launch_dashboard|LAUNCH~[0-9]\.BAT|LA[0-9A-F]{4}~[0-9]\.BAT'
$windows = @($all | Where-Object { ($_.Name -eq 'powershell.exe' -or $_.Name -eq 'cmd.exe') -and $_.CommandLine -match $batPat -and $_.ProcessId -ne $me -and $_.CommandLine -notmatch 'ops_windows|Get-CimInstance' })

"== 역할 프로세스 =="
foreach ($r in 'trainer','sidecar','dashboard') { "  {0,-9} : {1}" -f $r, (($roleProcs[$r] | ForEach-Object { $_.ProcessId }) -join ', ') }
$owner = (Get-NetTCPConnection -LocalPort 7860 -State Listen | Select-Object -First 1).OwningProcess
"  port7860  : $owner"

"== 창 =="
$toClose = @()
foreach ($w in $windows) {
  $desc = Get-Descendants $w.ProcessId
  $live = @($desc | Where-Object { $liveRolePids -contains $_ })
  $tag = if ($live.Count -gt 0) { "KEEP (live role python: $($live -join ','))" } else { "DEAD -> close" }
  $bat = ($w.CommandLine | Select-String -Pattern $batPat -AllMatches).Matches.Value -join ','
  "  {0} pid {1,-6} {2,-28} {3}" -f $w.Name, $w.ProcessId, $bat, $tag
  if ($live.Count -eq 0) { $toClose += $w }
}

"== 중복 대시보드 =="
$dupes = @($roleProcs['dashboard'] | Where-Object { $_.ProcessId -ne $owner })
if ($dupes.Count -eq 0) { "  없음" } else { foreach ($d in $dupes) { "  duplicate dashboard python pid $($d.ProcessId) (port owner $owner 유지)" } }

if (-not $Apply) { "`n(dry-run) 실제로 닫으려면 -Apply"; exit 0 }
foreach ($d in $dupes) { Stop-Process -Id $d.ProcessId -Force; "  killed duplicate dashboard python $($d.ProcessId)" }
Start-Sleep 1
# 중복 대시보드를 죽인 뒤 그 창도 자손이 없어졌으므로 다시 계산해 닫는다
$all = Get-CimInstance Win32_Process
foreach ($w in $windows) {
  $desc = Get-Descendants $w.ProcessId
  $live = @($desc | Where-Object { $liveRolePids -contains $_ -and $_ -notin ($dupes | ForEach-Object { $_.ProcessId }) })
  if ($live.Count -eq 0) { Stop-Process -Id $w.ProcessId -Force; "  closed dead window $($w.Name) $($w.ProcessId)" }
}
"done."
