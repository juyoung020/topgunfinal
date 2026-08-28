<!--
원본 파일: 참고자료 및 매뉴얼/교전 대시보드 매뉴얼/engagement_log_dashboard_guide.html
원본 형식: HTML 문서 (스크롤형, svg=0)
변환 방식: BeautifulSoup+markdownify (텍스트·코드·표·SVG 라벨 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# Engagement Log & Dashboard Guide

LOG

Engagement Log

CSV Replay / Dashboard

Guide

개요
YAML 설정
YAML 케이스
--save-log 케이스
출력 경로
대시보드 연결
점검 목록

# Engagement Log와 Dashboard 연결 가이드

학습 중 교전 replay CSV를 남기는 `engagement_log` 설정,
로컬 교전 검증용 `--save-log`, 그리고 통합 대시보드의
`Training`/`Replay` 탭 연결 방법을 한 번에 정리합니다.

experiments/*.yaml
run_local_dogfight.py --save-log
tools/dashboard.py

## 1. YAML에서 engagement_log 켜기

학습 중 CSV replay 생성

사용자가 말하는 engage log는 실험 YAML의 `engagement_log` 섹션입니다.
`scripts/run_experiment.py`가 이 섹션을 읽어
`train_rllib.py`의 `--engagement-log-*` 옵션으로 변환합니다.

### 1기본 설정 블록

```
dashboard:
  enabled: true
  logdir: artifacts/dashboard

engagement_log:
  enabled: true
  interval: 10
  steps: 600
  episodes: 1
  print: true
```

| 키 | 의미 | 권장 사용 |
| --- | --- | --- |
| `dashboard.enabled` | 학습 지표를 `metrics.jsonl`로 남길지 결정 | 대시보드 Training 탭을 볼 계획이면 `true` |
| `dashboard.logdir` | 대시보드 지표 루트 | 기본값은 `artifacts/dashboard` |
| `engagement_log.enabled` | 학습 중 별도 평가 교전을 실행해 Tacview CSV 쌍 저장 | Replay 탭으로 정책 궤적을 보고 싶으면 `true` |
| `interval` | N iteration마다 replay 저장 | 짧은 실험은 1~5, 긴 실험은 10~50 |
| `steps` | replay episode당 최대 step 수 | 빠른 확인은 120~300, 궤적 확인은 600 이상 |
| `episodes` | 저장 시점마다 몇 개 episode를 남길지 | 일반적으로 1, 분산 확인은 2~3 |
| `print` | 콘솔에 replay 요약 출력 | 로그가 많으면 `false` |

**판단 근거**
`engagement_log`는 RLlib 학습 EnvRunner와 별도로 짧은 평가 환경을 만들어
현재 actor의 교전 궤적을 저장합니다. replay buffer나 learner batch에는 직접 영향을 주지 않지만,
추가 시뮬레이션을 돌리므로 너무 촘촘하게 켜면 학습 시간이 늘어납니다.

## 2. YAML 케이스별 예시

실험 목적별 설정

### 1빠른 smoke: 매 iteration, 짧게 저장

```
engagement_log:
  enabled: true
  interval: 1
  steps: 120
  episodes: 1
  print: true
```

### 2기본 학습 모니터링: 10 iteration마다 저장

```
engagement_log:
  enabled: true
  interval: 10
  steps: 600
  episodes: 1
  print: true
```

### 3긴 학습: 저장 빈도를 낮추고 조용히 기록

```
engagement_log:
  enabled: true
  interval: 50
  steps: 900
  episodes: 1
  print: false
```

### 4분산 확인: 저장 시점마다 여러 episode

```
engagement_log:
  enabled: true
  interval: 20
  steps: 600
  episodes: 3
  print: true
```

### 5Replay 저장 끄기

```
engagement_log:
  enabled: false
```

### 6YAML 실행 전 dry-run으로 옵션 변환 확인

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe scripts\run_experiment.py `
  experiments\student_sac_mlp.yaml `
  --dry-run
```

**dry-run에서 확인할 것**
출력 argv에 `--engagement-log-interval`,
`--engagement-log-steps`, `--engagement-log-episodes`,
`--dashboard-logdir`가 원하는 값으로 들어갔는지 확인합니다.

## 3. --save-log 로컬 CSV 생성 케이스

학습 후 단일 교전 복기

`--save-log`는 `run_local_dogfight.py`가 episode를 정상적으로
끝낸 뒤 `env.make_tacviewLog()`를 호출해 ownship CSV, target CSV,
summary JSON을 저장하는 옵션입니다. 기본 저장 위치는 환경 설정의
`artifacts_dir`이며 Release 기본값은 `artifacts/logs`입니다.

### 1학습한 RL ownship vs BT target

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend bt `
  --target-bt-dll AIP_BASE_target.dll `
  --save-log
```

### 2BT vs BT: DLL/Rule XML 단독 확인

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend bt `
  --ownship-bt-dll AIP_BASE.dll `
  --target-backend bt `
  --target-bt-dll AIP_BASE_target.dll `
  --bt-rule-xml Rule_forTraining.xml `
  --save-log
```

### 3RL vs fixed: 정책 기본 조종 확인

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend fixed `
  --max-engage-time 120 `
  --save-log
```

### 4Hybrid vs BT: residual/blend/switch 확인

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend hybrid `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend bt `
  --hybrid-mode residual `
  --residual-scale 0.35 `
  --save-log
```

### 5custom observation bundle 검증

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend bt `
  --observation-mode custom `
  --observation-module student.my_observation `
  --save-log
```

### 6RL vs RL: 두 bundle 비교

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_v1 `
  --target-backend rl `
  --target-bundle-dir artifacts\models\team01\ppo_mlp_v1 `
  --save-log
```

**주의**
`--save-log`는 정상 episode loop가 끝난 뒤 로그를 씁니다.
DLL access violation, provider build 실패, 강제 종료처럼 `finally` 정리 전에
프로세스가 죽는 경우에는 마지막 CSV가 생성되지 않을 수 있습니다.

## 4. 로그 출력 경로

어디에 무엇이 생기는가

| 생성 방식 | 주요 파일 | 용도 |
| --- | --- | --- |
| 학습 기본 CSV | `artifacts/logs/<output-name>/<output-tag>/training_log.csv` | iteration별 reward, custom metric, learner metric 확인 |
| 대시보드 지표 | `artifacts/dashboard/<output-name>_<output-tag>/metrics.jsonl` | 통합 대시보드 `Training` 탭에서 읽는 지표 |
| 학습 중 engagement replay | `artifacts/logs/<output-name>/<output-tag>/engagement_replays/` | iteration별 짧은 평가 교전 CSV replay |
| engagement replay index | `replay_index.csv`, `replay_index.jsonl` | iteration, episode, reward, end_condition, CSV 경로 요약 |
| 로컬 `--save-log` | `artifacts/logs/*_ownship_(F-16)[Blue].csv` `artifacts/logs/*_target_(F-16)[Red].csv` `artifacts/logs/*_summary.json` | 단일 로컬 교전 복기 |

```
artifacts/
├── dashboard/
│   └── team01_sac_mlp_v1/
│       ├── metrics.jsonl
│       └── config.json
└── logs/
    └── team01/
        └── sac_mlp_v1/
            ├── training_log.csv
            ├── policy_probe.csv
            └── engagement_replays/
                ├── replay_index.csv
                ├── replay_index.jsonl
                └── iter_000010/
                    └── episode_00/
                        ├── *_ownship_(F-16)[Blue].csv
                        ├── *_target_(F-16)[Red].csv
                        └── *_summary.json
```

## 5. 대시보드 로그 뷰어 연결

Training + Replay

### 1학습 지표와 replay를 함께 보기

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py `
  --training-logdir artifacts\dashboard `
  --logdir artifacts\logs\team01\sac_mlp_v1\engagement_replays `
  --default-tab replay `
  --port 7860
```

브라우저에서 `http://127.0.0.1:7860`을 열고 상단 탭을 전환합니다.

### 2로컬 --save-log 결과만 보기

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py `
  --logdir artifacts\logs `
  --default-tab replay `
  --port 7860
```

### 3Training 탭을 기본으로 열기

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py `
  --training-logdir artifacts\dashboard `
  --logdir artifacts\logs `
  --default-tab training `
  --port 7860
```

### 4포트 충돌 시 다른 포트 사용

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py `
  --training-logdir artifacts\dashboard `
  --logdir artifacts\logs `
  --default-tab replay `
  --port 7861
```

**탭별 입력**
`Training` 탭은 `metrics.jsonl`을 읽고,
`Replay` 탭은 Blue/Red CSV 쌍을 찾습니다. 학습 중 저장한 replay는
`engagement_replays` 폴더를, 로컬 `--save-log`는
`artifacts/logs` 폴더를 `--logdir`로 지정하면 됩니다.

## 6. 점검 목록

로그가 안 보일 때

#### YAML / 학습

- `engagement_log.enabled: true`인지 확인한다.
- `interval`이 전체 iteration보다 너무 크지 않은지 확인한다.
- `scripts/run_experiment.py ... --dry-run`에서 engagement 옵션이 생성되는지 확인한다.
- `dashboard.enabled: true`이고 `dashboard.logdir`가 대시보드 실행 경로와 같은지 확인한다.

#### CSV / Replay

- Blue ownship CSV와 Red target CSV가 같은 폴더에 쌍으로 있는지 확인한다.
- `--logdir`가 CSV 파일이 들어 있는 상위 폴더를 가리키는지 확인한다.
- 학습 engagement replay는 `engagement_replays`를, 로컬 로그는 `artifacts/logs`를 우선 확인한다.
- episode가 정상 종료되지 않고 프로세스가 죽은 경우 `--save-log` CSV가 없을 수 있다.

Q. dashboard.enabled와 engagement_log.enabled는 같은 기능인가?

아닙니다. `dashboard.enabled`는 학습 scalar 지표를 `metrics.jsonl`로 남기는 설정이고,
`engagement_log.enabled`는 별도 평가 교전을 돌려 Replay용 CSV를 저장하는 설정입니다.

Q. --save-log와 engagement_log는 언제 구분해서 쓰나?

`engagement_log`는 학습 중 주기적으로 정책 궤적을 저장할 때 사용합니다.
`--save-log`는 학습이 끝난 bundle을 로컬에서 한 번 붙여 보고, 그 단일 episode를 복기할 때 사용합니다.

Q. replay가 대시보드에 안 뜨면 무엇부터 보나?

먼저 `--logdir` 아래에 `*_ownship_(F-16)[Blue].csv`와
`*_target_(F-16)[Red].csv`가 있는지 확인합니다. 그 다음 포트 주소
`http://127.0.0.1:7860/?tab=replay`를 직접 열어 봅니다.

