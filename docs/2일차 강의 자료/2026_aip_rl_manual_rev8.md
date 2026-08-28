<!--
원본 파일: 2일차 강의 자료/2026_aip_rl_manual_rev8.html
원본 형식: HTML 슬라이드 덱 (slides=35, svg=2)
변환 방식: BeautifulSoup+markdownify (텍스트·코드·표·SVG 라벨 무손실 추출)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# 2026 AI Pilot Top Gun Challenge · 학생 매뉴얼 (rev7 개선판)

---

## Slide 1 — 2026 AI Pilot Top Gun Challenge 학생 매뉴얼

DogFightEnv Release · Student Manual

나만의 AI Pilot을 만드는 워크플로 — 보상·관측·커리큘럼 설계부터  
학습·로컬 검증·Unreal 제출까지 단대단 안내.

PPO / SAC
YAML 실험
RL vs BT
Tacview Replay
Unreal 제출

**버전** rev7-improved (HTML 슬라이드판) · **기준** DogFightEnv Release · **날짜** 2026-05-21  
**키보드** ← → 이동, Space 다음, Home/End 처음·끝

> 🖼️ **[SVG 다이어그램 #2]** — 라벨: LOS | Ownship (RL) | Target (BT)

---

## Slide 2 — 이 매뉴얼이 전달하려는 것

01 · 접근법

RLlib 기반 실험 공통 플랫폼 사용 가이드. **학생은 보상·관측·커리큘럼·YAML 조건을 자유롭게 설계**하고, 공통 코드는 **실행 계약과 기록 방식**을 제공합니다. 아이디어는 작게 돌리고, 로그로 읽고, 다음 가설로 잇습니다.

### 실행 위치 · 런타임 자산

모든 명령은 `Release/`에서 실행. DLL · Rule XML · aircraft · engine · scripts는 **이름 변경·이동 금지**.

### 관측 mode / module 일치

학습 · 로컬 검증 · 제출 추론에서 같은 `observation_mode`와 `observation_module`을 사용해야 차원이 맞습니다.

### bundle ↔ 관측 차원 호환

`artifacts/models/<team>/<tag>/metadata.json`의 `obs_mode`가 추론 환경과 같아야 합니다.

**한 줄 원칙:** 작게 돌리고 · 기록되게 두고 · 로그로 읽는다. 이 매뉴얼의 모든 단계는 이 세 가지를 반복하는 방식으로 구성되어 있습니다.

---

## Slide 3 — 좋은 실험은 작은 루프 입니다

01 · 접근법

가설 1개, 조건 1개만 바꾸기. 짧게 돌리고, 로그를 비교하고, 다음 가설로 잇기.

1**가설**한 가지 질문

2**YAML 기록**조건 보존

3**짧은 학습**smoke 우선

4**로그 확인**지표·궤적

5**수정**다음 가설로

### 작게

- 가설 1개에 조건 1개만 변경
- iterations는 처음엔 1–10 smoke
- 여러 변수를 동시에 건드리지 않기

### 기록되게

- YAML로 조건 보존 (`experiments/*.yaml`)
- `output.name` + `tag`로 폴더 분리
- `config.json`도 자동 함께 저장

### 읽히게

- dashboard에서 여러 run 동시 비교
- metric은 reward 외에 4–5종 함께
- 의심스러우면 Replay 탭에서 궤적 직접 확인

---

## Slide 4 — 관찰 가능한 지표는 결과의 이유 를 읽습니다

01 · 접근법

승률 하나로 판단하지 않습니다. "왜 그렇게 됐는지"를 metric으로 같이 봅니다.

### reward_mean

에피소드 평균 reward. 추세로 학습 안정성 확인.

우선순위 가장 기본. 단독으로는 부족.

### crash_rate

추락 발생률. 보상 과격도와 함께 봄.

주의 0.05 이상이면 보상·안전 페널티 재검토.

### ep_min_distance

에피소드 내 최소 접근 거리. 접근/회피 행동 진단.

의미 줄어들면 추격, 늘면 회피 학습.

### ep_wez_steps

WEZ 안에서 머문 step. 교전 점유 시간.

목표 점진 증가가 추격형 정책의 신호.

### win_rate

승률. 최종 평가지표.

함정 reward는 같은데 win이 낮은 경우 있음 (reward shaping ↔ outcome 분리).

### 해석 팁

같은 reward에도 행동 양상은 다양합니다. 다섯 지표를 묶어 **"무엇이 잘 됐고, 무엇이 안 됐는가"**를 한 그림으로 그립니다.

---

## Slide 5

02

환경 준비

Release 폴더 구조 이해 → Python 환경 설치 → 의존성 + smoke 검증 →
런타임 자산 점검 → 실패 원인 대응. 학습 코드를 만지기 전 반드시 통과해야 하는 단계입니다.

---

## Slide 6 — Release 폴더를 루트로 사용 합니다

02 · 환경 준비

수정 중심 / 공통 플랫폼 / 런타임 자산을 명확히 구분하세요.

### 폴더 구조

Release/
├── src/dogfight/ # 공통 플랫폼 — 수정 지양
├── student/ # 학생 작성 템플릿
│ ├── my_reward.py
│ ├── my_observation.py
│ ├── my_curriculum.py
│ ├── my_train.py
│ └── my_submission.py
├── experiments/ # YAML 실험 템플릿
├── train_rllib.py # 단일 학습 본체
├── train_curriculum.py # 커리큘럼 학습 본체
├── run_local_dogfight.py
├── run_unreal_inference.py
└── DLL · Rule XML · aircraft/ · engine/ · scripts/ # 런타임 자산

### 수정 중심 영역

- `student/` 학생 파일
- `experiments/*.yaml`

### 공통 플랫폼

- `src/dogfight/` 실행 계약
- 기본적으로 직접 수정하지 않음

### 런타임 자산

- DLL · XML · aircraft · engine · scripts
- **이름 변경 · 이동 금지**

---

## Slide 7 — 가상환경 → 의존성 → smoke 순서로

02 · 환경 준비

학습보다 **import와 dry-run 확인**이 먼저입니다. Ray/Torch 문제는 가상환경과 버전 충돌부터 보세요.

### STEP 1 · Anaconda 가상환경 생성

```
conda create -n aip python=3.11
conda activate aip
```

### STEP 2 · 의존성 설치

```
cd DogFightEnv\Release
python -m pip install -r requirements.txt
```

### STEP 3 · import smoke

```
python -c "import JSBSimWrapper; print('OK')"
```

### STEP 4 · dry-run으로 첫 학습 명령 점검

```
python scripts\run_experiment.py experiments\student_sac_mlp.yaml --dry-run
```

### Anaconda 설치 시 주의

- Python 3.11.x 권장
- 설치 시 "Add to PATH" 체크박스 확인 (시스템에 따라 다름)
- Command Prompt에서 진행 권장

### STEP 5 (선택) · SAC LSTM 패치

LSTM 학습 경로를 쓰려면 RLlib 설치본을 패치합니다. 먼저 dry-run.

```
python RLLibLstm\tools\apply_rllib_sac_lstm_patch.py ^
  C:\Users\USER\anaconda3\envs\aip --dry-run
```

Advanced Appendix C에서 자세히 설명.

**순서가 중요한 이유:** 의존성이 깨진 상태에서 학습을 시작하면 Ray 초기화 단계에서 길게 멈추거나 의미 없는 오류를 보게 됩니다. 1–4단계가 모두 통과한 후에만 본 학습을 시작합니다.

---

## Slide 8 — 런타임 자산은 실행 계약 입니다

02 · 환경 준비

아래 파일·폴더는 함부로 이름 변경하거나 이동하지 않습니다. 어떤 자산이 어떤 역할을 하는지 알면 오류 메시지를 훨씬 빨리 해석할 수 있습니다.

| 종류 | 파일 / 폴더 | 주의 |
| --- | --- | --- |
| JSBSim 커널 | JSBSimAIPLib.dll | Release 루트에 존재해야 함. `ctypes`로 직접 로드됨. |
| BT DLL | AIP_BASE.dll AIP_BASE_target.dll | 기본 / target DLL 구분. 팀 DLL은 CLI 인자로 지정. |
| Rule XML | Rule_forTraining.xml Rule_<팀이름>.xml | 기본 Rule 유지. 팀별 Rule은 `--bt-rule-xml`로 임시 활성화. |
| Aircraft / Engine | aircraft/, engine/ | 폴더 이동 금지. F-16 등 항공기 모델 XML. |
| JSBSim scripts | scripts/ | 초기 실행 자산. cruise XML 등 JSBSim 진입 스크립트. |

**왜 강제인가:** JSBSim과 BT DLL은 컴파일 타임에 폴더 구조를 가정하고 빌드되어 있습니다. 자산 이동 시 추적이 어려운 segfault 또는 silent fallback이 발생할 수 있습니다.

---

## Slide 9 — 실패 원인은 4가지 부터 확인합니다

02 · 환경 준비

대부분의 첫 실행 실패는 아래 네 경로 안에 있습니다. 증상 → 확인 → 해결로 차분히.

### DLL을 찾지 못함

**확인:** Release 루트에서 실행 중인가? `JSBSimAIPLib.dll`이 같은 폴더에?

**해결:** `cd DogFightEnv\Release`로 이동 후 재실행. 파일명·DLL 누락 여부 확인.

### import 실패

**확인:** 가상환경이 활성화되어 있는가? `requirements.txt` 설치 완료?

**해결:** `conda activate aip` → `pip install -r requirements.txt` 재실행.

### 모델 로드 실패

**확인:** `metadata.json` + `policy_weights.pkl.gz` 두 파일이 동일 폴더에?

**해결:** `BUNDLE_DIR` 경로 확인. `artifacts/models/<team>/<tag>` 형식.

### 관측 차원 오류 (가장 흔함)

**확인:** 학습 때 `observation_mode`와 추론 때가 다른가? `OBSERVATION_SIZE` 일치?

**해결:** 학습/검증/제출 세 곳을 한 모듈로 통일. 자세한 체인은 슬라이드 30 참고.

**대원칙:** 실패 메시지보다 위 4가지 체크리스트를 먼저 돌리세요. 매뉴얼 작성자 경험상 새 학생의 95%의 첫 실행 오류는 이 4가지 안에 있습니다.

---

## Slide 10

03

환경 계약

Observation · Action · Reward · Termination —
네 가지 계약으로 환경이 움직입니다. 무엇을 자유롭게 바꿔도 되고, 무엇은 절대 깨면 안 되는지를 분명히 합니다.

---

## Slide 11 — 환경은 네 개의 계약 으로 움직입니다

03 · 환경 계약

네 가지의 입출력 모양을 알면 어디를 자유롭게 바꿀 수 있는지, 어디를 건드리면 안 되는지 명확해집니다.

### ① Observation

정책 입력 벡터. mode / module / shape이 학습·검증·제출에서 일치해야 함.

자유도 높음 — `student/my_observation.py`에서 자유롭게 설계.

### ② Action

4차원 연속 제어 `[-1, 1]⁴`. throttle은 내부에서 `[0, 1]`로 변환.

자유도 낮음 — 환경 계약. 바꾸면 BT/JSBSim 연동이 깨집니다.

### ③ Reward

`float` 보상 + `components` dict 반환. 분석 가능한 이름으로 컴포넌트 기록.

자유도 높음 — `student/my_reward.py`의 핵심 설계 영역.

### ④ Termination / Info

종료 사유와 부가 정보. 로그·metric의 해석 근거. 환경에서 자동으로 채움.

자유도 읽기 전용 — 직접 수정하지 않고 해석합니다.

---

## Slide 12 — 관측 모드: 기본 4종 + custom

03 · 환경 계약

`tactical16`은 기본 제공 예시일 뿐 정답이 아닙니다. 본인의 가설에 맞는 관측을 직접 설계하는 것이 핵심.

| 모드 | 차원 | 특징 |
| --- | --- | --- |
| classic12 | 12 | 기본 비교용 (baseline) |
| relative14 | 14 | 상대 위치 중심 |
| tactical16 | 16 | 기본 제공 예시 (templates default) |
| legacy37 | 37 | 구환경 호환 (연구용) |
| custom | ? | 학생 직접 설계 |

**core 메시지:** 정답을 외우지 말고 **가설을 만들어 직접 관측을 설계**하세요. 학습된 정책 성능은 결국 관측 설계에 강하게 의존합니다.

### custom 모드 사용법

학생용 관측을 만들려면 `student/my_observation.py`를 작성하고 다음 인자를 사용합니다.

```
python train_rllib.py ^
  --observation-mode custom ^
  --observation-module student.my_observation
```

같은 학습/검증/제출 어디에서나 **동일한 module path**를 지정해야 차원이 일치합니다.

- `OBSERVATION_MODE = "student8"`
- `OBSERVATION_SIZE = 8`
- `build_observation(...) → np.float32 (N,)`

---

## Slide 13 — 액션과 종료는 결과 해석의 기준

03 · 환경 계약

승패만 보지 마세요. 종료 조건은 정답이 아니라 분석 기준입니다.

### 액션 공간 — 4축 연속 [-1, 1]

| 축 | 의미 | 범위 |
| --- | --- | --- |
| 0 | roll | [-1, 1] |
| 1 | pitch | [-1, 1] |
| 2 | rudder / yaw | [-1, 1] |
| 3 | throttle | [-1, 1] → [0, 1] |

throttle은 정책 입장에선 `[-1, 1]`로 통일된 표현이지만, JSBSim에 전달될 때 내부에서 `[0, 1]`로 변환됩니다.

### 종료 조건 — 7+종

| 그룹 | 조건 |
| --- | --- |
| Health | ownship/target HP 0 이하 |
| Altitude | 최저 고도 미만 |
| Time | `max_engage_time` 도달 |
| Step | `episode_step_limit` 도달 |
| FDM | JSBSim 오류, NaN |
| Guard | 연구용 2-circle 가드 등 |

`summary.json`의 `end_condition`이 어떤 카테고리인지가 정책 개선의 1차 단서입니다.

---

## Slide 14

04

학생 수정 영역

보상 · 관측 · 커리큘럼 · YAML — 네 가지 파일이 학생의 창의력을 담는 곳입니다. 공통 학습 루프는 본체가 담당하므로, 학생 파일은 가능한 한 얇게 유지하는 것이 좋습니다.

---

## Slide 15 — 학생 수정 영역은 분리 되어 있습니다

04 · 학생 작성

공통 학습 루프를 담은 본체(`train_rllib.py` 등) 수정은 지양합니다. 아이디어는 아래 네 파일과 YAML로 주입합니다.

### student/my_reward.py

보상 아이디어. `compute_reward()` 반환 계약을 지키면 자유 설계.

`MY_REWARD_CONFIG` dict + `components` dict로 분석 가능하게.

### student/my_observation.py

관측 아이디어. `OBSERVATION_SIZE`와 `build_observation()` shape 계약.

차원을 바꾸면 bundle은 새로 학습해야 함 (호환 불가).

### student/my_curriculum.py

커리큘럼 단계 아이디어. `get_stages()`가 `list[CurriculumStage]` 반환.

기본 stage 0~14는 참고용 — 자유롭게 재구성 가능.

### experiments/*.yaml

실험 조건을 파일로 보존. `output`/`env`/`algo`/`runtime` 섹션.

Python 모듈은 module path로 주입 (`reward_module`, `observation_module`, `stages_module`).

---

## Slide 16 — my_reward.py: 공식보다 반환 계약

04 · 학생 작성

어떤 공식을 쓰든 자유지만, 두 가지는 지켜야 합니다: **float 총 보상**과 **components dict**.

```
MY_REWARD_CONFIG = {
    "pursuit_scale": 0.3,
    "closure_scale": 0.1,
    "damage_scale": 20.0,
    "low_altitude_penalty": 0.1,
    "step_penalty": -0.01,
}

# 본체에서 자동 호출
def compute_reward(
    obs, action, geo_info, info, config=None,
):
    components = {}
    components["pursuit"] = ...
    components["closure"] = ...
    components["damage"]   = ...
    components["safety"]   = ...
    components["step"]     = ...
    total = sum(components.values())
    return float(total), components
```

### 지켜야 할 것 (계약)

- 반환 = `(float total, dict components)`
- `components`의 키는 **분석 가능한 이름**으로 (예: `pursuit`, `damage`, `step`)
- 각 컴포넌트는 step 단위 스칼라

### 이름 짓기 팁

- 의도가 보이는 이름 — `safety`, `pursuit` ⓞ
- 축약 금지 — `r1`, `x` ✗
- dashboard에서 component별 그래프로 자동 추적

**설계는 별도 가이드 참고:** ATA/AA/LOS/WEZ 등 보상 컴포넌트의 직관은 **“보상 설계 직관 슬라이드”**에서 자세히 다룹니다.

---

## Slide 17 — my_observation.py: 차원 계약

04 · 학생 작성

관측을 새로 만들면 이전 bundle과 호환되지 않습니다. 차원을 바꾸는 결정은 신중하게.

### 필수

- `OBSERVATION_SIZE` — int
- `build_observation(ownship, target, geo_info, wez_config=None) → np.float32(N,)`

### 선택

- `OBSERVATION_MODE` — 식별자 (예: "student8")
- `OBSERVATION_LOW`, `OBSERVATION_HIGH` — 박스 범위
- `describe_observation()` — 차원별 의미 설명

### 차원 변경 위험

- 기존 `checkpoint` / `bundle`과 호환 불가 — 새로 학습
- 학습/로컬/Unreal 세 곳에 모두 같은 module path 지정 필요
- `metadata.json`의 `obs_mode`가 정답 — 추론 환경이 이것을 본다

**일관성 기록 위치 3곳:**
① YAML `env.observation_module` · ② `metadata.json` `observation_module` · ③ `my_submission.py` `OBSERVATION_MODULE`. 세 곳이 같은 값을 가져야 추론 시 차원이 맞습니다. (자세한 일관성 체인은 슬라이드 30 참고)

---

## Slide 18 — my_curriculum.py: get_stages() 계약

04 · 학생 작성

기본 stage는 출발점이 아니라 계약 확인용 참고입니다. 본인의 학습 시나리오에 맞춰 자유롭게 재구성하세요.

```
from dogfight.ai.curriculum import CurriculumStage

def get_stages() -> list[CurriculumStage]:
    return [
        CurriculumStage(
            name="my_stage_0",
            initial_scenario=...,
            target_mode="fixed",
            promote_when={"reward_mean": 5.0},
            ...
        ),
        CurriculumStage(
            name="my_stage_1",
            target_mode="behavior_tree",
            ...
        ),
        ...
    ]
```

```
python train_curriculum.py ^
  --stages-module student.my_curriculum
```

### 기본 curriculum 참고용 14단계

- **Stage 0–3**: survival / pursuit / WEZ / autopilot
- **Stage 4–13**: two-circle head-on alpha 0°–180°
- **Stage 14**: full dogfight

### 설계 방향 예시

- 고정 표적으로 안정 비행부터
- loiter / autopilot으로 추종 행동
- BT 상대로 점진적 난이도 상승
- 각 stage `promote_when`으로 자동 진급 조건 명시

---

## Slide 19

05

실험 관리

YAML 템플릿 6종 · dry-run · 두 실험 비교 · 모델 번들. 코드 외부에서 실험을 “기록되게” 만드는 방법입니다.

---

## Slide 20 — YAML 템플릿 6종 — 실험 조건을 보존

05 · 실험 관리

YAML은 조건을 기록하고, Python 아이디어는 module로 주입합니다.

| 템플릿 | 용도 | 주요 키 |
| --- | --- | --- |
| student_sac_mlp.yaml student_ppo_mlp.yaml | 일반 학생 시작점 · MLP baseline | `algo.mlp`, `reward_module`, `observation_module` |
| student_sac_lstm.yaml student_ppo_lstm.yaml | LSTM 경로 (SAC는 RLLibLstm 패치 필요) | `algo.lstm`, `algo.network` |
| student_mixed_initial_sac_mlp.yaml | BT / loiter target 혼합 · MLP 예시 | `env_config.initial_scenario` |
| student_mixed_initial_sac_lstm.yaml | mixed initial + SAC LSTM (고급) | `RLLibLstm`, `initial_scenario` |

**운영 원칙:** 원본 YAML을 직접 수정하지 말고, `Copy-Item`으로 복사해 `team01_sac_mlp_v1.yaml`처럼 실험명을 붙입니다. 그래야 어떤 조건으로 돌렸는지 나중에 추적할 수 있습니다.

---

## Slide 21 — dry-run → smoke → 본실행

05 · 실험 관리

긴 학습 전에 두 번의 안전망을 둡니다. dry-run으로 명령어 변환을 보고, smoke로 1–10 iteration만 짧게 돌립니다.

### STEP 1 · dry-run

YAML → CLI 변환만 출력. 학습은 시작하지 않음.

```
python scripts\run_experiment.py ^
  experiments\team01_v1.yaml --dry-run
```

**확인:** output.name/tag, observation_module, env_config 분기.

### STEP 2 · smoke (1–10 iter)

실제로 짧게 돌려보기. 관측 shape · reward 반환 · bundle 저장 확인.

```
python train_rllib.py ^
  --algorithm sac --iterations 1 ^
  --output-name team01 --output-tag smoke
```

**이상 신호:** NaN reward, shape mismatch, bundle 미생성.

### STEP 3 · 본실행

위 두 단계가 통과한 뒤에만 긴 학습 시작.

```
python scripts\run_experiment.py ^
  experiments\team01_v1.yaml
```

이 시점에서는 reward 곡선이 의미 있게 변화할 만큼 충분히 돌립니다.

**Ray 정리 권장:** smoke 직전 `python -m ray stop --force`로 잔존 노드 정리. 이전 학습이 비정상 종료된 후에는 거의 필수.

---

## Slide 22 — 두 실험을 비교할 때는 3개 로그 를 함께 봅니다

05 · 실험 관리

숫자(metric)와 조건(config)을 함께 보지 않으면 “왜 그렇게 됐는지” 알 수 없습니다.

### Run A · sac_mlp_v1

- YAML: `student_sac_mlp.yaml`
- `config.json` · observation_module 확인
- `metrics.jsonl` · reward_mean, crash_rate

### Run B · mixed_initial_sac_mlp_v1

- YAML: `student_mixed_initial_sac_mlp.yaml`
- `config.json` · initial_scenario 분포 확인
- `metrics.jsonl` · win_rate, ep_min_distance

| 파일 | 볼 것 | 역할 |
| --- | --- | --- |
| metrics.jsonl | reward_mean 추세, crash_rate, win_rate | dashboard scalar 차트의 원천 |
| config.json | YAML/CLI/module 설정 | 조건 비교의 정답지 |
| metadata.json | obs_mode / observation_module | bundle 해석 기준 |

---

## Slide 23 — 모델 번들은 제출 단위 입니다

05 · 실험 관리

두 파일만 있으면 어디서든 같은 정책을 추론할 수 있습니다 (호환 환경 가정).

artifacts/models/<team>/<tag>/
├── metadata.json # 관측 모드·LSTM 여부·구조 메타
└── policy_weights.pkl.gz # 정책 가중치

### metadata.json 핵심 키

```
{
  "algorithm": "sac",
  "obs_mode": "tactical16",
  "observation_module": "",
  "use_lstm_sac": false,
  "lstm_cell_size": 64,
  ...
}
```

### 제출에 필요한 것

- `BUNDLE_DIR` = `artifacts/models/<team>/<tag>`
- 두 파일이 같은 폴더에 있어야 함
- `my_submission.py`에서 `BUNDLE_DIR` 설정

### 주의

- 관측 차원이 다르면 추론 즉시 실패
- LSTM 학습 모델은 LSTM 옵션을 켠 환경에서만 동작
- `metadata.json`이 누락되면 RLlib가 구조를 모름

---

## Slide 24

06

학습 + 로컬 검증

PPO/SAC · 재개 방식 · 로컬 교전 · 종료 사유 분석. 학습한 모델을 실제로 돌려보는 단계입니다.

---

## Slide 25 — PPO · SAC · 재개 방식

06 · 학습 + 검증

알고리즘과 재개 방식 선택은 실험 목적에 맞춰. 도구일 뿐, 정답은 아닙니다.

### 알고리즘 선택

### PPO

정책 업데이트 폭 제한. 비교적 안정적인 baseline. 주 옵션: `clip-param`, `gae-lambda`.

### SAC

Entropy 기반 탐색. 연속 제어 실험에 적합. 주 옵션: `tau`, `target-entropy`.

**LSTM 경로:** SAC LSTM은 RLlib 설치본 패치가 필요합니다 (`RLLibLstm/`). Appendix C 참고.

### 재개 방식 — 보존 상태가 다름

| 방식 | 옵션 | 보존 |
| --- | --- | --- |
| **Native checkpoint** | --restore-checkpoint | policy + optimizer + replay |
| **Lightweight bundle** | --init-bundle | policy weight only |
| **Curriculum resume** | --resume | stage/iteration 위치 |

**구분 기준:** 중단된 학습 그대로 이어가려면 native checkpoint. 좋은 정책을 시드로 새 실험을 시작하려면 lightweight bundle.

---

## Slide 26 — 로컬 검증은 제출 전 안전 점검

06 · 학습 + 검증

bundle을 ownship에 태우고, BT target과 1v1 교전을 돌려 종료 사유부터 확인합니다.

1**bundle 선택**

2**backend 조합**

3**교전 실행**

4**종료 사유**

5**다음 실험**

```
python run_local_dogfight.py ^
  --ownship-backend rl ^
  --ownship-bundle-dir artifacts\models\team01\v1 ^
  --target-backend bt ^
  --target-bt-dll AIP_BASE_target.dll ^
  --observation-mode tactical16 ^
  --save-log
```

custom 관측을 사용한 정책은 `--observation-mode custom --observation-module student.my_observation` 함께 지정.

### backend 조합

|  |  |
| --- | --- |
| rl | 학습된 정책 |
| bt | C++ 행동트리 DLL |
| hybrid | RL + BT 결합 |
| fixed | 고정/단순 행동 |

---

## Slide 27 — 먼저 볼 것은 승률 보다 실패 원인

06 · 학습 + 검증

`summary.json`의 `end_condition`이 어떤 카테고리에 몰려 있는지로 정책의 약점을 진단합니다.

### ownship_dead

**해석:** 적의 사거리에 들어갔거나 추격 실패 후 역공받음.

**조치:** AA 페널티 강화, WEZ 회피 보상 추가, 회피 기동 학습.

### ownship_alt (저고도)

**해석:** 강하 기동 학습 후 저고도 복구 실패.

**조치:** low_altitude_penalty 강화, 최저고도 가드 점검.

### target_dead

**해석:** 성공. 단, WEZ 점유 시간이 적정한지 함께 확인 (한 방 운인지, 점진 추격인지).

**조치:** 다음 단계 난이도(behavior_tree) 도입 고려.

### max_time / step_limit

**해석:** 결판 못 냄. 추격 의지 부족 또는 둘 다 회피 학습.

**조치:** closure 보상 강화, step 페널티 검토.

**분석 절차:** 10–20회 교전을 돌려 `end_condition` 카운트 분포를 봅니다. 한 카테고리에 70% 이상 몰리면 그 방향의 보상·관측 수정이 가장 큰 영향.

---

## Slide 28

07

Unreal 제출

경진대회 Unreal 서버에 학습된 정책을 연결하는 단계. 로컬 검증과 동일한 입력 계약을 사용합니다.

---

## Slide 29 — Unreal 접속도 같은 입력 계약 을 씁니다

07 · Unreal 제출

PlaneInfo → Observation → Policy/BT → CMD → Unreal step. 로컬 검증과 같은 module path와 관측 모드를 사용합니다.

1**PlaneInfo**UDP 수신

2**Observation**벡터 생성

3**Policy / BT**액션 계산

4**CMD**UDP 송신

5**Unreal step**시뮬레이션 진행

### my_submission.py 수정 지점

| 설정 | 의미 | 확인 |
| --- | --- | --- |
| TEAM_NAME | 팀 표시 이름 | 등록명과 일치 |
| SERVER_IP SERVER_PORT | Unreal 서버 주소 | 운영 공지 기준 |
| MODE | rl / bt / hybrid | 실험 의도와 일치 |
| BUNDLE_DIR | 제출 policy 경로 | metadata·weights 확인 |
| OBSERVATION_MODE OBSERVATION_MODULE | policy 입력 계약 | 학습 설정과 일치 |

```
python run_unreal_inference.py ^
  --mode rl ^
  --bundle-dir artifacts\models\team01\v1 ^
  --team-name team01 ^
  --server-ip <공지된 IP> ^
  --server-port 9999
```

**제출 직전 체크:** 로컬에서 같은 bundle로 `run_local_dogfight.py --target-backend bt`를 한 번 더 돌려 종료 사유가 정상인지 확인하는 것이 가장 안전한 사전 점검입니다.

---

## Slide 30 — 관측 일관성 체인 — 5개 위치를 통일하세요

08 · 가장 흔한 버그 · 본문 승격

학생 95%가 한 번씩 겪는 차원 mismatch는 거의 모두 아래 5개 위치 중 하나가 어긋났기 때문입니다.

1**YAML**experiments/*.yaml

2**Train CLI**train_rllib.py

3**Metadata**metadata.json

4**Local**run_local_dogfight.py

5**Submission**my_submission.py

| 위치 | 확인할 값 | 불일치 위험 |
| --- | --- | --- |
| YAML | `env.observation_mode` / `env.observation_module` | 학습 조건 기록 오류 → 재현 불가 |
| train_rllib.py | `--observation-mode` / `--observation-module` | 학습 입력 차원 불일치 → 즉시 실패 |
| metadata.json | `obs_mode` / `observation_module` | bundle 해석 오류 → 추론 불일치 |
| run_local_dogfight.py | `--observation-mode` / `--observation-module` | 로컬 성능 왜곡 → 잘못된 의사결정 |
| my_submission.py / CLI | `OBSERVATION_MODE` / `OBSERVATION_MODULE` `BT_RULE_XML` / `ACTION_REPEAT` | 제출 추론 입력 또는 BT 자산 불일치 → 시합 패 |

**점검 한 줄:** `metadata.json`이 정답지입니다. 모든 다른 위치는 이것과 같은 값을 가져야 합니다. 의심스러우면 `metadata.json`을 직접 열어 확인하세요.

---

## Slide 31 — 제출 전 최종 체크리스트

09 · 최종 점검

시합·평가 직전에 한 번 더 훑는 항목들. 한 번이라도 막힌 적이 있는 항목은 두 번 확인.

- **실행 위치** — `Release/`에서 실행 중인가?
- **가상환경** — `conda activate aip` 활성?
- **DLL** — `JSBSimAIPLib.dll` · `AIP_BASE*.dll` Release 루트?
- **관측 일치** — 학습/local/submission 세 곳 같은 module path?
- **bundle 두 파일** — `metadata.json` + `policy_weights.pkl.gz`?

- **로컬 검증** — `--save-log`로 마지막 교전 1회 확인?
- **종료 사유 정상** — `summary.json`이 의미 있는 outcome?
- **YAML 보존** — 사용한 YAML이 `experiments/`에 남아 있나?
- **my_submission.py** — TEAM_NAME, SERVER_IP/PORT, BUNDLE_DIR 채움?
- **LSTM 경로** — LSTM 모델이면 RLlib 패치 적용 확인?

**운영 원칙 한 줄:** 모르는 상태로 제출하지 않습니다. 자신 없는 부분은 로컬에서 한 번 더 돌려 확인한 뒤 제출합니다.

---

## Slide 32

A

Appendix

오류 FAQ · 로그 종류와 사용법 · SAC LSTM 패치 — 본문 흐름을 끊지 않도록 부록으로 분리한 참고 자료.

---

## Slide 33 — 오류 FAQ

Appendix A

증상 → 먼저 확인 → 조치 순서로 정리한 표.

| 증상 | 먼저 확인 | 조치 |
| --- | --- | --- |
| DLL 오류 | Release 루트와 파일명 | 위치/이름 확인, 재다운로드 |
| import 실패 | Python · venv · requirements | `conda activate aip` → `pip install -r requirements.txt` |
| 모델 로드 실패 | BUNDLE_DIR과 파일 2개 | `metadata.json` + `policy_weights.pkl.gz` 동일 폴더 확인 |
| 관측 오류 (shape mismatch) | mode/module/shape | 학습 설정과 제출 설정 비교 — 슬라이드 30의 5위치 체인 |
| 서버 무응답 | IP/port/방화벽 | 운영 공지와 네트워크 환경 확인 |
| Ray 초기화 멈춤 | 이전 Ray 노드 잔존 | `python -m ray stop --force` |
| NaN reward | my_reward.py 계산에서 0 division/log(0) | 안전 가드 추가, smoke iter=1로 재현 |

---

## Slide 34 — 로그는 다음 가설의 근거 입니다

Appendix B

로그를 그냥 쌓지 말고 무엇을 보러 가는지 명확히 합니다.

| 로그 | 볼 것 | 사용 |
| --- | --- | --- |
| training_log.csv | reward, crash, win, WEZ, distance | 학습 추세 분석 |
| metrics.jsonl | dashboard scalar 데이터 | 여러 run 시각 비교 |
| config.json | YAML/CLI/module 설정 | 조건 비교의 정답지 |
| Tacview CSV | 위치 · 자세 · health 시계열 | 로컬 교전 복기 |
| summary.json | end_condition · outcome | 종료 사유 카운트 분석 |

### Dashboard 실행

```
python tools\dashboard.py ^
  --training-logdir artifacts\dashboard ^
  --logdir logs ^
  --port 7860
```

브라우저: `http://127.0.0.1:7860`

### Replay 탭 바로 열기

```
python tools\dashboard.py ^
  --default-tab replay ^
  --logdir logs ^
  --port 7860
```

`http://127.0.0.1:7860/?tab=replay`

---

## Slide 35 — SAC LSTM 패치 적용

Appendix C · Advanced

LSTM 학습 경로를 쓰려면 Ray 2.54.0 RLlib 설치본을 패치해야 합니다. `RLLibLstm/`에 원본·패치본·manifest가 보관되어 있습니다.

### STEP 1 · dry-run 패치

```
python RLLibLstm\tools\apply_rllib_sac_lstm_patch.py ^
  C:\Users\USER\anaconda3\envs\aip --dry-run
```

### STEP 2 · 실제 패치 적용

```
python RLLibLstm\tools\apply_rllib_sac_lstm_patch.py ^
  C:\Users\USER\anaconda3\envs\aip
```

### STEP 3 · LSTM YAML 학습

```
python scripts\run_experiment.py ^
  experiments\student_sac_lstm.yaml
```

### LSTM scope 3종

- **actor_only** — actor LSTM + MLP Q (가장 가벼움)
- **actor_critic** — recurrent Q / twin / target Q (Ray 1.9.2 RNNSAC 모사)
- **sequence_v1** — YAML layer sequence로 actor/Q 구조 자유 설계

**주의:** 패치는 사용자 conda env의 `site-packages`를 수정합니다. 다른 PC에서 작업하려면 `RLLibLstm/manifest.json`과 가이드를 함께 전달하세요.

**SAC LSTM smoke:** 학습 직전 `ray stop --force` → 10 iter smoke → bundle 생성 확인 → 본실행 순서.