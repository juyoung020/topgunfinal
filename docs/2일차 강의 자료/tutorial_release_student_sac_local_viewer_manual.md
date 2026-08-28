<!--
원본 파일: 2일차 강의 자료/tutorial_release_student_sac_local_viewer_manual.html
원본 형식: HTML 문서 (스크롤형, svg=1)
변환 방식: BeautifulSoup+markdownify (텍스트·코드·표·SVG 라벨 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# Release SAC MLP 100iter 학습 - 로컬 교전 로그 뷰어 매뉴얼

DogFightEnv · **Release SAC MLP 매뉴얼** · 학습 → 교전 → 로그 뷰어

원본 내용 유지 · 스타일/목차 형식 적용 · 2026-05-22

#### 목차

1. 한눈에 보는 흐름
2. 실행 준비
3. YAML 100iter 설정
4. 학습 실행
5. 로컬 교전 로그 생성
6. 로그 뷰어 사용
7. 확인 포인트

DogFightEnv Release Student Manual

# SAC MLP 100iter 학습부터 로컬 교전 로그 뷰어까지

`Release/experiments/student_sac_mlp.yaml`을 이용해 간단한 학습 모델을 만들고,
`run_local_dogfight.py`로 `AIP_BASE_target.dll` 상대 교전 로그를 저장한 뒤,
웹 로그 뷰어에서 결과를 복기하는 학생용 실습 절차입니다.

## 00 한눈에 보는 흐름

1**실행 준비**Release 폴더에서 Python 환경 확인

2**YAML 설정**`runtime.iterations`를 100으로 설정

3**학습 실행**`run_experiment.py`로 SAC MLP 학습

4**로컬 교전**학습 bundle로 `AIP_BASE_target.dll`과 교전

5**로그 확인**웹 Replay 탭에서 CSV 로그 확인

> 🖼️ **[SVG 다이어그램 #1]** — 라벨: student_sac_mlp.yaml | iterations, output tag | run_experiment.py | train_rllib.py 호출 | model bundle | metadata + weights | run_local_dogfight.py | AIP_BASE_target.dll | logs/*.csv + summary.json Web Replay Viewer | logs/*.csv + summary.json | Web Replay Viewer

**판단 근거:**
학생에게는 “학습 설정 파일 → 모델 bundle → 로컬 교전 → replay 확인”의 산출물 흐름이 가장 중요합니다.
그래서 내부 RLlib 세부 구조보다 파일 위치와 CLI 계약을 먼저 보이도록 구성했습니다.

## 01 실행 준비

권장 Python은 프로젝트 기준 conda 환경입니다. `conda activate aip` 후 모든 명령은 `Release` 폴더에서 실행합니다.

```
python -m pip install -r requirements.txt
```

**주의:**
`*.dll`, `Rule.xml`, `Rule_forTraining.xml`, `aircraft/`, `engine/` 폴더는 런타임 계약에 포함됩니다.
실습 중 이름을 바꾸거나 이동하지 않습니다.

Ray가 이전 학습에서 남아 있으면 시작 전에 정리합니다. 이미 깨끗한 상태라면 건너뛰어도 됩니다.

```
python -m ray stop --force
```

| 항목 | 확인할 위치 |
| --- | --- |
| YAML 템플릿 | `experiments\student_sac_mlp.yaml` |
| YAML 실행기 | `scripts\run_experiment.py` |
| 로컬 교전 실행기 | `run_local_dogfight.py` |
| 웹 로그 뷰어 | `tools\dashboard.py` 또는 `tools\web_log_viewer.py` |

**파일명 메모:**
현재 배포본의 실행기는 `run_experiment.py`입니다. `run_experiments.py`처럼 복수형 파일은 없습니다.

## 02 YAML을 100 iteration 실습용으로 설정

`run_experiment.py`는 YAML의 `runtime.iterations` 값을 그대로 읽습니다.
명령줄에서 iteration만 덮어쓰는 옵션은 없으므로, 실습용 복사본을 만들어 수정하는 방식을 권장합니다.

```
Copy-Item experiments\student_sac_mlp.yaml experiments\team01_sac_mlp_100it.yaml
```

복사한 YAML에서 아래 항목을 수정합니다.

```
output:
  name: team01
  tag: sac_mlp_100it

runtime:
  iterations: 100
```

### 학습 상대 모드 선택

| 선택 | YAML 설정 | 수업에서의 의미 |
| --- | --- | --- |
| 기본 빠른 실습 | `env.target_mode: fixed` | 고정 표적을 상대로 기초 조종/추종을 빠르게 확인합니다. |
| DLL 상대 학습 | `env.target_mode: behavior_tree` + `target_behavior_dll: AIP_BASE_target.dll` | 학습 중에도 AIP target DLL이 움직이는 상대가 됩니다. 실행 비용과 난도가 올라갑니다. |

**판단 근거:**
`student_sac_mlp.yaml`의 기본 target mode는 `fixed`입니다.
따라서 이 매뉴얼의 기본 흐름은 “짧은 fixed 학습 후, 로컬 교전에서 `AIP_BASE_target.dll` 상대 평가”로 설명합니다.
학습부터 DLL 상대를 쓰려면 `target_mode`를 `behavior_tree`로 바꿔야 계약이 명확합니다.

## 03 학습 실행

먼저 dry-run으로 YAML이 어떤 `train_rllib.py` 명령으로 변환되는지 확인합니다.

```
python scripts\run_experiment.py experiments\team01_sac_mlp_100it.yaml --dry-run
```

문제가 없으면 실제 학습을 시작합니다. 100 iteration은 PC 성능과 Ray 초기화 상태에 따라 시간이 걸릴 수 있습니다.

```
python scripts\run_experiment.py experiments\team01_sac_mlp_100it.yaml
```

### 생성되는 주요 산출물

| 산출물 | 기본 경로 예시 | 용도 |
| --- | --- | --- |
| 모델 bundle | `artifacts\models\team01\sac_mlp_100it` | `run_local_dogfight.py --ownship-bundle-dir`에 넣는 추론 모델 |
| 학습 로그 CSV | `artifacts\logs\team01\sac_mlp_100it\training_log.csv` | iteration별 reward, 거리, WEZ, 승패 등 확인 |
| 대시보드 로그 | `artifacts\dashboard\team01_sac_mlp_100it\metrics.jsonl` | 웹 Training 탭 차트 표시 |
| 실험 기록 | `artifacts\records\team01\sac_mlp_100it` | YAML, reward/observation/config 스냅샷 보관 |

**수업 팁:**
reward 평균만 보지 말고 `ATA`, 거리 접근, `ep_min_distance`, `ep_wez_steps`, crash rate, win rate를 함께 확인하도록 안내합니다.

## 04 학습 모델로 AIP_BASE_target.dll 상대 로컬 교전

학습이 끝나면 ownship은 RL bundle, target은 BT DLL backend로 실행합니다.
`--save-log`를 켜야 기본 저장 위치인 `artifacts\logs` 아래에 replay용 CSV가 남습니다.

```
python run_local_dogfight.py `
  --ownship-backend rl `
  --ownship-bundle-dir artifacts\models\team01\sac_mlp_100it `
  --target-backend bt `
  --target-bt-dll AIP_BASE_target.dll `
  --observation-mode tactical16 `
  --max-engage-time 120 `
  --episode-step-limit 7200 `
  --save-log
```

정상 종료되면 터미널에는 종료 조건, 양측 health, total reward가 출력됩니다.

```
simulation finished
end_condition: ...
terminated: True truncated: False
total_reward: ...
ownship_health: ...
target_health: ...
tacview log saved
```

### 로그 파일 이름

`artifacts\logs` 아래에 같은 timestamp를 가진 3개 파일이 생성됩니다.

```
artifacts\logs\
  2026_5_22_10_30_12_ownship_(F-16)[Blue].csv
  2026_5_22_10_30_12_target_(F-16)[Red].csv
  2026_5_22_10_30_12_summary.json
```

**저장 범위:**
`--save-log`는 정상 episode 종료 후 저장됩니다.
reset 실패, provider 예외, 강제 중단처럼 종료 블록에 도달하지 못한 경우까지 항상 보존하는 crash dump 기능은 아닙니다.

## 05 tools 로그 뷰어 사용

통합 대시보드의 Replay 탭을 바로 열려면 다음 명령을 사용합니다.

```
python tools\dashboard.py `
  --default-tab replay `
  --logdir <log path> `
  --port 7860
```

브라우저에서 아래 주소를 엽니다.

```
http://127.0.0.1:7860/?tab=replay
```

Replay 전용 호환 실행기를 사용해도 됩니다. 기본 포트는 7870입니다.

```
python tools\web_log_viewer.py --logdir <log path> --port 7870
```

```
http://127.0.0.1:7870
```

![DogFightEnv web log viewer replay render screenshot](260519_2043_web_log_viewer_render.png)

그림 1. 웹 로그 뷰어 렌더 예시. 실제 실습에서는 `run_local_dogfight.py --save-log`로 생성한 최신 CSV 쌍을 선택해 재생합니다.

### 뷰어에서 확인할 항목

**궤적**  
Blue ownship과 Red target의 상대 위치, 접근/이탈 방향을 확인합니다.

**HUD 지표**  
거리, health, end condition, 시간 진행을 확인합니다.

**WEZ**  
표적이 유효 교전 구역 안에 들어오는지 봅니다.

**카메라**  
orbit view로 회전하면서 기동 형태를 복기합니다.

**판단 근거:**
학생 실습에서는 Tacview CSV를 외부 도구로 옮기는 것보다, 배포본에 포함된 웹 뷰어로 바로 확인하는 흐름이 재현성이 높습니다.
`tools/dashboard.py`는 Training 탭과 Replay 탭을 함께 제공하므로 학습 지표와 교전 결과를 한 서버에서 연결해 설명할 수 있습니다.

## 06 확인 포인트와 자주 생기는 실수

| 상황 | 확인 방법 |
| --- | --- |
| 100 iteration으로 실행되지 않음 | `--dry-run` 출력의 `--iterations` 값을 확인합니다. YAML의 `runtime.iterations`가 100이어야 합니다. |
| 모델 경로를 못 찾음 | `artifacts\models\\`가 실제 존재하는지 확인합니다. |
| DLL 상대가 아닌 것 같음 | 로컬 교전 명령에 `--target-backend bt --target-bt-dll AIP_BASE_target.dll`이 들어갔는지 확인합니다. |
| 로그 뷰어 목록이 비어 있음 | `--logdir <log path>`가 교전 로그 폴더를 가리키는지, ownship/target CSV 쌍이 같은 timestamp로 있는지 확인합니다. |
| 브라우저가 열리지 않음 | 터미널에 표시된 포트와 주소를 확인하고, 다른 서버가 같은 포트를 쓰면 `--port 7871`처럼 바꿉니다. |

### 최소 검증 명령

```
python -m py_compile `
  scripts\run_experiment.py `
  run_local_dogfight.py `
  tools\dashboard.py `
  tools\web_log_viewer.py

python scripts\run_experiment.py experiments\team01_sac_mlp_100it.yaml --dry-run
```

**판단 근거:**
긴 Ray 학습을 매뉴얼 작성자가 대신 실행해 “통과”라고 주장하는 것은 재현성과 맞지 않습니다.
수업 전에는 위 dry-run과 짧은 1-2 iteration smoke를 먼저 확인하고, 실제 100 iteration은 학생 PC 또는 강의용 PC에서 수행하는 절차로 두는 것이 안전합니다.

작성 기준: 2026-05-22, DogFightEnv Release 배포본 기준. 분석 메모:
`LogDevelop/260522_0103_release_student_sac_local_viewer_manual_analysis.md`

