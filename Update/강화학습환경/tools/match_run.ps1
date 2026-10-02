# tools/match_run.ps1 — 실서버 한 판 자동 실행 (뷰어 재시작 -> 2000ft -> OpenServer -> A(Blue) -> B(Red) -> Start -> 캡처 -> 종료 감지)
#   powershell -File tools\match_run.ps1 -A <번들경로|cutoff> -B <번들경로|cutoff> -Tag <이름> [-Preset 2000ft] [-MaxSec 215]
#   번들경로는 작업 루트 기준 상대경로 (..\..\model\xxx 또는 artifacts\models\AeroFlyer\xxx). cutoff = C:\cutoff_model\unreal_bt_client.exe
#   결과: artifacts\eval_visual\match_<Tag>_t{15,30,60,...}.png (HP 바 스트립), match_<Tag>_end.png (전체 화면), attach 로그 match_<Tag>_{a,b}.log (UTF-16)
#   판정은 end.png 의 HP 바 / "xxx Win" 표시로 사람이 읽는다. 뷰어 프로세스 실제 이름 DogFightViewer-Win64-Shipping.
#   종료 감지: python 클라이언트 로그의 RX MT_GameControl 이 2 이상(시작 1 + 종료 1)이면 판이 끝난 것 — 격추로 20 초에 끝나면 바로 다음 판으로.
#   [2026-09-13] -SpeedMs 추가. 서버 Speed(m/s) 는 입력칸이 하나라 양쪽에 같은 값이 들어간다
#   (한쪽만 빠르게 줄 수 없다 - 판정에서 아군만 유리하게 만드는 것은 불가능). 0 이면 안 건드린다.
param([Parameter(Mandatory=$true)][string]$A, [Parameter(Mandatory=$true)][string]$B, [Parameter(Mandatory=$true)][string]$Tag, [string]$Preset = "2000ft", [int]$MaxSec = 215, [int]$AltFt = 0, [int]$SpeedMs = 0, [switch]$DryRun)
if ($DryRun) { "DRY A=[$A] B=[$B] Tag=[$Tag]"; exit 0 }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = "C:\Users\user one\anaconda3\envs\aip\python.exe"
$env:PYTHONIOENCODING = "utf-8"
$fso = New-Object -ComObject Scripting.FileSystemObject
$wd = $fso.GetFolder((Get-Location).Path).ShortPath
$out = "$wd\artifacts\eval_visual"
function Attach($bundle, $name, $log) {
  if ($bundle -eq "cutoff") { Start-Process "C:\cutoff_model\unreal_bt_client.exe" -WorkingDirectory "C:\cutoff_model"; return }
  # [2026-09-13] exe:<경로> = 제출용으로 패키징한 우리 exe 를 그대로 붙인다.
  #   제출 검증은 "번들이 잘 나는가"가 아니라 "운영진이 받을 그 exe 가 실제로 교전하는가"라서
  #   python 경로가 아니라 exe 를 직접 띄워야 의미가 있다. 팀명/서버는 exe 안에 박혀 있다.
  if ($bundle -like "exe:*") {
    $ep = $bundle.Substring(4)
    # [2026-09-13] stdout 을 매치 로그로 돌린다. 안 그러면 exe 는 로그를 안 남겨
    #   "붙었는지" 확인할 방법이 없고, 아래 대기 루프가 그냥 시간만 보내고 Start 를 누른다.
    #   실측: exe 는 기동~접속준비에 8.2초가 걸리는데 확인 없이 Start 를 눌러
    #   우리 기체가 무응답으로 지연 패널티를 받았다(0.0 vs 100.0).
    Start-Process $ep -WorkingDirectory (Split-Path -Parent $ep) -RedirectStandardOutput $log
    return
  }
  # [2026-09-04] cutoffbt = 컷오프 BT 복원본(student/cutoff_bt.py)을 파이썬 클라이언트로 붙인다.
  if ($bundle -eq "cutoffbt") {
    $pre0 = "`$host.UI.RawUI.WindowTitle='ATTACH-$Tag'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; `$env:PYTHONUTF8='1'; `$env:PYTHONUNBUFFERED='1'; Set-Location '$wd'; "
    Start-Process powershell -ArgumentList '-Command',($pre0 + "& '$py' -u student\tools\cutoff_bt_client.py --team-name $name --server-ip 127.0.0.1 --server-port 9999 | Tee-Object -FilePath '$log'")
    return
  }
  $pre = "`$host.UI.RawUI.WindowTitle='ATTACH-$Tag'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; `$env:PYTHONUTF8='1'; `$env:PYTHONUNBUFFERED='1'; Set-Location '$wd'; "
  # no -NoExit: the window closes when the client exits (its output is in $log). -NoExit left a dead console per failed attach (8/30).
  Start-Process powershell -ArgumentList '-Command',($pre + "& '$py' -u attach_client.py --bundle '$bundle' --team-name $name --server-ip 127.0.0.1 --server-port 9999 | Tee-Object -FilePath '$log'")
}
# fail fast on a bad bundle path (8/30: a newline inside the path made attach_client die -> 3 viewer restarts per match, 6 min lost)
$A = "$A".Trim(); $B = "$B".Trim()
foreach ($bp in @($A, $B)) {
  if ($bp -like "exe:*") {
    if (-not (Test-Path $bp.Substring(4))) { "[$Tag] ABORT: exe not found: [$($bp.Substring(4))]"; exit 3 }
    continue
  }
  if ($bp -ne "cutoff" -and $bp -ne "cutoffbt" -and -not (Test-Path (Join-Path $bp "policy_weights.pkl.gz"))) { "[$Tag] ABORT: bundle not found: [$bp]"; exit 3 }
}
function GameControlCount($log) {
  if (-not (Test-Path $log)) { return 0 }
  $m = Get-Content $log -ErrorAction SilentlyContinue | Select-String 'MT_GameControl=(\d+)' | Select-Object -Last 1
  if ($m) { return [int]$m.Matches[0].Groups[1].Value } else { return 0 }
}
# 스폰 거리 검증: 클라이언트 로그의 frame=0 pos=(x,y,z) 두 기체로 거리(m) 계산. 2000ft=609.6 / 2500ft=762 / 3000ft=914.4 m.
#   프리셋 클릭이 안 먹으면 기본 스폰(수천 km)이라 여기서 걸린다 — 고정 대기·좌표 대신 "패킷으로 확인될 때까지" 반복.
# [2026-09-04] 시나리오 IC(HABFM/OBFM_RED/SCISSORS) 추가. 거리 프리셋은 초록 화살표 픽셀로 확인되지만
#   시나리오 버튼엔 그 표시가 없다 -> 스폰 거리를 기대값 대신 정상 범위로만 검사한다(기본 스폰은 수천 km 라 걸린다).
$SCEN = @("habfm", "obfm_red", "scissors")
$EXPECT = @{ "2000ft" = 609.6; "2500ft" = 762.0; "3000ft" = 914.4 }[$Preset]
function SpawnDistance($log) {
  if (-not (Test-Path $log)) { return -1 }
  $p = @{}; $f = @{}
  foreach ($m in (Get-Content $log -ErrorAction SilentlyContinue | Select-String 'plane_id=([01]) age=\S+ frame=(\d+) pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\)')) {
    $g = $m.Matches[0].Groups; $id = $g[1].Value; $fr = [int]$g[2].Value
    if (-not $f.ContainsKey($id) -or $fr -lt $f[$id]) { $f[$id] = $fr; $p[$id] = @([double]$g[3].Value, [double]$g[4].Value, [double]$g[5].Value) }   # 가장 이른 프레임(첫 패킷은 frame 3 쯤)
  }
  if ($p.Count -lt 2) { return -1 }
  $a = $p["0"]; $b = $p["1"]
  return [math]::Sqrt(($a[0]-$b[0])*($a[0]-$b[0]) + ($a[1]-$b[1])*($a[1]-$b[1]) + ($a[2]-$b[2])*($a[2]-$b[2]))
}
$na = if ($A -eq "cutoff") { "cutoff" } elseif ($A -eq "cutoffbt") { "CutoffReplica" } elseif ($A -like "exe:*") { [IO.Path]::GetFileNameWithoutExtension($A.Substring(4)) } else { Split-Path -Leaf $A }
$nb = if ($B -eq "cutoff") { "cutoff" } elseif ($B -eq "cutoffbt") { "CutoffReplica" } elseif ($B -like "exe:*") { [IO.Path]::GetFileNameWithoutExtension($B.Substring(4)) } else { Split-Path -Leaf $B }
$la = "$out\match_${Tag}_a.log"; $lb = "$out\match_${Tag}_b.log"
# exe/cutoff 는 python 로그를 안 남긴다 -> 스폰거리 검증은 로그를 남기는 쪽을 봐야 한다.
$watch = if ($A -ne "cutoff" -and $A -notlike "exe:*") { $la } else { $lb }
$ok = $false
for ($attempt = 1; $attempt -le 3 -and -not $ok; $attempt++) {
  & $py tools\viewer_ctl.py kill | Out-Null
  # attach_client python only (role match) -- a blanket python kill took the dashboard down (8/30)
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*attach_client.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like "*ATTACH-$Tag*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
# [2026-09-13] exe 클라이언트는 Start-Process 로 직접 띄워서 위 ATTACH-<Tag> 그물에 안 걸린다.
#   판이 끝나도 살아남아 "서버 연결이 끊겼습니다. 3초 뒤 재접속합니다" 를 무한 반복한다(실측).
#   다음 판 뷰어에 옛 클라이언트가 붙어 판이 엉키므로 역할명으로 확실히 닫는다.
foreach ($bp in @($A, $B)) {
  if ($bp -like "exe:*") {
    $en = [IO.Path]::GetFileNameWithoutExtension($bp.Substring(4))
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq $en } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
  }
}
  Remove-Item $la, $lb -ErrorAction SilentlyContinue
  Start-Process "C:\topgunfinal\BattleServer_V1.2_VeryLow\DogFightViewer.exe"
  # wait for the viewer window instead of a fixed 12 s (8/30: user asked for back-to-back matches)
  for ($k = 0; $k -lt 20; $k++) { Start-Sleep -Seconds 1; & $py tools\viewer_ctl.py find 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { break } }
  Start-Sleep -Seconds 3
  if ($SCEN -contains $Preset) {
    & $py tools\viewer_ctl.py click $Preset 2 | Out-Null; "[$Tag] scenario $Preset clicked (스폰 기하로 확인)"
  } else {
    $pl = & $py tools\viewer_ctl.py preset $Preset; "[$Tag] $pl"
    # [2026-09-13] 픽셀 확인 실패로 판을 버리지 않는다(사용자 보고: 화면엔 2000ft 가 선택돼 있는데 인식이 안 돼 꺼진다).
    #   green px 0 으로 읽힌 실측이 있다 — 창이 덮였거나 캡처 타이밍이라 클릭 성패와 무관하다.
    #   진짜 관문은 아래 스폰 거리 패킷 검증(609.6 m ±60) 하나. 프리셋이 정말 안 먹었으면 기본 스폰(수천 km)이라 거기서 걸린다.
    if ($LASTEXITCODE -ne 0) { "[$Tag] attempt $attempt preset 픽셀확인 실패 -> 스폰 거리로 검증 (계속 진행)" }
  }
  # [2026-09-04 사용자 지시] 저고도 시작 판: Alt(ft) 입력칸을 바꾼다(기본 15000). 0 이면 안 건드린다.
  if ($AltFt -gt 0) { $al = & $py tools\viewer_ctl.py alt $AltFt; "[$Tag] $al" }
  if ($SpeedMs -gt 0) { $sm = & $py tools\viewer_ctl.py speed $SpeedMs; "[$Tag] $sm" }
  & $py tools\viewer_ctl.py click openserver 2 | Out-Null
  Start-Sleep -Seconds 1
  # attach A then B; poll the client log for its plane id (max 10 s) instead of a fixed 7 s wait
  Attach $A $na $la
  # exe 는 단일 파일 압축해제 + torch/ray import 로 기동이 느리다(실측 8.2초) -> 넉넉히 기다린다.
  $waitA = if ($A -like "exe:*") { 40 } else { 10 }
  if ($A -eq "cutoff") { Start-Sleep -Seconds 3 } else { for ($k = 0; $k -lt $waitA; $k++) { Start-Sleep -Seconds 1; if ((Test-Path $la) -and (Get-Content $la -ErrorAction SilentlyContinue | Select-String 'MT_SetPlaneID' -Quiet)) { break } } }
  if ($A -like "exe:*") { "[$Tag] A(exe) 접속확인 대기 ${k}초 · MT_SetPlaneID " + $(if ((Test-Path $la) -and (Get-Content $la -ErrorAction SilentlyContinue | Select-String 'MT_SetPlaneID' -Quiet)) { "확인됨" } else { "미확인(주의)" }) }
  Attach $B $nb $lb
  if ($B -eq "cutoff") { Start-Sleep -Seconds 3 } else { for ($k = 0; $k -lt 10; $k++) { Start-Sleep -Seconds 1; if ((Test-Path $lb) -and (Get-Content $lb -ErrorAction SilentlyContinue | Select-String 'MT_SetPlaneID' -Quiet)) { break } } }
  # PlaneInfo 는 Start 뒤에만 온다 -> Start 누르고 첫 프레임 위치로 스폰 거리를 확인. 틀리면 이 attempt 를 버리고 뷰어부터 다시.
  & $py tools\viewer_ctl.py click start | Out-Null
  for ($k = 0; $k -lt 8; $k++) {
    Start-Sleep -Seconds 1
    $d = SpawnDistance $watch
    if ($d -gt 0) { break }
  }
  if ($SCEN -contains $Preset) {
    if ($d -gt 50 -and $d -lt 8000) { $ok = $true }
    else { "[$Tag] attempt $attempt spawn dist=$([math]::Round($d)) m out of range -> scenario not applied, viewer restart" }
  }
  elseif ($d -gt 0 -and [math]::Abs($d - $EXPECT) -lt 60) { $ok = $true }
  else { "[$Tag] attempt $attempt spawn dist=$([math]::Round($d)) m (expect $EXPECT) -> preset not applied, viewer restart" }
}
if (-not $ok) { "[$Tag] ABORT: preset not applied after 3 attempts"; exit 2 }
"[$Tag] spawn dist OK $([math]::Round($d,1)) m ($Preset)"
& $py tools\spawn_geom.py $watch   # 스폰 기하(기수차·ATA) — 헤드온인지 꼬리잡기인지 숫자로 남긴다
Start-Sleep -Seconds 1
& $py tools\viewer_ctl.py key 5 | Out-Null
# HP 시계열: 화면 HP 바를 0.25 s 마다 읽는 감시 python (역할명 hpwatch) -> match_<Tag>_hp.csv. 패킷엔 HP 가 없다.
Start-Process $py -ArgumentList "tools\viewer_ctl.py","hpwatch","$out\match_${Tag}_hp.csv","$MaxSec" -WindowStyle Hidden
"[$Tag] Blue=$na Red=$nb started $(Get-Date -Format HH:mm:ss)"
# exe/cutoff 는 python 로그를 안 남긴다 -> 스폰거리 검증은 로그를 남기는 쪽을 봐야 한다.
$watch = if ($A -ne "cutoff" -and $A -notlike "exe:*") { $la } else { $lb }
$t = 0; $nextShot = 15
while ($t -lt $MaxSec) {
  Start-Sleep -Seconds 1; $t += 1
  if ($t -ge $nextShot) { & $py tools\viewer_ctl.py hp "$out\match_${Tag}_t$t.png" | Out-Null; $nextShot = if ($t -lt 30) { 30 } else { $t + 30 } }
  # watch BOTH client logs: the losing client stops logging when its plane dies, so its GameControl count stays at 1
  # (8/30 sp3(Blue) vs 7200: kill at 23 s, end only detected at MaxSec 215 s). Either log reaching 2 = game over.
  $gc = 0; foreach ($lg in @($la, $lb)) { $v = GameControlCount $lg; if ($v -gt $gc) { $gc = $v } }
  if ($gc -ge 2) { Start-Sleep -Seconds 1; break }
}
& $py tools\viewer_ctl.py shot "$out\match_${Tag}_end.png" | Out-Null
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*hpwatch*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
# 클라이언트 창 정리: 창 제목은 늦게 붙어 못 믿는다 -> 명령줄에 ATTACH-<Tag> 가 있는 powershell 을 닫는다 (자기 자신 제외)
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like "*ATTACH-$Tag*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
# [2026-09-13] exe 클라이언트는 Start-Process 로 직접 띄워서 위 ATTACH-<Tag> 그물에 안 걸린다.
#   판이 끝나도 살아남아 "서버 연결이 끊겼습니다. 3초 뒤 재접속합니다" 를 무한 반복한다(실측).
#   다음 판 뷰어에 옛 클라이언트가 붙어 판이 엉키므로 역할명으로 확실히 닫는다.
foreach ($bp in @($A, $B)) {
  if ($bp -like "exe:*") {
    $en = [IO.Path]::GetFileNameWithoutExtension($bp.Substring(4))
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq $en } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
  }
}
"[$Tag] done ${t}s -> $out\match_${Tag}_end.png"
