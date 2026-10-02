# AI Pilot Top Gun Challenge — 본선 워크스페이스 (2026-08-28~)

F-16 1v1 도그파이트 RL. 예선 통과(제출 v2 = ladder5220). 이 폴더는 본선용 슬림 사본.
원본(37GB): `Desktop\topgun\Update\강화학습환경` + GitHub `juyoung020/topgun-rl-workspace`(비공개).

## 작업 방식 (반드시 지킬 것)

- **본학습은 보이는 창으로.** `tools\launch.ps1` 로만 띄운다(내부에서 8.3 경로 계산). 한글 경로를 그대로 Start-Process 에 주면 배트가 안 뜬다.
- **산출물은 절대 안 지운다.** 폐기는 `_DEPRECATED_<날짜>` 로 이름만 바꿔 `artifacts/_deprecated/` 로.
- **추측하지 말고 측정한다.** 보상 항 영향 = 학습 로그의 배치 간 std.
- **판정 = 리플레이 분석**(`student/tools/replay_judge.py`): 학습이 25 iter 마다 저장하는 리플레이(summary.json + Tacview CSV)만 읽어 v2 상대 판을 격추승/동시격추/격추패/추락/종료우위/종료열위로 센다. **별도 판정 실행·시뮬레이션은 안 돌린다**(8/29 사용자 결정 — CPU 를 학습에 준다). 실서버 화면 HP 는 제출 후보 최종 확인에만. 학습 상태 = 그림 두 장(`eval_visual.py`). 숫자와 그림이 어긋나면 그림. **판정·추세 보고는 리플레이(결정론, 25 iter 당 6판)로만 한다** — 러너 로그(`termination=` 줄)는 탐색 잡음 포함·Ray 샘플링이라 보조 자료이고, 쓰면 '로그 기준' 이라고 명시한다(8/29 지시: 장기전 추락률 표를 로그로 내고 리플레이라고 오해하게 한 뒤). 표본이 모자라면 '리플레이 N판, 판정 불가' 라고 쓴다.
- **창·프로세스 정리는 `tools\ops_windows.ps1` 로만.** 손으로 `Stop-Process` 금지(Ray 대시보드를 죽여 학습이 통째로 내려간 사고, 8/28).
- **경로는 태그 하나(`FINAL_SP_TAG`)에서만 파생**한다 — run·live_tune·스냅샷·리플레이·대시보드 전부. 어디에도 태그·경로를 따로 하드코딩하지 않는다. `tools\launch.ps1` 이 기동 전에 `tools\preflight.py` 로 일치를 검사해 FAIL 이면 안 띄운다(8/29: 대시보드 logdir 이 옛 태그를 봐서 리플레이가 안 보인 사고).
- 주석·문서엔 사실만(무엇을·왜·누구 지시). 내 해석·평가 금지. 사용자 판정 문서는 원문 그대로.
- 응답은 압축. 상세 이력은 `Update/강화학습환경/변경사항.md`. git 은 전역 신원 그대로.

## 경로

- **이 폴더는 `C:\topgunfinal` 처럼 C: 최상단·공백/한글/밑줄 없는 이름에 둔다** — 그래야 교전서버(컷오프 exe)가 돈다. 접속 절차는 `BattleServer_V1.2_VeryLow\CLAUDE.md`.
- 작업 루트 `<이 폴더>\Update\강화학습환경` (어디로 옮겨도 됨 — 절대경로 없음) · 교전 서버 `..\..\BattleServer_V1.2_VeryLow` · 컷오프 `..\..\cutoff_model\unreal_bt_client.exe`
- Python `C:\Users\user one\anaconda3\envs\aip\python.exe` (Ray/RLlib 2.54, torch) · 팀명 **`에어프라이어`**
- **현 챔피언(8/30) `model/champion_v2r6_iter7200`** (= `artifacts/models/AeroFlyer/final_v2r6_iter7200`, final_v2r6 는 iter 7400 에서 정지). 실서버 2000ft Blue/Red 1판씩 26판 **20승 4무 2패** — 컷오프 21 s 격추 ×2, 전 챔피언 v2r5_iter1000 ×2, s52 ×2, 회피형 ×6 전승; 패·무 = s48·peak3100·scrim(정면 25~29 s 맞교환). 교전 기하 `docs/교전기하_7200_20260830/`. 전 챔피언 `model/prev_champion_v2r5_iter1000`(구 champion_v2r5_iter1000). 판정 도구 `tools/match_run.ps1`(한 판, HP 시계열 자동), `tools/viewer_ctl.py`, `tools/server_traj.py`(궤적·WEZ).
- **다음 재기동 플랜 `student/다음라운드_플랜.md`** · 절차서 `student/EXECUTION_MANUAL.md` · 도구·번들·손잡이 목록 `student/학습에 쓸수있는 도구.md` · 실서버 결과 `docs/실서버_대전결과_20260824.md`

## 현재 학습 (stage 35 `selfplay_final`, **태그 `final_v2r7`**(8/30 밤, = final_v2r6 iter_7200(현 챔피언) 복원, **정면형 풀** s52 .20 / s48_snap12241 .20 / peak3100 .20 / scrim_exp025 .15 / sub_cand_snap12241 .10 / aimcur .075 / league_v4 .075 — 실서버에서 진/비긴/간신히 이긴 정면 맞교환형 중심, **[MOD-PAIR] 자리 짝**: 상대·고도를 뽑으면 Blue 자리 → 다음 판 같은 짝의 Red 자리(랜덤 50:50 아님), 보상·하이퍼·스폰은 v2r6 그대로; 이전 **`final_v2r6`**(8/29 밤, = final_v2r5 iter_1000(챔피언) 복원, **혼합 고정 풀** s52 .35 / aimcur .15 / aimangle .15 / sp3_iter0400 .15 / s48 .10 / league_v4 .10 — 실서버 13판에서 진/못 잡은 상대 중심, 스폰·보상·하이퍼는 v2r5 그대로; v2r5 = final_v2r4 iter_0200 복원 + lr 2e-4 / kl-target 0.02 / kl-coeff 0.1, iter 1201 까지·정점 iter 800~1000; v2r4 = 관측 램프+deck 선형+sink 게이트, iter 307 까지·정점 iter 175~199 승 11.8%·이후 정체; v2r3 = 절벽, v2r2/v2r1 이전 단계): 학습 주체 = **v2**(`0815_ladder/.../iter_5220` 네이티브 체크포인트), 상대 = **우리 `final_sp3_iter0400` 고정 100%**, 8/29 부터) — `final_sp`(1437)·`final_sp2`(3060)·`final_sp3`(460, v2 상대 리플레이 102판 격추패 0) 보존

- PPO+LSTM cell 128 / seq 32 / 10 Hz / 관측 16D / std-cap 0.10. 러너 16 / batch 16384 / minibatch 1024 / epochs 3 / γ 0.995 / GAE λ 0.95 / vf 비공유·vf-loss-coeff 0.5 / **lr 2e-4·kl-coeff 0.1·kl-target 0.02**(8/29 v2r5 부터; 그 전 lr 1e-4·kl-coeff 0.2·target 0.01. `--kl-target` 은 [MOD-KLTARGET]). **관측 `alt` 채널 저고도 램프(8/29)**: 2,000 ft(609.6 m) 위는 선형(0~14,000 m), 아래는 610 m −0.913 → 추락선 305 m **−1.5** 로 선형(해상도 13배) — `my_observation.py` `ALT_CLIFF_M/ALT_FLOOR_M/ALT_FLOOR_VAL`. 학습·제출·고정 상대가 같은 파일을 쓰므로 그 전 번들(iter0400 등)은 610 m 아래를 다르게 읽는다. **커리큘럼(승급) 안 씀** — 바꾸는 건 풀 배치·보상·스폰뿐.
- 계보: final_sp = v1 `0824_r48/.../iter_1120` 복원 → final_sp2 = final_sp iter_1400 복원(self 70%+v2 30%) → final_sp3 = final_sp2 iter_3060 복원(v2 고정 100%) → **final_v2r1~v2r4 = v2 iter_5220 복원, v2r5 = v2r4 iter_0200 복원, 상대 final_sp3_iter0400 고정**. 고정 상대 번들은 `my_curriculum.py` 의 `_FIXED_OPP_BY_TAG`(태그별). self 슬롯이 없는 동안 **sidecar 는 안 띄운다**. Elo-PFSP 끔.
- 스폰(2라운드 적용) = 2000ft **옆구리 배치(line abreast, 기수 반대)** 를 기본으로: Blue/Red 자리 50:50 뒤집기 · 고도 4,572/3,500/5,500/914 m = 2:1:1:1 · 랜덤화 150 m/±20°/롤 ±15°/피치 ±8° · **914 m 전용 선회 진입 래트 레이스 20%**(롤 +60, 반지름 600 m, 측정 미완). 풀 10항목(고정 상대 10: 고도 4종×2 자리 0.8 + 래트레이스 2 0.2). self 를 다시 넣으면 20항목 + sidecar `--lag-steps 1×10`.
- 보상(2라운드) = **승 +300(+시간보너스 200; 8/29 iter 3060 부터, 그 전 600) / 패·동시격추·시간종료 0 / 추락 −700**, **w_deck 12 선형**(2,500 ft 에서 0 → 1,000 ft 에서 −12; 8/29 iter 160 재기동부터. 그 전엔 로지스틱 폭 ±50 ft 계단으로 2,450 ft 아래 정액 −12. 크기 12 는 iter ~55 부터, 그 전 4) · w_recover 0(final_v2r1 에서 5 로 30 iter 시험, 무효) · **w_sink 0.03 저고도 게이트**(8/29 final_v2r4 iter 120 부터: 침하율 15 m/s 초과분 × 0.03, 2,000 ft 아래에서만·2,200 ft 까지 램프; 45° 강하 250 m/s = 스텝당 −4.9). 지표에 `draw_rate`(동시격추) 분리. 1라운드는 승 1500 / 추락 −1700 이었음 — reward_mean 은 라운드 간 비교 불가, 성분·승/무/패/추락률로 비교, 딜 300×정밀배수(±1° ×2), **피딜 50**(맞은 HP 당 −50, 8/29 iter ~360 부터) · 고고도·과속·WEZ·스냅·정면배수·적추락 0, 저고도선 2,500 ft. 전체 34항은 `final_sp/live_tune.json`(핫) = 코드.
- 리플레이 = 25 iter 마다 6판. 판정은 `replay_judge.py` 로 100 iter 구간(24판)별 고정 상대 결과. 번들(`policy_weights.pkl.gz`)은 100 iter 마다 `killfloor_probe/` 에 덮어쓰기 → 보존할 땐 `artifacts/models/AeroFlyer/<태그>_iterNNNN` 으로 복사(final_sp3_iter0300/0400 있음). 체크포인트는 20 iter.

## 학습 = 창 3개 (전부 떠 있어야 학습이다; v2 고정 풀에선 sidecar 없이 2개)

```
# 창 3개 (sidecar -> 트레이너 -> 대시보드). 절대경로 없음 — tools\launch.ps1 이 자기 위치에서 8.3 경로를 계산
powershell -File tools\launch.ps1 sidecar -Tag final_v2r6      # 반드시 1개 — 풀에 self 슬롯이 있을 때만(v2 고정 풀에선 생략)
powershell -File tools\launch.ps1 resume  -Tag final_v2r6     # 이어받기 (새 라운드 첫 기동: round2 — bat 기본값 final_v2r6 <- final_v2r5 iter_1000)
powershell -File tools\launch.ps1 dashboard
# 새 라운드 = 새 태그: sidecar/round2 에 -Tag <새이름>, launch_final_round2.bat 의 ROUND2_FROM 으로 출발 체크포인트 지정
# 상태 / 정리 / 실서버 / 제출
python student/tools/eval_visual.py --tag final_v2r6
python student/tools/replay_judge.py --tag final_v2r6   # 혼합 풀이면 상대별 표가 붙는다 --since 2400 --plot   # 판정: v2 상대 리플레이 집계 + artifacts/eval_visual/replay_judge_<tag>.png
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
