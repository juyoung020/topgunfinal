# 에어프라이어 (AeroFlyer) — AI Pilot Top Gun Challenge 2026 본선

**AI Pilot Top Gun Challenge 2026** 본선에 참가한 팀 **에어프라이어**의 작업 저장소입니다.
강화학습으로 F-16 1대 1 근접 공중전(dogfight) 조종 AI 를 학습시켰고, 본선에 실제로 제출한 실행 파일과 가중치, 학습 코드, 실험 기록을 담고 있습니다.

## 과제

- JSBSim 비행 역학 위에서 F-16 두 대가 1대 1 로 교전하고, 상대를 먼저 격추하거나 시간 종료 시 우위를 점하면 이깁니다.
- 조종 입력은 **roll / pitch / yaw / throttle** 4개뿐입니다 (조종면 직접 제어 불가).
- 제출물은 대회 교전 서버에 접속해 실시간으로 조종하는 클라이언트입니다.

## 방법

| 항목 | 내용 |
|---|---|
| 알고리즘 | PPO + LSTM (Ray RLlib 2.54, PyTorch) |
| 정책 | LSTM cell 128, 시퀀스 32, 10 Hz 제어 |
| 관측 | 직접 설계한 16차원 (저고도 구간은 고도 해상도를 높여 추락 회피를 학습하기 쉽게 함) — `student/my_observation.py` |
| 보상 | 격추 승리·추락 패널티·명중/피격 데미지·저고도 경고 등 항목별 가중치 — `student/my_reward.py` |
| 학습 방식 | 셀프플레이 → 실서버에서 진 상대 위주의 고정 상대 풀로 이어 학습, 스폰 고도·자리(Blue/Red) 무작위화 |
| 판정 | 학습 중 저장되는 리플레이를 종류별(격추승/동시격추/격추패/추락/종료 우위·열위)로 집계, 후보는 실서버 교전으로 최종 확인 |

자세한 학습 이력(보상·하이퍼파라미터 변경, 계보, 실패 사례)은 `CLAUDE.md` 와 `Update/강화학습환경/변경사항.md` 에 날짜별로 남아 있습니다.

## 본선 제출본

본선에 제출한 실행 파일 두 개는 릴리스 [`final-submission`](https://github.com/juyoung020/topgunfinal/releases/tag/final-submission) 에 있습니다.

| 제출 | 실행 파일 | 가중치 |
|---|---|---|
| 메인 | `AeroFlyer.exe` (`에어프라이어_APTGC2026_main.zip`) | `model/final_main_recv_daeil_iter8820` |
| 헤드온(정면 교전) 특화 | `AeroFlyer_headon.exe` (`에어프라이어_APTGC2026_headon.zip`) | `model/final_headon_peak_daeilheadon_iter0401` |

학습 도중 챔피언·비교 상대로 쓴 다른 가중치와 각각의 실서버 전적은 [`model/README.md`](model/README.md) 에 정리되어 있습니다.

## 폴더 구조

```
model/                    추론용 가중치 번들 (metadata.json + policy_weights.pkl.gz), 계열별 설명은 model/README.md
Update/강화학습환경/       학습 환경 (대회 제공) + 우리 코드
  student/                  ★ 우리가 작성한 부분: 관측·보상·커리큘럼·제출 클라이언트·판정 도구
    my_observation.py         16차원 관측
    my_reward.py              보상 함수
    my_curriculum.py          상대 풀·스폰 구성
    my_submission.py          교전 서버 접속 클라이언트 (제출용)
    tools/                    리플레이 판정(replay_judge.py), 학습 상태 시각화(eval_visual.py) 등
    EXECUTION_MANUAL.md       실행 절차서
  tools/                    실행 스크립트(launch.ps1), 대시보드, 실서버 대전 도구
  변경사항.md                학습 이력
BattleServer_V1.2_VeryLow/ 교전 서버·뷰어 (대회 제공)
cutoff_model/              공식 컷오프 상대 클라이언트 (대회 제공)
docs/                      대회 강의 자료·매뉴얼, 실서버 대전 결과, 교전 기하 분석
```

## 실행

1. **위치**: 저장소를 `C:\topgunfinal` 처럼 C: 드라이브 바로 아래, 공백·한글·밑줄 없는 경로에 클론합니다. 교전 서버의 컷오프 실행 파일이 이 조건에서만 동작합니다.
2. **교전 서버 대용량 파일**: GitHub 용량 제한(100 MB) 때문에 `DogFightViewer-Windows.ucas`, `DogFightViewer-Win64-Shipping.exe` 두 파일은 저장소에 없습니다. 릴리스 [`backup-20260829`](https://github.com/juyoung020/topgunfinal/releases/tag/backup-20260829) 의 `BattleServer_V1.2_VeryLow.zip` 을 `BattleServer_V1.2_VeryLow\` 에 풀어 덮어씁니다.
3. **라이브러리** (Python 3.11):
   ```
   pip install "torch==2.11.0" "ray[rllib]>=2.54.0" numpy "gymnasium>=1.2.2" "dm-tree>=0.1.10" "pymap3d>=3.1.0" "scipy>=1.17.1" filelock
   ```
4. **학습된 가중치로 교전 서버에 붙이기**:
   ```
   cd Update\강화학습환경
   python attach_client.py --bundle ..\..\model\final_main_recv_daeil_iter8820 --team-name AeroFlyer --server-ip 127.0.0.1 --server-port 9999
   ```
   서버 띄우는 법은 `BattleServer_V1.2_VeryLow/CLAUDE.md`, 학습을 다시 돌리는 법은 `Update/강화학습환경/student/EXECUTION_MANUAL.md` 를 보세요.

## 알림

- `BattleServer_V1.2_VeryLow/`, `cutoff_model/`, `Update/강화학습환경/` 의 기반 환경 코드, `docs/` 의 강의 자료·매뉴얼은 **대회 주최 측이 참가팀에 제공한 것**이며 권리는 주최 측에 있습니다. 재현을 위해 함께 보관합니다.
- 팀이 작성한 부분은 주로 `Update/강화학습환경/student/`, `Update/강화학습환경/tools/`, `model/` 과 학습 기록 문서입니다.
- `CLAUDE.md`, `AGENTS.md` 는 작업 중 AI 코딩 도우미에게 준 작업 규칙·현황 메모입니다.
