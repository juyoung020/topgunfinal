<!--
원본 파일: 참고자료 및 매뉴얼/STUDENT 스크립트 매뉴얼/student_manual_rev1.html
원본 형식: HTML 문서 (스크롤형, svg=1)
변환 방식: BeautifulSoup+markdownify (텍스트·코드·표·SVG 라벨 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# Release/student/ 매뉴얼 — 5 파일 작성·실행 가이드

S

Release/student/

5 파일 작성·실행 매뉴얼

개요

5 파일 한눈에 보기
사전 준비

파일별 가이드

1. my_reward.py
2. my_observation.py
3. my_curriculum.py
4. my_train.py
5. my_submission.py

참고

전체 워크플로
자주 묻는 질문

# Release/student/ 5 파일 작성·실행 매뉴얼

학생이 직접 수정하는 다섯 개의 파일에 대한 작성 계약과 예시, 실행 명령을 정리한다.
본체 학습 루프와 실험 인프라(`train_rllib.py`,
`scripts/run_experiment.py`)는 그대로 두고, 학생은 이 다섯 파일에서
**보상 · 관측 · 커리큘럼 · 실행 설정 · 제출 설정**만 바꾼다.

cwd: DogFightEnv/Release
python 3.11.x
RLlib new API stack
관측 차원 변경 → bundle 호환 끊김

## 5 파일이 환경 / 학습 / 제출과 어떻게 연결되는가

> 🖼️ **[SVG 다이어그램 #1]** — 라벨: student/ | 학생이 수정하는 영역 | my_reward.py | 보상식 — compute_reward() | my_observation.py | 관측 벡터 — build_observation() | my_curriculum.py | 커리큘럼 단계 — get_stages() | my_train.py | 학습 실행 설정 — TRAINING/ENV/RL_CONFIG | my_submission.py | Unreal 서버 제출 클라이언트 | 본체 (Release/) | train_rllib.py | train_curriculum.py | scripts/run_experiment.py | src/dogfight/ | 학습 루프 / Ray / RLlib | checkpoint / bundle 저장 | dashboard / metrics.jsonl | artifacts/models/// | ├ metadata.json | └ policy_weights.pkl.gz | = 제출용 bundle | Unreal 서버 | UDP 9999 · 팀명 / BUNDLE_DIR | 관측 입력 계약은 학습과 동일해야 함 | BUNDLE_DIR

## 0. 사전 준비

cwd · python · 자산 확인

5 파일을 수정·실행하기 전, 반드시 **Release 폴더에서** 실행해야 한다.
DLL, Rule XML, aircraft, engine, scripts 자산이 Release 루트에 있어야 학습/추론이 동작한다.

```
cd DogFightEnv\Release
C:\Users\USER\anaconda3\envs\aip\python.exe -m pip install -r requirements.txt
python -c "import JSBSimWrapper; print('OK')"
```

**실행 위치 고정**
Release 루트에서 실행하지 않으면 `JSBSimAIPLib.dll`, `AIP_BASE*.dll`,
`Rule_forTraining.xml` 등 런타임 자산을 찾지 못한다. `cd DogFightEnv\Release` 이후
`python train_rllib.py` 또는 `python student\my_train.py` 형태로 호출한다.

## 1. my_reward.py

보상 — compute_reward() 반환 계약

에이전트가 무엇을 배울지 결정하는 핵심 파일이다. `MY_REWARD_CONFIG`(dict)와
`compute_reward(...)` 함수만 제공하면 본체가 매 step마다 호출해 reward를 계산한다.
반환값은 `(float total, dict components)` 두 값 튜플이며, `components`의 각 key는
대시보드에서 `ep_reward_<name>` 으로 자동 기록된다.

### 1계약 (Contract)

| 요소 | 타입 | 설명 |
| --- | --- | --- |
| `MY_REWARD_CONFIG` | dict | 보상 가중치/스케일을 dict로 보존. 본체에서 `reward_config`로 전달됨. |
| `compute_reward(...)` | callable | 아래 인자를 받아 `(float, dict)` 반환. |

#### compute_reward 인자

| 인자 | 타입 | 설명 |
| --- | --- | --- |
| `ownship_state` | np.ndarray | `StateIndex.*`로 인덱싱. ROLL, PITCH, YAW, KCAS, ALT, HEALTH 등. |
| `target_state` | np.ndarray | 상대기 상태(같은 인덱싱). |
| `ownship_damage` | float | 아군 누적 피해. |
| `target_damage` | float | 적기 누적 피해. |
| `geo_info` | object | `_get_distance`, `_get_antenna_train_angle`, `_get_aspect_angle` 등 기하 메서드 제공. |
| `wez_config` | dict | WEZ 설정 (range, half_angle 등). |
| `reward_config` | dict | `MY_REWARD_CONFIG`의 런타임 사본. |
| `terminated` / `truncated` | bool | 에피소드 종료 플래그. |
| `end_condition` | str | 종료 사유(crash / altitude / time / fdm 등). |

### 2최소 동작 예시 (그대로 실행 가능)

```
# student/my_reward.py
from __future__ import annotations
from dogfight.sim.state_schema import StateIndex

MY_REWARD_CONFIG = {
    "step_penalty": -0.01,
    "win_reward": 100.0,
    "loss_reward": -100.0,
    "draw_reward": -10.0,
}

def compute_reward(ownship_state, target_state, ownship_damage, target_damage,
                   geo_info, wez_config, reward_config,
                   terminated, truncated, end_condition):
    components = {"step": float(reward_config["step_penalty"])}

    terminal = 0.0
    if terminated or truncated:
        own_hp = float(ownship_state[StateIndex.HEALTH])
        tgt_hp = float(target_state[StateIndex.HEALTH])
        if tgt_hp <= 0.0 < own_hp:
            terminal = float(reward_config["win_reward"])
        elif own_hp <= 0.0 < tgt_hp:
            terminal = float(reward_config["loss_reward"])
        else:
            terminal = float(reward_config["draw_reward"])
    components["terminal"] = terminal

    return float(sum(components.values())), components
```

### 3확장 예시 — 접근 보상 + WEZ 점유 shaping

```
MY_REWARD_CONFIG = {
    "step_penalty": -0.005,
    "win_reward": 150.0,
    "loss_reward": -150.0,
    "draw_reward": -5.0,
    "approach_scale": 0.002,
    "wez_bonus": 0.05,
}

def compute_reward(ownship_state, target_state, ownship_damage, target_damage,
                   geo_info, wez_config, reward_config,
                   terminated, truncated, end_condition):
    components = {"step": float(reward_config["step_penalty"])}

    # 1. 접근 shaping: 가까워질수록 작은 보상
    distance = geo_info._get_distance(ownship_state, target_state)
    components["approach"] = -reward_config["approach_scale"] * float(distance) / 1000.0

    # 2. WEZ 점유 보너스: 정면 진입 시 가산점
    ata = abs(geo_info._get_antenna_train_angle(ownship_state, target_state, False))
    half_angle = float(wez_config.get("half_angle", 30.0))
    wez_range = float(wez_config.get("range", 3000.0))
    in_wez = (ata <= half_angle) and (distance <= wez_range)
    components["wez"] = reward_config["wez_bonus"] if in_wez else 0.0

    # 3. terminal: 기존 win/loss/draw 유지
    terminal = 0.0
    if terminated or truncated:
        own_hp = float(ownship_state[StateIndex.HEALTH])
        tgt_hp = float(target_state[StateIndex.HEALTH])
        if tgt_hp <= 0.0 < own_hp:
            terminal = reward_config["win_reward"]
        elif own_hp <= 0.0 < tgt_hp:
            terminal = reward_config["loss_reward"]
        else:
            terminal = reward_config["draw_reward"]
    components["terminal"] = float(terminal)

    return float(sum(components.values())), components
```

### 4실행 명령

```
python train_rllib.py --algorithm sac --reward-module student.my_reward \
  --output-name team01 --output-tag reward_v1 --iterations 50
```

YAML로 관리하려면 `experiments/student_sac_mlp.yaml`을 팀 파일명으로 복사한 뒤
`env.reward_module: student.my_reward` 주석을 해제하고
`python scripts\run_experiment.py experiments\team01_sac_mlp.yaml --dry-run`으로 먼저 명령을 확인한다.

**components 이름은 분석 도구다**
대시보드와 `training_log.csv`에 `ep_reward_step`,
`ep_reward_wez`처럼 자동 기록된다. 이름을 의미 있게 짓고 같은 키를 실험 간 유지하면 비교가 쉽다.

**스케일 차이가 크면 학습이 흔들린다**
terminal +100과 step shaping 0.5를 섞으면 step shaping이 사라진다. 같은 자리수 안에서 가중치를 잡는다.

#### 제출 전 점검

- `MY_REWARD_CONFIG`가 dict인지
- `compute_reward`가 `(float, dict)`를 반환하는지
- `components`의 합과 `total`이 일치하는지
- terminal에서 win/loss/draw가 모두 다뤄지는지

## 2. my_observation.py

관측 — 정책 입력 벡터 계약

정책 네트워크가 보는 입력 벡터를 직접 정의한다. `OBSERVATION_SIZE`(int)와
`build_observation(...)`만 있으면 동작한다. 본체는 module path를
`--observation-module`로 지정받아 학습/로컬/Unreal 추론에서 같은 함수를 호출한다.

### 1계약

| 요소 | 구분 | 설명 |
| --- | --- | --- |
| `OBSERVATION_SIZE` | 필수 | 벡터 길이(int). 정책 입력 차원과 일치. |
| `build_observation(ownship_state, target_state, geo_info, wez_config=None)` | 필수 | `np.float32` 1-D 벡터 반환. shape는 `(OBSERVATION_SIZE,)`. |
| `OBSERVATION_MODE` | 선택 | 로그/메타데이터용 라벨(예: `"student8"`). |
| `OBSERVATION_LOW` / `OBSERVATION_HIGH` | 선택 | Gym `observation_space`의 범위. 기본 `-1.0 ~ 1.0` 권장. |
| `describe_observation()` | 선택 | 피처 목록과 size 설명을 반환해 metadata.json의 `observation_summary`에 기록. |

### 2최소 동작 예시 — 8차원 정규화 관측

```
# student/my_observation.py
from __future__ import annotations
import numpy as np
from dogfight.envs.observation import normalize
from dogfight.sim.state_schema import StateIndex

OBSERVATION_MODE = "student8"
OBSERVATION_SIZE = 8
OBSERVATION_LOW  = -1.0
OBSERVATION_HIGH =  1.0

def build_observation(ownship_state, target_state, geo_info, wez_config=None):
    distance = geo_info._get_distance(ownship_state, target_state)
    ata = geo_info._get_antenna_train_angle(ownship_state, target_state, False)
    aa  = geo_info._get_aspect_angle(ownship_state, target_state, False)

    obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    obs[0] = normalize(float(ownship_state[StateIndex.ROLL]),  -180.0, 180.0)
    obs[1] = normalize(float(ownship_state[StateIndex.PITCH]),  -90.0,  90.0)
    obs[2] = normalize(float(ownship_state[StateIndex.YAW]),     0.0, 360.0)
    obs[3] = normalize(float(ownship_state[StateIndex.KCAS]),    0.0, 600.0)
    obs[4] = normalize(float(ownship_state[StateIndex.ALT]),     0.0, 15000.0)
    obs[5] = normalize(float(distance), 0.0, 20000.0)
    obs[6] = normalize(float(ata),  -180.0, 180.0)
    obs[7] = normalize(float(aa),   -180.0, 180.0)
    return obs

def describe_observation():
    return {
        "mode": OBSERVATION_MODE, "size": OBSERVATION_SIZE,
        "features": [
            "ownship_roll_norm", "ownship_pitch_norm", "ownship_yaw_norm",
            "ownship_kcas_norm", "ownship_alt_norm",
            "distance_norm", "ata_norm", "aa_norm",
        ],
    }
```

### 3확장 예시 — 상대 속도/고도차를 추가한 10차원

```
OBSERVATION_MODE = "student10_rel"
OBSERVATION_SIZE = 10

def build_observation(ownship_state, target_state, geo_info, wez_config=None):
    distance = geo_info._get_distance(ownship_state, target_state)
    ata = geo_info._get_antenna_train_angle(ownship_state, target_state, False)
    aa  = geo_info._get_aspect_angle(ownship_state, target_state, False)
    own_alt = float(ownship_state[StateIndex.ALT])
    tgt_alt = float(target_state[StateIndex.ALT])
    own_kcas = float(ownship_state[StateIndex.KCAS])
    tgt_kcas = float(target_state[StateIndex.KCAS])

    obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    obs[0] = normalize(float(ownship_state[StateIndex.ROLL]),  -180.0, 180.0)
    obs[1] = normalize(float(ownship_state[StateIndex.PITCH]),  -90.0,  90.0)
    obs[2] = normalize(own_kcas, 0.0, 600.0)
    obs[3] = normalize(own_alt,  0.0, 15000.0)
    obs[4] = normalize(float(distance), 0.0, 20000.0)
    obs[5] = normalize(float(ata), -180.0, 180.0)
    obs[6] = normalize(float(aa),  -180.0, 180.0)
    # 상대 항목
    obs[7] = normalize(own_alt - tgt_alt, -10000.0, 10000.0)
    obs[8] = normalize(own_kcas - tgt_kcas, -400.0, 400.0)
    obs[9] = normalize(float(target_state[StateIndex.HEALTH]) -
                       float(ownship_state[StateIndex.HEALTH]), -1.0, 1.0)
    return obs
```

### 4실행 명령

```
python train_rllib.py --algorithm sac --observation-mode custom \
  --observation-module student.my_observation \
  --output-name team01 --output-tag observation_v1 --iterations 50
```

**차원이 바뀌면 기존 bundle과 호환되지 않는다**
`OBSERVATION_SIZE`나 feature 순서가 바뀌면 policy 입력 차원이 달라진다.
패치된 bundle은 `observation_size`와 `observation_summary`를 저장하지만,
차원이 달라진 weight 자체를 호환시켜 주지는 않는다. 새 tag로 새 실험을 시작한다.

**학습 / 로컬 / Unreal 같은 module path**
다음 4곳에 같은 module path를 기록한다: YAML `env.observation_module`,
train CLI `--observation-module`, 로컬 검증 `--observation-module`,
`my_submission.py`의 `OBSERVATION_MODULE`. 새 bundle의 `metadata.json`에는 `observation_module`, `observation_size`, `observation_summary`가 자동 기록된다.

#### 제출 전 점검

- 반환 vector shape == `OBSERVATION_SIZE`
- `dtype`이 `np.float32`
- 학습 때 쓴 module path가 `my_submission.py`에도 동일하게 들어 있는지
- `artifacts/models/<team>/<tag>/metadata.json`의 `observation_module`과 `observation_size`가 일치하는지

## 3. my_curriculum.py

커리큘럼 — 학습 단계 목록

커리큘럼 학습 시 단계 목록을 정의한다. `get_stages()`가 `CurriculumStage`의
리스트를 반환하면 본체 `train_curriculum.py`가 순서대로 학습하고 stage 간
진급/롤백을 관리한다.

### 1계약

| 요소 | 타입 | 설명 |
| --- | --- | --- |
| `get_stages()` | callable | `list[CurriculumStage]` 반환. 본체가 stage 0부터 순서대로 학습. |
| `CurriculumStage` | dataclass | `from dogfight.ai.curriculum import CurriculumStage`. 주요 인자는 아래 표 참고. |

#### CurriculumStage 주요 필드

| 필드 | 설명 |
| --- | --- |
| `index` / `name` / `description` | 식별과 로그 라벨. |
| `target_mode` | `"fixed"` / `"loiter"` / `"autopilot"` / `"behavior_tree"`. 적기 종류. |
| `episode_step_limit` | 에피소드 최대 step 수. |
| `max_iterations` | 이 단계 최대 학습 iteration. 진급 조건이 비어 있으면 이 수만큼 학습 후 자동 진급. |
| `checkpoint_interval` | 몇 iteration마다 checkpoint 저장할지. |
| `reward_overrides` | 이 단계에서만 덮어쓸 reward_config 키. |
| `randomization` | 초기 배치 랜덤화 dict. radius, r_roll, r_pitch, r_heading 등. |
| `advance_conditions` | `{"win_rate_min": 0.7, "crash_rate_max": 0.3}`처럼 rolling 진급 조건. |
| `advance_window` | rolling window iteration 수. |

### 2최소 동작 예시 — 2단계 워밍업 → BT

```
# student/my_curriculum.py
from __future__ import annotations
from dogfight.ai.curriculum import CurriculumStage

def get_stages() -> list[CurriculumStage]:
    return [
        CurriculumStage(
            index=0, name="student_fixed_target",
            description="Minimal fixed-target warmup stage.",
            target_mode="fixed", episode_step_limit=3600,
            max_iterations=10, checkpoint_interval=5,
            reward_overrides={},
            randomization={"enabled": True,
                           "radius": 500.0,
                           "r_roll": 5.0, "r_pitch": 5.0,
                           "r_heading": 30.0},
            advance_conditions={}, advance_window=5,
        ),
        CurriculumStage(
            index=1, name="student_bt_dogfight",
            description="Minimal behavior-tree opponent stage.",
            target_mode="behavior_tree", episode_step_limit=18000,
            max_iterations=20, checkpoint_interval=5,
            reward_overrides={},
            randomization={"enabled": True,
                           "radius": 1500.0,
                           "r_roll": 10.0, "r_pitch": 8.0,
                           "r_heading": 120.0},
            advance_conditions={}, advance_window=5,
        ),
    ]
```

### 3확장 예시 — 진급 조건과 보상 override

```
def get_stages() -> list[CurriculumStage]:
    return [
        CurriculumStage(
            index=0, name="warmup_fixed",
            description="고정 표적으로 기본 비행 안정화",
            target_mode="fixed", episode_step_limit=3600,
            max_iterations=20, checkpoint_interval=5,
            reward_overrides={"step_penalty": -0.002},
            randomization={"enabled": True, "radius": 800.0,
                           "r_roll": 5.0, "r_pitch": 5.0,
                           "r_heading": 45.0},
            advance_conditions={"crash_rate_max": 0.10},
            advance_window=5,
        ),
        CurriculumStage(
            index=1, name="pursuit_easy_bt",
            description="느린 BT 적기 추격",
            target_mode="behavior_tree", episode_step_limit=9000,
            max_iterations=40, checkpoint_interval=5,
            reward_overrides={"approach_scale": 0.004},
            randomization={"enabled": True, "radius": 1500.0,
                           "r_roll": 10.0, "r_pitch": 8.0,
                           "r_heading": 90.0},
            advance_conditions={"win_rate_min": 0.60,
                                "crash_rate_max": 0.30},
            advance_window=10,
        ),
        CurriculumStage(
            index=2, name="full_dogfight",
            description="전체 dogfight 시나리오",
            target_mode="behavior_tree", episode_step_limit=18000,
            max_iterations=200, checkpoint_interval=10,
            reward_overrides={},
            randomization={"enabled": True, "radius": 2500.0,
                           "r_roll": 15.0, "r_pitch": 10.0,
                           "r_heading": 180.0},
            advance_conditions={"win_rate_min": 0.70},
            advance_window=10,
        ),
    ]
```

### 4실행 명령

```
python train_curriculum.py --algorithm sac \
  --reward-module student.my_reward \
  --stages-module student.my_curriculum \
  --output-name team01 --output-tag curriculum_v1
```

중단된 커리큘럼을 이어 학습하려면 `--resume`을 추가한다. 그러면
`artifacts/dashboard/<run>/curriculum_state.json`의 stage/iteration이 복구된다.

**본편 기본 curriculum은 참고용**
`src/dogfight/ai/curriculum.py`에 0~14단계 + 투서클 헤드온 시퀀스가 들어 있다.
그대로 답안처럼 쓰는 대신, 본인 가설에 맞는 단계와 진급 조건을 직접 설계한다.

## 4. my_train.py

학습 실행 — wrapper · train_rllib.py 호출

학습 루프를 새로 짜지 않는다. `TRAINING_CONFIG / ENV_CONFIG / RL_CONFIG`를 수정한 뒤
`train_rllib.py`를 subprocess로 호출하는 **얇은 wrapper**다. dashboard, record,
bundle 저장 등 인프라는 모두 본체가 담당한다.

### 13개 설정 dict

| dict | 주요 키 | 설명 |
| --- | --- | --- |
| `TRAINING_CONFIG` | `team_name`, `output_tag`, `algorithm`, `iterations`, `reward_module`, `observation_module` | 실험 단위 / 학생 hook 모듈. |
| `ENV_CONFIG` | `observation_mode`, `target_mode`, `target_behavior_dll`, `max_engage_time`, `episode_step_limit` | 환경 조건. `observation_module`이 비어 있으면 `observation_mode`가 사용된다. |
| `RL_CONFIG` | `framework`, `num_env_runners`, `lr`, `gamma`, `train_batch_size`, `minibatch_size` 등 | RLlib 하이퍼파라미터. |

YAML 실행에서는 `runtime.save_lightweight_bundle`,
`runtime.lightweight_bundle_frequency`,
`runtime.save_native_checkpoint`,
`runtime.native_checkpoint_frequency`로 추론용 bundle과 학습 재개용 native checkpoint 저장을 따로 제어한다.
`0` 주기는 최종본만 저장한다는 뜻이며, 오래된 `checkpoint_frequency`는 호환용 alias다.

### 2이어 학습 상황별 실행

| 상황 | 사용 옵션 | 판단 기준 |
| --- | --- | --- |
| 같은 학습을 `checkpoint_final`에서 계속 | `--restore-checkpoint` | policy + optimizer + replay buffer까지 복원. |
| 좋은 정책을 초기 weight로 새 실험 시작 | `--init-bundle` | lightweight bundle의 policy weight만 사용. |
| 중단된 curriculum run의 stage/iteration 재개 | `--resume` | `curriculum_state.json` 기준으로 위치 복구. |

`--restore-checkpoint`와 `--init-bundle`은 동시에 지정하지 않는다.
전자는 학습 상태 복원, 후자는 weight-only 재시작이므로 목적이 다르다.

#### student/my_train.py로 재개 옵션 넘기기

Release판 `student/my_train.py`는 모르는 CLI 옵션을 본체
`train_rllib.py`로 그대로 넘긴다. 그래서 `--help`에 보이지 않는
`--restore-checkpoint`, `--init-bundle`도 dry-run으로 최종 명령을 확인한 뒤 사용할 수 있다.

```
# 1) 먼저 dry-run으로 train_rllib.py에 전달되는 최종 명령 확인
python student\my_train.py --dry-run ^
  --team-name team01 ^
  --output-tag v1_resume ^
  --iterations 50 ^
  --restore-checkpoint artifacts\checkpoints\team01\v1\checkpoint_final

# 2) 문제가 없으면 --dry-run만 제거하고 실제 이어 학습
python student\my_train.py ^
  --team-name team01 ^
  --output-tag v1_resume ^
  --iterations 50 ^
  --restore-checkpoint artifacts\checkpoints\team01\v1\checkpoint_final
```

좋은 bundle weight를 초기값으로 쓰는 새 실험은 다음처럼 실행한다.

```
python student\my_train.py --dry-run ^
  --team-name team01 ^
  --output-tag seed_v2 ^
  --iterations 50 ^
  --init-bundle artifacts\models\team01\v1
```

`checkpoint_final`을 만들고 싶다면 이전 학습에서 native checkpoint 저장 옵션을 켠다.

```
python student\my_train.py --dry-run ^
  --team-name team01 ^
  --output-tag v1 ^
  --iterations 50 ^
  --save-native-checkpoint ^
  --native-checkpoint-frequency 0
```

**curriculum resume는 별도 경로**
`--resume`은 `train_curriculum.py` 전용이다. `student/my_train.py`는
단일 `train_rllib.py` wrapper이므로 curriculum stage/iteration 재개에는 사용하지 않는다.

#### train_rllib.py를 직접 실행하는 경우

```
python train_rllib.py ^
  --algorithm sac ^
  --iterations 50 ^
  --restore-checkpoint artifacts\checkpoints\team01\v1\checkpoint_final ^
  --output-name team01 ^
  --output-tag v1_resume
```

기존 명령에 `--init-bundle`이 있었다면 제거하고
`--restore-checkpoint`만 남긴다. `checkpoint_final`은 이전 학습에서
`--save-native-checkpoint` 또는 YAML의
`runtime.save_native_checkpoint: true`가 켜져 있어야 생성된다.

#### bundle weight로 새 실험 시작하기

```
python train_rllib.py ^
  --algorithm sac ^
  --iterations 50 ^
  --init-bundle artifacts\models\team01\v1 ^
  --output-name team01 ^
  --output-tag seed_v2
```

이 방식은 제출/추론용 bundle을 좋은 초기 정책으로 쓰되 optimizer와 replay buffer는
새로 시작한다. 관측 mode/module과 관측 차원은 bundle 생성 당시 설정과 맞춰야 한다.

#### curriculum 학습 재개하기

```
python train_curriculum.py ^
  --algorithm sac ^
  --output-name team01 ^
  --output-tag curriculum_v1 ^
  --resume
```

같은 curriculum run이 중단된 경우에는 `--resume`을 우선 사용한다.
특정 native checkpoint를 시드로 새 curriculum run을 시작하려면
`--restore-checkpoint artifacts\checkpoints\team01\v1\checkpoint_final`을 지정한다.

#### YAML에서 지정하기

```
# 같은 학습 상태를 이어갈 때
runtime:
  restore_checkpoint: artifacts/checkpoints/team01/v1/checkpoint_final

# policy weight만 초기값으로 쓸 때
runtime:
  init_bundle: artifacts/models/team01/v1

# checkpoint_final을 만들고 싶을 때
runtime:
  save_native_checkpoint: true
  native_checkpoint_frequency: 0
```

### 3최소 동작 예시 — 학생 보상만 사용

```
# student/my_train.py (요약)
TRAINING_CONFIG = {
    "team_name": "team01",
    "output_tag": "v1",
    "algorithm": "sac",
    "iterations": 50,
    "reward_module": "student.my_reward",
    "observation_module": "",
}

ENV_CONFIG = {
    "observation_mode": "tactical16",
    "target_mode": "behavior_tree",
    "target_behavior_dll": "AIP_BASE_target.dll",
    "max_engage_time": 300.0,
    "episode_step_limit": 18000,
}

RL_CONFIG = {
    "framework": "torch",
    "num_env_runners": 1,
    "num_envs_per_env_runner": 1,
    "rollout_fragment_length": "auto",
    "batch_mode": "truncate_episodes",
    "lr": 3e-4, "gamma": 0.99,
    "train_batch_size": 4096,
    "minibatch_size": 256,
}
```

### 4확장 예시 — 학생 보상 + 학생 관측 + PPO

```
TRAINING_CONFIG = {
    "team_name": "team01",
    "output_tag": "obs_ppo_v1",
    "algorithm": "ppo",
    "iterations": 200,
    "reward_module": "student.my_reward",
    "observation_module": "student.my_observation",   # custom obs ON
}
ENV_CONFIG["target_mode"] = "behavior_tree"
ENV_CONFIG["episode_step_limit"] = 18000
RL_CONFIG["train_batch_size"] = 8192
RL_CONFIG["minibatch_size"] = 512
```

### 5실행 명령

```
# 1) dry-run 으로 호출되는 train_rllib.py 명령을 먼저 확인
python student\my_train.py --dry-run

# 2) smoke 실행: 한 iteration만
python student\my_train.py --iterations 1

# 3) 본 학습
python student\my_train.py --team-name team01 --output-tag v2 --iterations 200
```

**dry-run 먼저**
`my_train.py`는 `print()`로 실제 호출 명령을 보여준 뒤
`subprocess.run`으로 `train_rllib.py`를 실행한다. `--dry-run`은
명령만 출력하고 종료하므로 옵션 조합이 의도대로 들어갔는지 빠르게 점검할 수 있다.

**학습 루프를 직접 짜지 않는다**
wrapper 안에서 RLlib을 부르거나, env 생성을 새로 하지 않는다. 그렇게 하면 dashboard, record,
bundle 저장이 끊어진다. 항상 `train_rllib.py`를 통해 호출한다.

## 5. my_submission.py

제출 — Unreal 서버 클라이언트

학습한 모델을 경진대회 Unreal 서버에 연결하는 UDP 클라이언트다. 학습 시 사용한
bundle 경로(`BUNDLE_DIR`)와 관측 mode/module을 그대로 입력하는 것이 가장
중요하다. `MODE`는 `rl`, `bt`, `hybrid` 세 가지.

### 1설정 항목

| 설정 | 의미 | 확인 포인트 |
| --- | --- | --- |
| `TEAM_NAME` | 표시 이름 | 운영 공지의 등록명과 정확히 일치 |
| `SERVER_IP` / `SERVER_PORT` | Unreal 서버 주소 | 운영 공지 기준 |
| `MODE` | `rl` / `bt` / `hybrid` | 실험 의도와 일치 |
| `BUNDLE_DIR` | 제출용 policy 경로 | `metadata.json` + `policy_weights.pkl.gz` 두 파일이 모두 존재해야 함 |
| `OBSERVATION_MODE` / `OBSERVATION_MODULE` | policy 입력 계약 | 학습 metadata의 mode/module/size와 동일해야 함 |
| `BT_DLL` / `BT_RULE_XML` | BT 백엔드 사용 시 행동 트리 | Release 루트에 파일 존재 |
| `HYBRID_MODE`, `RESIDUAL_SCALE`, `ALPHA` | hybrid 세부 옵션 | `residual` / `blend` / `switch` |
| `ACTION_REPEAT` | policy 호출 주기 | 학습 시 step_ratio와 동일하게(기본 6) |

### 2최소 동작 예시 — RL 단일 모드 제출

```
# student/my_submission.py 핵심 수정 부분
TEAM_NAME = "team01"
SERVER_IP = "221.151.77.208"
SERVER_PORT = 9999

MODE = "rl"

BUNDLE_DIR = "artifacts/models/team01/v1"
OBSERVATION_MODE = "tactical16"
OBSERVATION_MODULE = ""   # 기본 관측이면 빈 문자열
```

### 3확장 예시 — custom 관측 + RL/BT 하이브리드

```
TEAM_NAME = "team01"
SERVER_IP = "221.151.77.208"
SERVER_PORT = 9999

MODE = "hybrid"

BUNDLE_DIR = "artifacts/models/team01/observation_v1"
OBSERVATION_MODE = "custom"
OBSERVATION_MODULE = "student.my_observation"

BT_DLL = "AIP_BASE.dll"
BT_RULE_XML = "Rule_team01.xml"

HYBRID_MODE = "residual"   # BT가 베이스, RL은 보정
RESIDUAL_SCALE = 0.35
ALPHA = 0.5

ACTION_REPEAT = 6
```

### 4실행 명령

```
# 방법 A: 파일 수정 후 직접 실행
python student\my_submission.py

# 방법 B: 커맨드라인으로 직접 — RL 모델 사용
python run_unreal_inference.py --mode rl ^
    --bundle-dir artifacts/models/team01/v1 ^
    --team-name team01 ^
    --server-ip <서버IP> --server-port 9999

# 방법 C: RL + BT 하이브리드
python run_unreal_inference.py --mode hybrid ^
    --bundle-dir artifacts/models/team01/v1 ^
    --bt-dll AIP_BASE.dll --bt-rule-xml Rule_team01.xml ^
    --hybrid-mode residual --residual-scale 0.35 ^
    --team-name team01 --server-ip <서버IP>
```

### 5제출 전 로컬 검증

```
python run_local_dogfight.py ^
    --ownship-backend rl ^
    --ownship-bundle-dir artifacts/models/team01/v1 ^
    --target-backend bt --save-log
```

**관측 계약 불일치는 silent failure가 된다**
학습 시 `tactical16`으로 훈련했는데 제출 시 `OBSERVATION_MODULE`이 다른 module을
가리키면 policy 입력 차원이 어긋난다. `metadata.json`의 `obs_mode` /
`observation_module` / `observation_size`와 `my_submission.py`의 두 값을 항상 함께 확인한다.

**BT 모드는 모델이 없어도 동작**
`MODE = "bt"`면 `BUNDLE_DIR`을 보지 않는다. 학습이 늦어졌다면 우선 BT로 접속해
네트워크/팀명을 점검하고, 학습 후 `MODE = "rl"`로 전환한다.

#### 제출 직전 최종 체크리스트

- 실행 위치: `DogFightEnv\Release` 루트인지
- DLL / Rule XML / aircraft / engine / scripts 자산 존재 여부
- `BUNDLE_DIR` 안에 `metadata.json`, `policy_weights.pkl.gz` 둘 다 있는지
- `OBSERVATION_MODE` / `OBSERVATION_MODULE`이 학습 metadata와 같은지
- `TEAM_NAME`이 운영 공지와 일치하는지
- `ACTION_REPEAT`가 학습 시 `step_ratio`와 같은지 (기본 6)

## ★ 전체 워크플로

아이디어 → 실험 → 제출

1. **가설 정의** — 어떤 보상/관측/커리큘럼을 시험할지 한 줄로 적는다.
2. **학생 파일 수정** — 변경 범위를 1개로 좁힌다 (예: `my_reward.py`만).
3. **dry-run** — `python student\my_train.py --dry-run` 또는
   `python scripts\run_experiment.py experiments\student_sac_mlp.yaml --dry-run`으로 호출 명령을 확인.
4. **smoke 1 iteration** — `--iterations 1`로 실행 가능성/관측 shape/보상 반환/bundle 저장을 점검.
5. **본 학습** — 안정화 후 `iterations`와 `train_batch_size`를 키운다.
6. **대시보드 비교** — `artifacts/dashboard/<run>/metrics.jsonl`과 `config.json`을 같이 본다.
7. **로컬 검증** — `run_local_dogfight.py`로 RL vs BT 한 경기를 돌려 실패 원인을 본다.
8. **Unreal 제출** — `my_submission.py` 또는 `run_unreal_inference.py`로 서버에 접속.

## ? 자주 묻는 질문

FAQ

관측 차원을 바꿨는데 기존 bundle을 이어 쓸 수 있나요?

아니요. `OBSERVATION_SIZE`가 바뀌면 policy network 입력 차원이 바뀌어
`--restore-checkpoint` 또는 `--init-bundle`로 이어 학습할 수 없습니다.

같은 모듈 안에서 feature 순서만 살짝 바뀐 경우에도 weight는 호환되지 않습니다.
새 `output-tag`로 처음부터 학습하세요.

단, weight는 정상인데 오래된 bundle metadata에 size만 빠진 경우는 패치된 loader가
`observation_summary.size`, `observation_size`, 또는 custom module의
`OBSERVATION_SIZE`로 차원을 복원합니다.

my_train.py에서 자체적으로 RLlib을 호출해도 되나요?

권장하지 않습니다. wrapper의 핵심은 dashboard, record, bundle/native checkpoint 저장 같은 공통 인프라를
본체 `train_rllib.py`에 위임하는 것입니다. 직접 호출하면 metadata가 비거나,
대시보드에서 보이지 않거나, bundle이 누락될 수 있습니다.

학습이 멈춘 자리에서 이어 학습하려면?

방식이 세 가지로 다릅니다.

`--restore-checkpoint`: policy + optimizer + replay buffer를 모두 복원해
중단된 학습을 그대로 재개합니다. 예:
`--restore-checkpoint artifacts\checkpoints\team01\v1\checkpoint_final`.

`--init-bundle`: policy weight만 시드로 사용하고 optimizer는 새로 시작합니다.
좋은 정책을 시드로 새 실험을 시작할 때 씁니다. 예:
`--init-bundle artifacts\models\team01\v1`.

`--restore-checkpoint`와 `--init-bundle`은 동시에 쓰지 않습니다.

커리큘럼 학습은 같은 run을 이어갈 때 `--resume`으로 stage/iteration을 이어갑니다
(curriculum_state.json 기준). 특정 checkpoint에서 새 curriculum run을 시작할 때는
`--restore-checkpoint`를 사용합니다.

저장 여부와 주기는 YAML의 `save_lightweight_bundle`,
`lightweight_bundle_frequency`, `save_native_checkpoint`,
`native_checkpoint_frequency`에서 따로 조정합니다.

BT만 제출하고 싶은데 my_submission.py를 바꾸지 않아도 되나요?

`MODE = "bt"`로 두고 `BT_DLL` / `BT_RULE_XML`만 팀 파일로 바꾸면 됩니다.
`BUNDLE_DIR`은 BT 모드에서는 사용되지 않습니다.

대시보드에서 어떤 metric부터 봐야 하나요?

승률(`ep_win_rate`)만 보지 말고 `ep_reward_mean`, `ep_crash_rate`,
`ep_min_distance`, `ep_wez_steps`를 함께 봅니다.
"왜 졌는가"는 종료 사유(`end_condition`)를 보면 더 명확합니다.

YAML 템플릿과 my_train.py 중 무엇을 써야 하나요?

둘 다 같은 본체를 호출합니다. **YAML 템플릿**은 실험 조건을 파일로 보존하기 좋고
(`experiments/student_*_template.yaml`), **my_train.py**는 자주 바꾸는 설정을
Python dict로 빠르게 조정할 때 편합니다. 보통 학기 중에는 YAML로 정식 실험을 기록하고,
새 아이디어를 빠르게 돌릴 때만 my_train.py를 씁니다.

AIP 경진대회 매뉴얼 rev5 · Release/student/ 작성 가이드 · 2026-05-14 기준

