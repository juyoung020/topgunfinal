# 교전서버(BattleServer_V1.2_VeryLow) — 붙이는 법 (2026-08-28 실측)

## 위치 조건 (이걸 어기면 안 돌아간다)

- **전체 워크스페이스를 `C:\` 최상단에 둔다: `C:\topgunfinal\`** — 폴더 이름에 **공백·한글·밑줄 금지**.
  `Desktop\topgun_본선\...`(공백 `user one` + 한글)에 두었을 땐 컷오프 클라이언트가 `Fatal error!` 로 죽고 시뮬이 시작되지 않았다.
- 공식 컷오프 클라이언트도 최상단 ASCII 경로: **`C:\cutoff_model\unreal_bt_client.exe`** (Downloads 원본과 동일 파일).
- 뷰어 exe: `C:\topgunfinal\BattleServer_V1.2_VeryLow\DogFightViewer.exe` (이 폴더는 Downloads 의 `BattleServer_V1.2_VeryLow (1).zip` 원본 231 파일. 로그·설정이 쌓인 옛 폴더는 폐기).

## 붙이기 전 점검
- `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` — VRAM 여유 없으면(다른 모델·Docker·WSL) 서버 틱이 떨어진다. `ollama ps` / Docker Desktop / `wsl --shutdown`.
- 원격(RustDesk)으로 붙을 땐 창 이동·좌표 클릭 대신 사용자가 뷰어 조작, 클라이언트는 `[Console]::OutputEncoding=UTF8` 로 띄운 창에서.

## 절차 (매판 뷰어를 새로 켠다 — Stop_Simulation 으론 재시작이 안 된다)

1. `DogFightViewer.exe` 실행 → 창이 뜨면 시나리오 `2000ft`(예선/본선 1~3R 거리) → `OpenServer` **두 번 클릭**(첫 클릭은 창 활성화에 먹힘) → `Server On` 확인. Port 9999, Speed 200, Alt 15000 ft 기본.
2. 클라이언트 접속. **먼저 붙는 쪽이 plane 0 = Blue**, 두 번째가 Red.
   ```
   cd C:\topgunfinal\Update\강화학습환경
   launch_attach.bat ..\..\model\final_sp_iter0160 iter160 127.0.0.1 9999      # 우리 번들 (model\ 아래 아무거나)
   C:\cutoff_model\unreal_bt_client.exe                                          # 공식 컷오프 (인자 없음, 127.0.0.1:9999 고정)
   ```
   제출 패키지 그대로 붙일 땐 그 폴더에서 `python student\my_submission.py --server-ip 127.0.0.1 --server-port 9999`.
3. **컷오프가 `plane_id=1` 을 받으면 곧바로 `Start`** — 컷오프는 서버 응답이 5~7초 없으면 경고 후 스스로 나간다. 접속 후 15초 기다렸다가 Start 를 누르면 이미 없다.
4. Start 후 키 `5` = 관전 시점. 판정은 **상단 HP 바 화면**(왼쪽 Blue / 오른쪽 Red, 승자 이름 "xxx Win" 표시). 로그 CSV 재적분은 근소차에서 틀린 전례.
5. 진영 교대(접속 순서 바꿔) 한 판 더. 2000ft 정면은 Red(plane1) 슬롯이 유리한 경향.

## 자동화 (2026-08-29 현행) — `tools\match_run.ps1` 한 판, `tools\viewer_ctl.py` 창 제어

```
cd C:\topgunfinal\Update\강화학습환경
powershell -ExecutionPolicy Bypass -File tools\match_run.ps1 -A <Blue 번들|cutoff> -B <Red 번들|cutoff> -Tag <이름>
   예) -A ..\..\model\champion_v2r6_iter7200 -B ..\..\model\recv_snap9980 -Tag i7200_vs_r9980
   예) -A ..\..\model\champion_v2r6_iter7200 -B cutoff -Tag i7200_vs_cutoff   (전 챔피언 폴더는 prev_champion_v2r5_iter1000 으로 개명, 표의 champion_v2r5_iter1000 = 그 번들)
```
- 한 판 = 뷰어 전부 종료 → 새 뷰어 → 창을 주 모니터 (0,0) 1920×1080 에 배치 → `2000ft` 2회 클릭 → `OpenServer` 2회 → A 접속(Blue) → B 접속(Red) → `Start` → 키 5 → 15·30·60·…·210 s 에 HP 바 캡처 → 끝 화면 캡처 → 클라이언트 창(제목 `ATTACH-<Tag>`) 닫기.
- 산출물: `artifacts\eval_visual\match_<Tag>_t{15,30,…}.png`(HP 바 스트립), `match_<Tag>_end.png`(전체 화면, "xxx Win"/"Draw" 표시), `match_<Tag>_{a,b}.log`(클라이언트 로그, UTF-16 — PowerShell `Select-String` 로 읽는다).
- **판정 = end.png 의 HP 바와 "Win" 표시**(사람이 읽음). 서버 CSV(`DogFightViewer\Binaries\Win64\Log\M_D_H_M_{0,1}.csv`, 60 Hz 위치·자세, HP 없음)는 뷰어를 닫아야 flush 되며 궤적 재구성용.
- 여러 판 순차: `artifacts\eval_visual\match_queue_blue.ps1` 처럼 목록을 도는 스크립트를 **별도 창**(`Start-Process powershell -File`)으로 띄운다 — 도구 호출이 끊겨도 판이 이어진다. 진행은 `match_queue.log`.
- 뷰어 창 제어: `python tools\viewer_ctl.py kill|find|click <2000ft|openserver|start> [n]|key 5|shot <png>|hp <png>`. 뷰어 프로세스 실제 이름 **DogFightViewer-Win64-Shipping**(`Stop-Process DogFightViewer` 로는 안 죽음 → 두 개가 겹쳐 떠서 클릭이 옛 창에 간 사고). 프리셋·OpenServer 는 첫 클릭이 창 활성화에 먹히므로 2회.
- PowerShell 변수는 대소문자 구분이 없다: 큐 스크립트에서 `$M`(모델 폴더)과 루프변수 `$m` 이 같은 변수라 번들 경로가 깨져 두 클라이언트가 같은 번들로 붙은 사고(8/29). 이름을 다르게.
- **8/30 구조 수정 (잔재 창·속도)**: ① attach 창·큐 창을 `-NoExit` 없이 띄운다 — 클라이언트가 죽거나 큐가 끝나면 창이 스스로 닫힌다(출력은 `match_<Tag>_{a,b}.log`·큐 로그에 전부 남음). ② `match_run.ps1` 은 시작 전에 번들 경로 `policy_weights.pkl.gz` 존재를 검사해 없으면 즉시 `ABORT`(경로에 개행이 섞여 attach 가 죽고 뷰어를 3번 재시작하던 사고). ③ 고정 대기(뷰어 12 s·접속 7 s·종료 폴링 5 s) 대신 뷰어 창 감지·클라이언트 `MT_SetPlaneID` 감지·1 s 폴링. ④ `viewer_ctl.py kill` 은 뷰어 프로세스가 실제로 사라질 때까지 기다린다(2 s 고정 대기로는 옛 창이 남아 `viewer windows x2` → 프리셋이 옛 창에 클릭돼 매판 재시작). ⑤ python 은 `attach_client.py` 명령줄만 죽인다(전체 python 킬은 대시보드·트레이너를 잡는다). ⑥ 큐 스크립트는 **한 줄에 한 항목**으로 쓰고 `Parser::ParseFile` 로 문법 검사 뒤 띄운다 — 긴 배열 한 줄을 `Out-File` 로 쓰면 줄이 감겨 경로에 개행이 들어간다. 파일 인코딩은 ASCII 가 아니라 **UTF-8(BOM)** (작업 루트 8.3 이름에 한글이 있어 ASCII 로 쓰면 `???~1`).
- 정리: 판이 끝나면 `ATTACH-<Tag>` 창은 자동으로 닫힌다. 남은 잔재는 python 자식이 없는 attach 창만 골라 닫는다(`Get-CimInstance Win32_Process` 로 자식 확인). 트레이너·MCP·사용자 창은 건드리지 않는다.
- **스폰 검증(고정 대기·좌표 대신 패킷으로)**: 프리셋 클릭이 안 먹는 일이 잦다(8/29 세 번). `match_run.ps1` 은 Start 뒤 클라이언트 로그의 첫 PlaneInfo(frame≈3) 두 기체 `pos=(x,y,z)` 로 스폰 거리를 재서 2000ft=609.6 m(2500ft 762 / 3000ft 914) ±60 m 가 아니면 그 판을 버리고 뷰어부터 다시(최대 3회). PlaneInfo 는 Start 전엔 안 온다. 로그 `spawn dist OK 609.8 m` 줄이 있어야 유효한 판.
- 뷰어 창은 반드시 하나: `viewer_ctl.py kill` 뒤 새로 띄운다(두 개면 클릭이 옛 창에 가서 프리셋이 안 먹음).
- 붙이기 전 점검: `nvidia-smi` VRAM 여유(Ollama 등 상주 모델이 잡고 있으면 서버 틱이 3 Hz 로 떨어져 Delay Count·양쪽 HP 감소), Docker/WSL. 정상 = 클라이언트 PlaneInfo 초당 120개(2기×60 Hz).

## (구) 모니터2 좌표 자동화 (`tools\server_ui.py`, 원격 세션에선 창이 화면 밖으로 가서 못 씀)

```
python tools\server_ui.py find              # 창 찾아 모니터2 (-1920,-40,1920,1080) 로 이동
python tools\server_ui.py click 2000ft
python tools\server_ui.py click openserver 2
python tools\server_ui.py click start
python tools\server_ui.py key 5
python tools\server_ui.py shot out.png      # 모니터2 캡처 (HP 바 판정용)
```
버튼 좌표: openserver(-1074,944) start(-950,996) 2000ft(-1327,825) 2500ft(-1180,825) 3000ft(-1034,825) HABFM(-1327,875) OBFM_RED(-1180,879) SCISSORS(-1034,875).
접속 확인은 클라이언트 콘솔의 `[Last RX] type=MT_PlaneInfo`(시뮬 중) / `MT_GameControl`(종료). `MT_SetPlaneID` 에서 멈춰 있으면 Start 가 안 된 것.

## 실측 기록 (2026-08-29, 2000ft, 판정 = 화면 HP)

| Blue | Red | 결과 |
|---|---|---|
| v2r5_iter1000 | 컷오프 | 200 s 종료 99.1 : 75.6 판정승 |
| 컷오프 | v2r5_iter1000 | 종료 63.3 : 96.4 판정승(Red 슬롯) |
| v2r5_iter1000 | ladder5220 | 23 s 격추승 (8.9 : 0) |
| ladder5220 | v2r5_iter1000 | 23 s 격추승(Red 슬롯) (0 : 7.1) |
| v2r5_iter1000 | final_sp3_iter0400 | 22 s 격추승 (100 : 0) |
| v2r5_iter1000 | league_v3 (완전 회피형) | 155 s 격추승 (68.7 : 0) |
| champion_v2r5_iter1000 | league_v4 (회피형) | 165 s 격추승 (100 : 0) |
| champion_v2r5_iter1000 | r9980 | 27 s 격추승 (89.8 : 0) |
| champion_v2r5_iter1000 | v1 s48 (snap12241) | **Draw** 23 s 동시격추 (0 : 0) |
| champion_v2r5_iter1000 | sub_cand_snap12241 (8/20 챔피언) | 25 s 격추승 (3.2 : 0) |
| champion_v2r5_iter1000 | c13280 (s45, 직전 제출본) | **Draw** 23 s 동시격추 (0 : 0) |
| champion_v2r5_iter1000 | peak3100 | 27 s 격추승 (0.2 : 0) |
| champion_v2r5_iter1000 | scrim_exp025 | 23 s 격추승 (31.2 : 0) |
| champion_v2r5_iter1000 | aimcur_0823 | 200 s 종료 판정승 (94.8 : 58.2) |
| champion_v2r5_iter1000 | aimangle_v4_0824 | 200 s 종료 판정승 (94.9 : 73.2) |
| champion_v2r5_iter1000 | symmetric_iter1920 (v2 부모) | 99 s 격추승 (72.8 : 0) |
| champion_v2r5_iter1000 | **s52_ladder5220_beaten** | **81 s 격추패 (0 : 100)** — 유일한 패배 |

## 실측 기록 (2026-08-30, 2000ft, 판정 = 화면 HP) — final_v2r6 후보 3200 vs 7200
| Blue | Red | 결과 |
|---|---|---|
| final_v2r6_iter3200 | final_v2r6_iter7200 | **Draw** 25 s 동시격추 (0 : 0) |
| final_v2r6_iter7200 | final_v2r6_iter3200 | **Draw** 25 s 동시격추 (0 : 0) |
| final_v2r6_iter7200 | 컷오프 | 21 s 격추승 (60.7 : 0) |
| 컷오프 | final_v2r6_iter7200 | 21 s 격추승(Red 슬롯) (0 : 55.6) |
| final_v2r6_iter3200 | 컷오프 | 52 s 격추승 (20.2 : 0) |
| 컷오프 | final_v2r6_iter3200 | 52 s 격추승(Red 슬롯) (0 : 51.2) |
컷오프(풀 밖 상대) 기준 7200 이 3200 보다 빠르고(21 s vs 52 s) 덜 맞음(HP 56~61 vs 20~51) — 사용자 판단: 7200 우선, 전 상대 Blue/Red 1판씩.

### 7200 전 상대 (2026-08-30 19:23~, 2000ft, Blue/Red 1판씩)
| Blue | Red | 결과 |
|---|---|---|
| final_v2r6_iter7200 | champion_v2r5_iter1000 | 22 s 격추승 (65.1 : 0) |
| champion_v2r5_iter1000 | final_v2r6_iter7200 | 23 s 격추승(Red 슬롯) (0 : 66.8) |
| final_v2r6_iter7200 | s52_ladder5220_beaten | 28 s 격추승 (50.5 : 0) |
| s52_ladder5220_beaten | final_v2r6_iter7200 | 28 s 격추승(Red 슬롯) (0 : 53.7) |
| final_v2r6_iter7200 | final_sp3_iter0400 | 23 s 격추승 (53.5 : 0) |
| final_sp3_iter0400 | final_v2r6_iter7200 | 23 s 격추승(Red 슬롯) (0 : 51.1) — 종료 감지는 215 s(패자 로그만 봐서), 이후 양쪽 로그 감시로 수정 |
| final_v2r6_iter7200 | cand_s48_snap12241 | **25 s 격추패 (0 : 0.05)** — 정면 맞교환, s48 이 HP 0.05 남김 |
| cand_s48_snap12241 | final_v2r6_iter7200 | **Draw** 25 s 동시격추 (0 : 0) |
| final_v2r6_iter7200 | recv_aimcur_0823 | 22 s 격추승 (94.1 : 0) |
| recv_aimcur_0823 | final_v2r6_iter7200 | 22 s 격추승(Red 슬롯) (0 : 95.6) |
| final_v2r6_iter7200 | recv_aimangle_v4_0824 | 22 s 격추승 (94.5 : 0) |
| recv_aimangle_v4_0824 | final_v2r6_iter7200 | 22 s 격추승(Red 슬롯) (0 : 95.6) |
| final_v2r6_iter7200 | recv_league_v4_best60 | 53 s 격추승 (82.3 : 0) |
| recv_league_v4_best60 | final_v2r6_iter7200 | 53 s 격추승(Red 슬롯) (0 : 87.7) |
| final_v2r6_iter7200 | sub_cand_peak3100 | **Draw** 29 s 동시격추 (0 : 0) |
| sub_cand_peak3100 | final_v2r6_iter7200 | **29 s 격추패(Red 슬롯) (1.5 : 0)** — peak3100 이 HP 1.5 남김 |
| final_v2r6_iter7200 | sub_cand_snap12241 | 28 s 격추승 (3.2 : 0) — 간신히 |
| sub_cand_snap12241 | final_v2r6_iter7200 | 28 s 격추승(Red 슬롯) (0 : 2.3) — 간신히 |
| final_v2r6_iter7200 | recv_snap9980 | 101 s 격추승 (16.7 : 0) |
| recv_snap9980 | final_v2r6_iter7200 | 84 s 격추승(Red 슬롯) (0 : 7.5) |
| final_v2r6_iter7200 | recv_scrim_exp025 | **Draw** 26 s 동시격추 (0 : 0) |
| recv_scrim_exp025 | final_v2r6_iter7200 | **Draw** 26 s 동시격추 (0 : 0) |
| final_v2r6_iter7200 | symmetric_iter1920 | 22 s 격추승 (78.9 : 0) |
| symmetric_iter1920 | final_v2r6_iter7200 | 22 s 격추승(Red 슬롯) (0 : 78.9) |

교전 기하 분석(궤적·거리·ATA·첫 WEZ 거리, 22판): `..\docs\교전기하_7200_20260830\README.md` — 첫 WEZ 진입 전 판 850~914 m(914 m 부터 쏨), 전 판 19~27 s 정면 머지 한 번으로 결판. 도구 `tools\server_traj.py`, HP 시계열은 `viewer_ctl.py hpwatch`(match_run 자동).

**7200 합계 (컷오프 포함 26판, Blue/Red 1판씩)**: **20승 4무 2패**. 회피형(aimcur·aimangle·league)·컷오프·champion·s52·sp3·symmetric·snap9980 은 양 슬롯 전승. 못 잡은 건 전부 **정면 맞교환형 옛 계보**: s48_snap12241(패·무), peak3100(무·패 — 상대 HP 1.5 남음), scrim_exp025(무·무), sub_cand_snap12241 은 HP 2~3 남기고 간신히 승. 즉 실서버 약점 = 정면 2,000 ft 에서 22~29 s 에 서로 쏘는 교환전(리플레이 동시격추 증가와 같은 현상).
같은 계열 맞대결은 양 슬롯 모두 정면 25 s 맞교환 — 우열 판정 불가. 일반화 비교는 풀 밖 상대(컷오프)로: 아래 표에 추가.

합계(Blue, 유효판): 13전 **10승 2무 1패** — 무승부 2 = 우리 정면형 계보(s48·c13280) 동시격추, 패 1 = s52. 무효판(프리셋 미적용·뷰어 중복·VRAM)은 러너의 `spawn dist OK` 줄이 없는 것 — 재대결로 대체함.

## 실측 기록 (이전)

- 2026-08-28 21:0x: `final_sp_iter0160`(Blue) vs 컷오프(Red), 2000ft → **iter160 Win, 20초**(우리 HP 61, 컷오프 0).
- 예선 결과 전체: `..\docs\실서버_대전결과_20260824.md`.

## 함정

| 증상 | 원인 |
|---|---|
| 컷오프 `Fatal error!` | 경로에 공백·한글 → `C:\cutoff_model\` 로 |
| 타이머 200 고정, 기체가 안 움직임, 클라이언트 RX 가 `MT_SetPlaneID` 뿐 | Start 가 안 먹음(컷오프가 이미 나갔거나 창이 활성화 안 됨). 뷰어 재시작 후 3번 절차를 빨리 |
| 폴더 이름 변경/이동 실패 (`Access denied`) | 탐색기 창이 그 폴더를 열고 있음 |
| 뷰어 버튼이 안 눌림 | 다른 창(탐색기 등)이 뷰어를 덮고 있음 — `server_ui.py find` 로 앞으로 |
| Start 뒤 `Delay Count` 가 양쪽 똑같이 오르고 HP 가 같이 깎임, 클라이언트 PlaneInfo 초당 3개, 컷오프 자진 종료 | **GPU VRAM 부족** — 8/29 Ollama `gemma4:26b` 가 14 GB 점유(16 GB 중 15.2 GB 사용) → 뷰어 프레임 폭락 → 서버 틱(60 Hz)이 뷰어에 묶여 3 Hz. 클라이언트 연산은 0.12 ms/프레임로 무관. `ollama ps` 확인 → `ollama stop <모델>`. 붙이기 전에 `nvidia-smi` 로 VRAM 여유 확인 |
