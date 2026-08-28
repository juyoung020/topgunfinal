# 실행 메뉴얼 (본선 슬림 워크스페이스, 2026-08-28)

작업 루트: `C:\topgunfinal\Update\강화학습환경`

## 1. 본선 학습 (stage 35 selfplay_final — 학습 v1 iter_1120, 상대 = v1 자기 사본 70% + v2 고정 30%)

PowerShell 에서 (작업 루트에서, 창 세 개가 순서대로 뜬다 — 절대경로 없음):

```
powershell -File tools\launch.ps1 all
# 하나씩: sidecar | trainer(첫 기동, v1 iter_1120) | resume(이어받기, 최신 체크포인트) | dashboard
```

- 상대 풀: `final_sp\stage_35_selfplay_final\snapshots\snap_*` (snap_0000 = v1 시드, sidecar 가 100 iter 마다 승격, self 슬롯 = 직전 사본) 70% + `artifacts\models\AeroFlyer\sub_cand_ladder5220`(v2) 30%
- 산출물: `artifacts\curriculum\AeroFlyer\final_sp\` (console.log, training_log.csv, checkpoints 20 iter 마다), 리플레이 `artifacts\replays\AeroFlyer_final_sp`, 지표 `artifacts\dashboard\AeroFlyer_final_sp`
- 보상 핫튜닝: `final_sp\live_tune.json` 의 `reward` (target_pool 은 sidecar 가 씀 — 손대지 말 것). 코드값(`my_curriculum.py` stage 35)도 같이 맞춘다
- 이상 종료 후: `"C:\Users\user one\anaconda3\envs\aip\Scripts\ray.exe" stop --force`

## 2. 대시보드 (세 번째 창)

```
powershell -File tools\launch.ps1 dashboard
```
브라우저: http://127.0.0.1:7860/?tab=training  (bat 은 ASCII 전용 — 한글 주석 넣으면 chcp 뒤 cmd 파싱이 깨진다)

## 3. 실서버 판정 (300 iter 마다)

1. `..\..\BattleServer_V1.2_VeryLow\DogFightViewer\Binaries\Win64\DogFightViewer-Win64-Shipping.exe` 실행 → OpenServer → 프리셋(2000ft 등)
2. 두 클라이언트 접속 (먼저 붙는 쪽이 Blue/plane0):
   ```
   python attach_client.py --bundle artifacts\curriculum\AeroFlyer\final_sp\stage_35_selfplay_final\final_bundle --team-name cand --server-ip 127.0.0.1 --server-port 9999
   ..\..\cutoff_model\unreal_bt_client.exe          (공식 컷오프)
   python attach_client.py --bundle artifacts\models\AeroFlyer\recv_snap9980 --team-name r9980 --server-ip 127.0.0.1 --server-port 9999
   ```
3. Start → 판정은 **화면 HP 바**. 진영 교대(접속 순서 바꿔)로 2판. 매판 뷰어 재시작.

## 3-1. 새 라운드(새 태그) 시작

```
powershell -File tools\launch.ps1 sidecar -Tag <새태그>
powershell -File tools\launch.ps1 round2  -Tag <새태그>      # 출발 체크포인트는 launch_final_round2.bat 의 ROUND2_FROM (기본 final_sp iter_1400)
```
- 새 태그 폴더의 `live_tune.json`(보상 = 코드값) 과 `snapshots/snap_0000`(출발 사본) 은 미리 만들어 둔다 — preflight 가 없으면 FAIL.
- 이어받기는 `launch.ps1 resume -Tag <태그>`. 대시보드는 태그 무관(모든 run 표시).

## 4. 창·프로세스 정리 (반드시 이 스크립트로)

```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\ops_windows.ps1          # dry-run: 역할 프로세스·창 표
powershell -NoProfile -ExecutionPolicy Bypass -File tools\ops_windows.ps1 -Apply   # 자손 없는(끝난) 창 닫기 + 중복 대시보드 python 정리
```
- 살아있는 트레이너/sidecar/대시보드를 자손으로 가진 창은 KEEP. 트레이너·sidecar 는 이 스크립트가 절대 죽이지 않는다.
- 학습을 멈출 때: 트레이너 창에서 Ctrl+C → `ray stop --force` → 이 스크립트 `-Apply`.
- 손으로 `Stop-Process` 금지 (`dashboard.py` 패턴이 Ray 내부 대시보드에 걸려 학습이 통째로 죽은 사고, 8/28).

## 5. 이어받기

트레이너만 죽었을 때(sidecar·대시보드 살아 있음): `launch_final_resume.bat` — 최신 체크포인트(`checkpoints/iter_NNNN` 최대)를 자동으로 골라 `--resume` 으로 잇는다. 체크포인트는 20 iter 마다.

## 6. 제출 zip

```
"C:\Users\user one\anaconda3\envs\aip\python.exe" tools\make_submission_zip.py <artifacts\models\AeroFlyer 아래 번들 폴더명>
```
`student\my_submission.py` 의 `BUNDLE_DIR` 이 같은 번들을 가리켜야 한다. 팀명 `에어프라이어`.

## 7. 공식 문서 절차와의 관계

공식 절차 = `docs/2일차 강의 자료/2026_aip_rl_manual_rev8.md` Slide 18: `python train_curriculum.py --stages-module student.my_curriculum`, STEP1 설정 확인 → STEP2 smoke(1~10 iter) → STEP3 본실행. 우리 bat 은 이 명령에 PPO+LSTM·관측/보상 모듈·`--restore-checkpoint` 를 얹은 것.
문서에 없는 옵션(`--policy-std-cap --log-std-clip --gate-eval-episodes --start-stage --engagement-log-* --policy-probe-interval`)은 로컬 `[MOD-*]` 추가분 — 제출·서버 실행과 무관.
풀·스폰·보상 코드를 바꾼 뒤엔 본기동 전에 smoke 한 번(env 생성 + 몇 iter).
