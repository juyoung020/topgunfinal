# model/ — 추론용 경량 번들 (metadata.json + policy_weights.pkl.gz, 전부 16차원)

학습 이어가기용 네이티브 체크포인트(가중치+크리틱+옵티마이저)는 여기 없고 `Update/강화학습환경/artifacts/curriculum/.../checkpoints/` 에 그대로 있다.
붙이기: `Update/강화학습환경/launch_attach.bat <이 폴더 경로> <팀명> [ip] [port]` 또는 `python attach_client.py --bundle <경로> --team-name X --server-ip 127.0.0.1 --server-port 9999`.
실서버 결과: `docs/실서버_대전결과_20260824.md`. 붙이는 절차: `BattleServer_V1.2_VeryLow/CLAUDE.md`. 2026-08-28: `final_sp_iter0160` 이 컷오프를 20초에 격추(Blue 슬롯). 공식 컷오프는 `cutoff_model/unreal_bt_client.exe`.

| 폴더 | 정체 |
|---|---|
| `final_sp_iter0160` | 본선 학습 1차 (v1 베이스, 상대 v1사본 70%+v2 30%, iter 160) — 체크포인트 final_sp/.../iter_0160 에서 추출 |
| `v1_s48_snap12241` | v1 = s48 (0824_r48 stage48). 실서버 8승2무1패. 후방 공방 우수, 선회전 약함 |
| `v2_ladder5220` | v2 = ladder5220 (0815_ladder iter 5,220). 제출본. 정면·선회전 무패, 후방 방어 약함 |
| `s52_ladder5220_beaten` | s52 (0824_r48 stage52) — 5220 이긴 직후. ai전투기 대전/ladder5220_beaten_stage52_20260824.zip |
| `cand_c13280_s45` | c13280 — 직전 제출본 (snap_13280 계보 stage45) |
| `sub_cand_snap12241` | 12241 — 8/20 챔피언 (학습 풀 고정 상대였음) |
| `sub_cand_peak3100` | peak3100 — timefix 정점 (학습 풀 고정 상대였음) |
| `symmetric_iter1540` | v2 의 부모 (8/15 이전 자가대전) |
| `symmetric_iter1720` | v2 의 부모 |
| `symmetric_iter1920` | v2 의 부모 (stage 33 init) |
| `recv_snap9980` | r9980 — 팀원 별개 계열 (iter 9,980). v2 가 3000ft 레이스에서 진 상대 |
| `recv_scrim_exp025` | scrim — 팀원 산출물 |
| `recv_aimcur_0823` | aimcur — 팀원 산출물 |
| `recv_aimangle_v4_0824` | aimangle_v4 — 팀원 산출물 |
| `recv_league_v3_gen1_iter5` | league_v3 — 팀원 Elo 리그 |
| `recv_league_v4_best60` | league_v4 — 팀원 Elo 리그 |
