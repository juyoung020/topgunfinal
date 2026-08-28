<!--
원본 파일: 2일차 강의 자료/DogFightEnv_Log_Check_CLI_YAML_Guide.docx
원본 형식: DOCX (tables=9, images=0)
변환 방식: python-docx (문단·헤딩·코드블록·리스트·표 문서순 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# DogFightEnv_Log_Check_CLI_YAML_Guide

DogFightEnv 학습 로그 확인 CLI/YAML 매뉴얼

training_log, dashboard, policy_probe, engagement_replays, 통합 웹 포털 운영 절차

| 대상 | MyTrainEnv / Release | 작성일 | 2026-05-20 |
| --- | --- | --- | --- |

## 1. 목적과 사용 흐름

이 문서는 학습 중 숫자 로그와 실제 교전 replay 로그를 함께 확인하기 위한 운영 매뉴얼이다. 숫자 로그는 학습 안정성과 actor 출력 변화를 보고, 교전 replay는 현재 정책이 만든 궤적을 통합 웹 포털의 Replay 탭에서 재생해 확인한다.

- 빠른 수치 확인: training_log.csv, dashboard metrics.jsonl

- actor 출력 확인: policy_probe.csv / policy_probe.jsonl

- 실제 교전 궤적 확인: engagement_replays/의 Blue/Red Tacview CSV

- 시각화: tools/dashboard.py 통합 포털(Training / Replay 탭)

## 2. 로그 종류 요약

| 로그 | 켜는 방법 | 저장 위치 | 확인 목적 |
| --- | --- | --- | --- |
| training_log.csv | 기본 활성 | artifacts/logs/<name>/<tag>/ | reward, loss, alpha, replay size, tactical metric 확인 |
| dashboard metrics.jsonl | 기본 활성 또는 --dashboard-logdir | artifacts/dashboard/<run>/ | 브라우저에서 scalar trend와 config 확인 |
| policy_probe | --policy-probe-interval N | policy_probe.csv / policy_probe.jsonl | 고정 관측에 대한 actor action/state norm 변화 확인 |
| engagement_log | --engagement-log-interval N | engagement_replays/ | 현재 actor가 만든 실제 교전 궤적을 replay로 확인 |
| debug_io | --debug-io 또는 algo.lstm.debug_io | stdout | seq_lens, STATE_IN/OUT, Q concat shape 확인 |

## 3. 단일 학습 CLI 예시

SAC actor-critic LSTM 학습에서 숫자 probe와 교전 replay를 함께 켜는 예시다.

| ray stop --force <br> cd C:\Users\USER\workspace\DogFightEnv\DogFightEnv\Release <br> C:\Users\USER\anaconda3\envs\aip\python.exe train_rllib.py ` <br> --algorithm sac ` <br> --iterations 30 ` <br> --train-batch-size 64 ` <br> --rollout-fragment-length 8 ` <br> --use-lstm-sac ` <br> --lstm-scope actor_critic ` <br> --lstm-cell-size 64 ` <br> --max-seq-len 8 ` <br> --policy-probe-interval 5 ` <br> --policy-probe-steps 4 ` <br> --engagement-log-interval 10 ` <br> --engagement-log-steps 600 ` <br> --engagement-log-episodes 1 ` <br> --output-name f16_single_agent ` <br> --output-tag sac_lstm_log_check |
| --- |

| Note. 판단 근거: engagement_log는 실제 환경을 추가로 짧게 실행하므로 policy_probe보다 무겁다. 긴 학습에서는 interval을 10~50 이상으로 두고, steps는 먼저 120~600으로 짧게 시작하는 편이 안전하다. |
| --- |

## 4. YAML 작성 예시

scripts/run_experiment.py를 사용할 때는 YAML의 다음 섹션을 추가한다.

| policy_probe: <br> enabled: true <br> interval: 5 <br> steps: 4 <br> print: true <br> engagement_log: <br> enabled: true <br> interval: 10 <br> steps: 600 <br> episodes: 1 <br> print: true <br> dashboard: <br> enabled: true <br> logdir: artifacts/dashboard <br> algo: <br> lstm: <br> enabled: true <br> scope: actor_critic <br> cell_size: 64 <br> max_seq_len: 8 <br> debug_io: false |
| --- |

YAML 실행과 dry-run 확인 CLI는 다음과 같다.

| C:\Users\USER\anaconda3\envs\aip\python.exe scripts\run_experiment.py ` <br> experiments\student_sac_lstm.yaml --dry-run <br> C:\Users\USER\anaconda3\envs\aip\python.exe scripts\run_experiment.py ` <br> experiments\student_sac_lstm.yaml |
| --- |

## 5. Dashboard/Replay 실행 CLI

| 목적 | 명령 | 확인 항목 |
| --- | --- | --- |
| 통합 Training dashboard | python tools\dashboard.py --training-logdir artifacts\dashboard --port 7860 | reward/loss/alpha/replay trend, config |
| 교전 replay 탭 | python tools\dashboard.py --default-tab replay --logdir artifacts\logs\<name>\<tag>\engagement_replays --port 7860 | Blue/Red 궤적, 거리, WEZ, 종료 조건. PyVista 없이 브라우저에서 확인 |
| 호환 wrapper 실행 | python tools\training_dashboard\server.py --logdir artifacts\dashboard --port 7860 | 기존 명령 습관 유지. 내부적으로 통합 서버를 열고 기본 탭만 다르게 선택 |

## 6. 산출물 위치

| artifacts\logs\<output-name>\<output-tag>\training_log.csv <br> artifacts\logs\<output-name>\<output-tag>\policy_probe.csv <br> artifacts\logs\<output-name>\<output-tag>\policy_probe.jsonl <br> artifacts\logs\<output-name>\<output-tag>\engagement_replays\replay_index.csv <br> artifacts\logs\<output-name>\<output-tag>\engagement_replays\iter_000010\episode_00\*_ownship_(F-16)[Blue].csv <br> artifacts\logs\<output-name>\<output-tag>\engagement_replays\iter_000010\episode_00\*_target_(F-16)[Red].csv <br> artifacts\curriculum\<output-name>\<output-tag>\engagement_replays\stage_00_iter_000010\episode_00 |
| --- |

## 7. 육안 점검 체크리스트

| 확인 대상 | 정상 신호 | 주의 신호 |
| --- | --- | --- |
| policy_probe action | probe별 action이 다르고 iteration이 지날수록 변화 | 모든 probe에서 action이 거의 같으면 collapse 가능성 |
| LSTM state norm | state_out_norm이 probe step 사이에 변화 | 계속 None 또는 0이면 recurrent state 전달 경로 확인 |
| engagement replay | ownship/target 궤적이 시간 순서대로 재생 | 초기 위치만 찍히면 steps, env reset, action 출력 확인 |
| training_log loss | actor/critic/alpha가 numeric | 반복적으로 n/a 또는 inf/nan이면 learner metric/debug 확인 |
| Reward=[nan] | 새 episode completion이 없는 iteration이면 가능 | 완료 episode가 있는데 계속 nan이면 env metric 수집 확인 |

## 8. 권장 smoke 순서

1. scripts/run_experiment.py <yaml> --dry-run으로 CLI 변환을 확인한다.

1. ray stop --force로 잔존 Ray node를 정리한다.

1. iterations=2, engagement_log.steps=120으로 짧은 replay smoke를 수행한다.

1. replay_index.csv에 ownship/target CSV 경로가 들어갔는지 확인한다.

1. tools/dashboard.py --default-tab replay --logdir ...\engagement_replays --port 7860으로 Replay 탭에서 재생한다.

1. 문제가 없으면 interval과 steps를 늘려 장기 학습 설정에 반영한다.

## 9. 운영 주의사항

- engagement_log는 학습 batch를 직접 저장하지 않고 별도 평가 env를 실행한다.

- 따라서 replay buffer 샘플 순서, learner sequence batch, prioritized replay 계약에는 영향을 주지 않는다.

- 단, JSBSim 환경을 추가 실행하므로 학습 시간이 늘고 CSV 파일이 누적된다.

- LSTM actor는 replay episode 안에서 state를 유지하고 episode 시작 시 reset한다.

- Unreal 연동 검증은 별도 사용자 수행 항목으로 분리한다.
