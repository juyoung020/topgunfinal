<!--
원본 파일: 2일차 강의 자료/Release_매뉴얼.docx
원본 형식: DOCX (tables=19, images=0)
변환 방식: python-docx (문단·헤딩·코드블록·리스트·표 문서순 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# Release_매뉴얼

DogFightEnv Release 사용자 매뉴얼

학생 배포본 실행, YAML 실험 작성, 혼합 initial_scenario, SAC LSTM 고급 경로 정리
기준일: 2026-05-21 / 기준 경로: DogFightEnv/Release

| 문서 목적 <br> Release 배포본을 기준으로 설치, YAML 실험, 학생 보상/관측 작성, 학습 재개, 로컬 검증, Unreal 제출 전 점검을 한 번에 따라갈 수 있도록 정리한다. |
| --- |

## 1. Release 패키지의 역할

Release는 학생 배포용 실행 패키지이며, 공통 학습 루프와 저장 로직은 본체 스크립트가 담당한다.

학생은 주로 student/ 아래 Python 파일과 experiments/ 아래 YAML 템플릿을 수정한다.

DLL, Rule XML, aircraft/, engine/, scripts/ 자산은 JSBSim/DLL 실행 계약이므로 이름 변경, 이동, 삭제하지 않는다.

| 경로 | 역할 |
| --- | --- |
| train_rllib.py | 단일 PPO/SAC 학습. YAML의 env_config도 --experiment-yaml을 통해 병합한다. |
| scripts/run_experiment.py | YAML을 CLI 인자로 변환하고 원본 YAML 경로를 train_rllib.py로 전달한다. |
| student/my_reward.py | 학생 보상 함수 작성 위치 |
| student/my_observation.py | custom 관측 벡터 작성 위치 |
| student/my_submission.py | Unreal 제출용 bundle/server/team/DLL/XML 설정 |
| student/my_train.py | 선택형 간단 wrapper. 최신 권장 학습 경로는 YAML 실행 |
| experiments/ | 학생용 YAML 템플릿 6개 |
| artifacts/ | 학습 로그, lightweight bundle, dashboard, record 출력 |

## 2. 설치와 실행 준비

```
cd C:\Users\USER\workspace\DogFightEnv\DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe -m pip install -r requirements.txt
C:\Users\USER\anaconda3\envs\aip\python.exe scripts\run_experiment.py experiments\student_sac_mlp.yaml --dry-run
```

학습 전에 --dry-run으로 실제 train_rllib.py 인자가 어떻게 생성되는지 먼저 확인한다.

Ray/RLlib를 직접 초기화하는 검증 전에는 ray stop --force로 잔존 local Ray node를 정리한다.

기본 제출/BT Rule XML은 Rule_forTraining.xml이다. 팀별 Rule을 쓰는 경우 Rule_team01.xml처럼 별도 파일을 두고 --bt-rule-xml 또는 student/my_submission.py의 BT_RULE_XML에서 지정한다.

## 3. YAML 실험 템플릿

| YAML 파일 | 용도 |
| --- | --- |
| student_sac_mlp.yaml | SAC + MLP baseline. 가장 먼저 돌려볼 기본 off-policy 템플릿 |
| student_sac_lstm.yaml | SAC + actor/Q LSTM. RLLibLstm 패치 환경에서 사용하는 고급 템플릿 |
| student_ppo_mlp.yaml | PPO + MLP baseline. replay buffer 없이 on-policy로 학습 |
| student_ppo_lstm.yaml | PPO + LSTM. 기본 RLlib recurrent 경로 사용 |
| student_mixed_initial_sac_mlp.yaml | reset마다 BT/loiter target을 섞는 SAC MLP initial_scenario 예시 |
| student_mixed_initial_sac_lstm.yaml | reset마다 BT/loiter target을 섞는 SAC LSTM initial_scenario 예시 |

| YAML 경로 | 의미 |
| --- | --- |
| output.name / output.tag | 팀 이름과 저장될 모델/로그 버전 이름 |
| env.observation_mode | classic12, relative14, tactical16, legacy37, custom |
| env.observation_module | student.my_observation 같은 custom 관측 module path |
| env.target_mode | fixed, loiter, autopilot, behavior_tree |
| env_config.initial_scenario | reset 시 초기 배치와 target type 분포 설정 |
| env.reward_module | student.my_reward 같은 개인 보상 module path |
| env_config.reward / env_config.wez | 기본 보상 scale과 WEZ 기준 조정 |
| algo.name | sac 또는 ppo |
| algo.mlp / algo.lstm / algo.network | MLP, LSTM, sequence_v1 layer 구조 지정 |
| runtime.init_bundle | lightweight bundle weight에서 새 학습 시작 |
| runtime.restore_checkpoint | RLlib native checkpoint에서 optimizer/replay까지 복원 |
| policy_probe / engagement_log | 학습 중 수치 로그와 짧은 교전 Tacview CSV 저장 |

## 4. 혼합 initial_scenario 사용법

Release도 initial_scenario.mode: ref_old_random을 지원한다. 이 모드는 reset마다 ref old scenario index를 뽑아 behavior tree target과 loiter target을 섞는다.

| 설정 | 계약 |
| --- | --- |
| env.target_mode | 초기값은 behavior_tree로 둔다. BT target DLL을 env 생성 시점에 로드하기 위해 필요하다. |
| env.target_behavior_dll | AIP_BASE_target.dll 또는 사용할 target BT DLL |
| initial_scenario.mode | ref_old_random |
| legacy_scenario_indices | 0..4는 behavior_tree target, 5..7은 loiter target |
| legacy_randomization | 기체 산포, 자세 산포, 공통 N/E/D 산포, loiter bank 범위 지정 |

```
env:
  observation_mode: tactical16
  target_mode: behavior_tree
  target_behavior_dll: AIP_BASE_target.dll

env_config:
  initial_scenario:
    mode: ref_old_random
    legacy_scenario_indices: [0, 1, 2, 3, 4, 5, 6, 7]
    legacy_randomization:
      aircraft_radius_m: 100.0
      loiter_bank_deg_range: [40.0, 70.0]
```

| 판단 근거 <br> run_experiment.py는 YAML 원본을 --experiment-yaml로 넘기고, train_rllib.py는 YAML의 env_config를 실제 환경 설정에 deep merge한다. 따라서 initial_scenario, reward, wez처럼 CLI로 풀지 않는 nested 설정도 학습에 반영된다. |
| --- |

## 5. 학생 작성 파일 계약

| 파일 | 필수 계약 | 주의 |
| --- | --- | --- |
| student/my_reward.py | MY_REWARD_CONFIG, compute_reward(...) | 보상 scale과 종료 조건 영향을 함께 확인 |
| student/my_observation.py | OBSERVATION_SIZE, build_observation(...) | 학습/로컬/Unreal 추론에서 같은 모듈 사용 |
| student/my_submission.py | BUNDLE_DIR, TEAM_NAME, SERVER_IP | 제출 전 bundle 경로와 서버 주소 확인 |

| 판단 기준 <br> reward 평균만 보지 말고 ATA, 거리 접근, ep_min_distance, ep_wez_steps, crash rate, win rate를 함께 확인한다. |
| --- |

## 6. 학습과 학습 재개

```
$PY = "C:\Users\USER\anaconda3\envs\aip\python.exe"
$RUN = "scripts\run_experiment.py"
& $PY $RUN experiments\student_sac_mlp.yaml --dry-run
& $PY $RUN experiments\student_sac_mlp.yaml
```

| 방식 | 이어받는 것 | 용도 |
| --- | --- | --- |
| runtime.restore_checkpoint | RLlib optimizer, replay buffer, learner 상태 | 같은 학습을 계속 진행 |
| runtime.init_bundle | policy weight와 metadata | 제출 bundle을 초기 weight로 새 실험 시작 |
| output.name/tag 변경 | 새 artifacts 하위 경로 | 실험 결과 충돌 방지 |

## 7. SAC LSTM 고급 연구 경로

| 중요 <br> Ray 2.54.0 SAC LSTM은 RLlib 내부 패치가 필요하다. 다른 PC에서는 RLLibLstm/tools/apply_rllib_sac_lstm_patch.py를 먼저 dry-run 후 적용한다. PPO LSTM은 기본 RLlib recurrent 경로를 사용한다. |
| --- |

```
python RLLibLstm\tools\apply_rllib_sac_lstm_patch.py C:\Users\USER\anaconda3\envs\aip --dry-run
python RLLibLstm\tools\apply_rllib_sac_lstm_patch.py C:\Users\USER\anaconda3\envs\aip
```

| 모드 | 구조 | 용도 |
| --- | --- | --- |
| actor_only | actor LSTM + MLP Q | 기존 호환 기본값 |
| actor_critic | actor LSTM + [obs, action] -> Q LSTM -> Q head | Ray 1.9.2 RNNSAC 모사형 target/twin recurrent Q |
| sequence_v1 | actor/Q pre-LSTM MLP, LSTM, post-LSTM MLP를 YAML layer sequence로 지정 | RNNSAC_model.py처럼 네트워크 구조 자유도 확보 |

debug 확인 기준은 seq_lens, STATE_IN/OUT, q_concat_shape=(B,T,obs+action), q_out_shape=(B,T)이다.

긴 학습에서는 algo.lstm.debug_io를 false로 두고 output.tag를 새 실험명으로 분리한다.

## 8. 로그와 교전 확인

| 설정 | 출력 | 용도 |
| --- | --- | --- |
| dashboard.enabled | artifacts/dashboard | 학습 metric JSONL dashboard |
| policy_probe.enabled | policy_probe.csv/jsonl | 고정 입력에 대한 actor action/state 변화 확인 |
| engagement_log.enabled | engagement_replays/*.csv | 학습 중 짧은 교전 Tacview/뷰어 확인 |
| train_rllib.py CSV | artifacts/logs/<name>/<tag>/training_log.csv | reward, win/loss, WEZ, action, learner metric 기록 |

## 9. 출력, 로컬 검증, 제출

```
artifacts/
  logs/<output-name>/<output-tag>/training_log.csv
  models/<output-name>/<output-tag>/metadata.json
  models/<output-name>/<output-tag>/policy_weights.pkl.gz
  records/
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend bt --save-log
```

| run_local_dogfight.py --save-log 출력 | 내용 | 해석 |
| --- | --- | --- |
| ownship_(F-16)[Blue].csv | Time, Longitude, Latitude, Altitude, Roll, Pitch, Yaw, Health | 로컬 교전에서 아군 궤적과 생존 상태를 Replay/Tacview로 복기 |
| target_(F-16)[Red].csv | Time, Longitude, Latitude, Altitude, Roll, Pitch, Yaw, Health | 상대기 궤적과 자세 변화 확인 |
| summary.json | end_condition, outcome, ownship_health, target_health | 승패보다 먼저 종료 사유와 Health를 확인 |

| Tacview 로그 판단 근거 <br> run_local_dogfight.py는 terminated 또는 truncated로 episode loop가 정상 종료된 뒤 env.make_tacviewLog()를 호출한다. 환경은 정상 step 경로에서 매 step ownship/target 로그를 누적하고, make_tacviewLog()에서 두 CSV와 summary JSON을 쓴다. 따라서 정상 종료 교전 결과는 로그로 남지만 provider 예외, KeyboardInterrupt, reset/build 실패처럼 정상 종료 블록에 도달하지 못한 경우까지 항상 보존하는 crash dump 기능은 아니다. |
| --- |

Unreal 제출 전 student/my_submission.py의 BUNDLE_DIR, TEAM_NAME, SERVER_IP를 확인한다. BT 또는 hybrid 제출은 BT_DLL과 BT_RULE_XML도 팀 파일명에 맞춘다.

custom 관측을 사용한 policy는 로컬 검증과 Unreal 추론에서도 같은 observation module을 지정한다.

Release 학습 YAML은 step_ratio: 6을 사용하므로 Unreal 추론의 ACTION_REPEAT 또는 --action-repeat 기본값 6을 유지한다.

```
C:\Users\USER\anaconda3\envs\aip\python.exe run_unreal_inference.py `
  --mode hybrid `
  --bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --bt-dll AIP_BASE.dll `
  --bt-rule-xml Rule_team01.xml `
  --team-name team01 --server-ip <IP> --server-port 9999 `
  --action-repeat 6
```

## 10. Ray/RLlib와 ONNX 확장 구조

현재 기본 학습 경로는 Ray/RLlib가 DogFightWrapper 환경을 감싸는 구조다. Ray/RLlib는 rollout 수집, 학습 루프, checkpoint, lightweight bundle 저장을 담당하고, 환경 자체는 reset()/step()과 observation/action 계약을 제공한다.

| 구분 | 현재 지원 | 확장 가능 지점 |
| --- | --- | --- |
| 학습 프레임워크 | Ray/RLlib PPO/SAC | DogFightWrapper reset()/step()을 직접 호출하는 PyTorch/TensorFlow 학습 루프 |
| 모델 산출물 | metadata.json + policy_weights.pkl.gz lightweight bundle | PyTorch/TensorFlow 모델을 ONNX로 export |
| 추론 연결 | RLActionProvider, BTActionProvider, HybridActionProvider | ONNX Runtime을 ActionProvider.compute_action() 계약으로 감싼 adapter |
| local/Unreal 사용 | run_local_dogfight.py와 run_unreal_inference.py의 RL backend는 RLlib bundle 지원 | ONNX adapter와 CLI 옵션 추가 시 같은 provider 주입 구조로 공통 사용 가능 |

| ONNX 설명 시 주의 <br> 현재 CLI는 ONNX 파일을 바로 받아 실행하지 않는다. 강의에서는 ONNX를 '가능한 확장 구조'로 설명하고, 실제 사용에는 4차원 action [roll, pitch, rudder, throttle]을 반환하는 ActionProvider adapter가 필요하다고 명시한다. |
| --- |

| 판단 근거 <br> local 추론은 ownship/target provider를 환경에 주입하고, Unreal 추론은 provider를 ProviderCommandPolicy에 주입한다. 이 연결 지점은 RLlib bundle, BT DLL, hybrid provider가 이미 공유하는 추상화이므로 ONNX 추론도 같은 adapter 패턴으로 확장하는 것이 가장 작고 안전하다. |
| --- |

## 11. 최종 체크리스트

| 체크 | 확인 내용 |
| --- | --- |
| 환경 | Python 경로와 requirements 설치 확인 |
| 자산 | DLL, XML, aircraft, engine, scripts 위치 유지 |
| YAML | --dry-run으로 실제 CLI 확인 |
| 시나리오 | target_mode와 initial_scenario 계약 확인 |
| 관측 | 학습/검증/제출 observation module 일치 |
| Unreal | Rule_forTraining.xml 또는 팀별 Rule XML, BT DLL, action_repeat=6 확인 |
| 재개 | checkpoint와 bundle 의미 구분 |
| LSTM | RLLibLstm 패치 적용, ray stop --force, debug smoke 통과 |
| 로그 | policy_probe와 engagement_log 출력 위치 확인 |
| Tacview | run_local_dogfight.py --save-log 정상 종료 후 CSV 2개와 summary JSON 확인 |
| ONNX | 현재 직접 실행 기능이 아니라 ActionProvider adapter가 필요한 확장 구조임을 구분 |
| 제출 | bundle 경로와 서버 설정 확인 |

## 12. CLI 빠른 참조

```
cd C:\Users\USER\workspace\DogFightEnv\DogFightEnv\Release
$PY = "C:\Users\USER\anaconda3\envs\aip\python.exe"
$RUN = "scripts\run_experiment.py" 
```

| 케이스 | 명령 |
| --- | --- |
| SAC MLP baseline | & $PY $RUN experiments/student_sac_mlp.yaml --dry-run <br> & $PY $RUN experiments/student_sac_mlp.yaml |
| SAC LSTM | ray stop --force <br> & $PY $RUN experiments/student_sac_lstm.yaml --dry-run <br> & $PY $RUN experiments/student_sac_lstm.yaml |
| PPO MLP baseline | & $PY $RUN experiments/student_ppo_mlp.yaml --dry-run <br> & $PY $RUN experiments/student_ppo_mlp.yaml |
| PPO LSTM | & $PY $RUN experiments/student_ppo_lstm.yaml --dry-run <br> & $PY $RUN experiments/student_ppo_lstm.yaml |
| 혼합 initial SAC MLP | & $PY $RUN experiments/student_mixed_initial_sac_mlp.yaml --dry-run <br> & $PY $RUN experiments/student_mixed_initial_sac_mlp.yaml |
| 혼합 initial SAC LSTM | ray stop --force <br> & $PY $RUN experiments/student_mixed_initial_sac_lstm.yaml --dry-run <br> & $PY $RUN experiments/student_mixed_initial_sac_lstm.yaml |

실제 학습 전에는 항상 --dry-run으로 생성되는 CLI와 output.tag를 먼저 확인한다.

SAC LSTM 학습 전에는 RLLibLstm 패치 적용 여부를 확인하고, Ray 잔존 node가 있으면 ray stop --force를 먼저 실행한다.
