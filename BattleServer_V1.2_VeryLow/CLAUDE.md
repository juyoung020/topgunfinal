# 교전서버(BattleServer_V1.2_VeryLow) — 붙이는 법 (2026-08-28 실측)

## 위치 조건 (이걸 어기면 안 돌아간다)

- **전체 워크스페이스를 `C:\` 최상단에 둔다: `C:\topgunfinal\`** — 폴더 이름에 **공백·한글·밑줄 금지**.
  `Desktop\topgun_본선\...`(공백 `user one` + 한글)에 두었을 땐 컷오프 클라이언트가 `Fatal error!` 로 죽고 시뮬이 시작되지 않았다.
- 공식 컷오프 클라이언트도 최상단 ASCII 경로: **`C:\cutoff_model\unreal_bt_client.exe`** (Downloads 원본과 동일 파일).
- 뷰어 exe: `C:\topgunfinal\BattleServer_V1.2_VeryLow\DogFightViewer.exe` (이 폴더는 Downloads 의 `BattleServer_V1.2_VeryLow (1).zip` 원본 231 파일. 로그·설정이 쌓인 옛 폴더는 폐기).

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

## 자동화 (모니터2 기준 좌표, `tools\server_ui.py`)

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

## 실측 기록

- 2026-08-28 21:0x: `final_sp_iter0160`(Blue) vs 컷오프(Red), 2000ft → **iter160 Win, 20초**(우리 HP 61, 컷오프 0).
- 예선 결과 전체: `..\docs\실서버_대전결과_20260824.md`.

## 함정

| 증상 | 원인 |
|---|---|
| 컷오프 `Fatal error!` | 경로에 공백·한글 → `C:\cutoff_model\` 로 |
| 타이머 200 고정, 기체가 안 움직임, 클라이언트 RX 가 `MT_SetPlaneID` 뿐 | Start 가 안 먹음(컷오프가 이미 나갔거나 창이 활성화 안 됨). 뷰어 재시작 후 3번 절차를 빨리 |
| 폴더 이름 변경/이동 실패 (`Access denied`) | 탐색기 창이 그 폴더를 열고 있음 |
| 뷰어 버튼이 안 눌림 | 다른 창(탐색기 등)이 뷰어를 덮고 있음 — `server_ui.py find` 로 앞으로 |
