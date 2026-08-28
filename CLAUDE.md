# AI Pilot Top Gun Challenge — 본선 워크스페이스 (2026-08-28~)

F-16 1v1 도그파이트 RL. 예선 통과(제출 v2 = ladder5220). 이 폴더는 본선용 슬림 사본.
원본(37GB): `Desktop\topgun\Update\강화학습환경` + GitHub `juyoung020/topgun-rl-workspace`(비공개).

## 작업 방식 (반드시 지킬 것)

- **본학습은 보이는 창으로.** `tools\launch.ps1` 로만 띄운다(내부에서 8.3 경로 계산). 한글 경로를 그대로 Start-Process 에 주면 배트가 안 뜬다.
- **산출물은 절대 안 지운다.** 폐기는 `_DEPRECATED_<날짜>` 로 이름만 바꿔 `artifacts/_deprecated/` 로.
- **추측하지 말고 측정한다.** 보상 항 영향 = 학습 로그의 배치 간 std.
- **판정 = 실서버 화면 HP**(진영 교대). 학습 상태 = 그림 두 장(`eval_visual.py`). 숫자와 그림이 어긋나면 그림.
- **창·프로세스 정리는 `tools\ops_windows.ps1` 로만.** 손으로 `Stop-Process` 금지(Ray 대시보드를 죽여 학습이 통째로 내려간 사고, 8/28).
- 주석·문서엔 사실만(무엇을·왜·누구 지시). 내 해석·평가 금지. 사용자 판정 문서는 원문 그대로.
- 응답은 압축. 상세 이력은 `Update/강화학습환경/변경사항.md`. git 은 전역 신원 그대로.

## 경로

- **이 폴더는 `C:\topgunfinal` 처럼 C: 최상단·공백/한글/밑줄 없는 이름에 둔다** — 그래야 교전서버(컷오프 exe)가 돈다. 접속 절차는 `BattleServer_V1.2_VeryLow\CLAUDE.md`.
- 작업 루트 `<이 폴더>\Update\강화학습환경` (어디로 옮겨도 됨 — 절대경로 없음) · 교전 서버 `..\..\BattleServer_V1.2_VeryLow` · 컷오프 `..\..\cutoff_model\unreal_bt_client.exe`
- Python `C:\Users\user one\anaconda3\envs\aip\python.exe` (Ray/RLlib 2.54, torch) · 팀명 **`에어프라이어`**
- 절차서 `student/EXECUTION_MANUAL.md` · 도구·번들·손잡이 목록 `student/학습에 쓸수있는 도구.md` · 실서버 결과 `docs/실서버_대전결과_20260824.md`

## 현재 학습 (stage 35 `selfplay_final`, 태그 `final_sp`) — 사용자 결정 8/28

- PPO+LSTM cell 128 / seq 32 / 10 Hz / 관측 16D / std-cap 0.10. **커리큘럼(승급) 안 씀** — 바꾸는 건 풀 배치·보상·스폰뿐.
- 학습 = **v1**(`0824_r48/.../iter_1120` 복원). 상대 = **v1 자기 사본 70% + v2(ladder5220 고정) 30%**. self 슬롯 = 직전 사본(100 iter 전). Elo-PFSP 끔.
- 스폰 = 정면 2000ft 하나(서버 실측 line abreast, 4,572 m, 200 m/s). **다음 재기동(트레이너+sidecar 둘 다)부터**: 50:50 뒤집기(절반은 우리가 Red 자리) · 고도 변형 4,572 m 40% / 3,500 20% / 5,500 20% / **914 m(3,000 ft) 20%** · 랜덤화 150 m/±20°/롤 ±15°/피치 ±8° · `[MOD-TIE]` draw_rate 지표. 풀 16항목(self 8 + v2 8), sidecar `--lag-steps 1×8`. 코드 반영됨, 실행 중 학습엔 미적용.
- 보상 = v2 값 + 변경: **승 +1500 / 패·동시격추·시간종료 0 / 추락 −1700**, 딜 300×정밀배수(±1° ×2), 피딜·고고도·과속·WEZ·스냅·정면배수·적추락 0, 저고도선 2,500 ft. 전체 34항은 `final_sp/live_tune.json`(핫) = 코드.
- 300 iter 마다 실서버 판정(컷오프·v2·r9980 양 슬롯) → 정점 즉시 번들 보존.

## 학습 = 창 3개 (전부 떠 있어야 학습이다)

```
# 창 3개 (sidecar -> 트레이너 -> 대시보드). 절대경로 없음 — tools\launch.ps1 이 자기 위치에서 8.3 경로를 계산
powershell -File tools\launch.ps1 all          # 또는 sidecar | trainer | resume | dashboard 하나씩
# 상태 / 정리 / 실서버 / 제출
python student/tools/eval_visual.py --tag final_sp
powershell -File tools\ops_windows.ps1 [-Apply]
launch_attach.bat <번들> <팀명> [ip] [port]
python tools/make_submission_zip.py <번들폴더명>
```
2분 주기로 ① 세 창 생존 ② 스냅샷 승격 ③ iteration 진행 ④ RAM 을 같이 본다. 코드를 바꿨으면 본기동 전 smoke 한 번.

## 함정 (반복 금지)

- 보상은 `live_tune.json` 이 런타임에 덮는다 → 코드와 live_tune 을 **같이** 바꾼다. 번들 metadata 의 reward 는 기동 시점 값.
- sidecar 없으면 self 슬롯이 v1 출발점에 고정. sidecar 2개면 서로 GC → 러너 사망. 스냅샷은 `eval_kill_floor>0` 이어야 나온다.
- 동시격추는 env 가 "ownship destroyed"(패배)로 판정 → 로그 승률은 하한값. 같은 가중치 미러전도 3승 21패.
- `--init-bundle`(웜스타트)·`--anchor-bundle`(BC 앵커) 금지. 이어받기는 `--restore-checkpoint`(bat 이 %~dp0 로 절대경로를 만들어 줌) + `--resume`.
- bat 은 **순수 ASCII+CRLF**(`chcp 65001`+한글 주석이면 cmd 가 글자를 건너뜀). 코드·설정·문서에 **절대경로 금지**(폴더 이동으로 두 번 깨짐).
- `ray stop --force` 는 exit 255 로 뒤 명령 출력을 삼킨다 → 별도 호출. heredoc 안 python 문자열의 `\\` 는 반으로 준다 → 파일 스크립트.
- 최신 = 최강 아님(v2 가 후속작 전부 이김). 챔피언 판정은 계열 섞어 실서버로.
