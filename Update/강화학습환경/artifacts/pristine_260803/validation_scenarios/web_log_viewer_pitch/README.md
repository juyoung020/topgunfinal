# Web Log Viewer Pitch/Heading 검증 시나리오

## 목적

이 로그 세트는 다음 두 회귀를 눈으로 확인하기 위한 결정론적 시나리오다.

1. ENU 표시 좌표에서 양의 pitch가 기수 상승으로 보이는지 확인
2. `+X` 기수 F-16 모델이 180도 뒤집히지 않고 진행 방향을 보는지 확인

## 구성

- Blue: yaw 0도(북쪽), 속도 100 m/s
  - 0~5초: pitch 0도, 고도 1000 m
  - 5~10초: pitch +30도, 고도 1000→1250 m
  - 10~15초: pitch 0도, 고도 1250 m
  - 15~20초: pitch -30도, 고도 1250→1000 m
  - 20~24초: pitch 0도, 고도 1000 m
- Red: yaw 180도(남쪽), pitch 0도, 고도 1125 m

## 실행

`DogFightEnv/MyTrainEnv`에서:

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe tools\web_log_viewer.py `
  --logdir validation_scenarios\web_log_viewer_pitch `
  --port 7870
```

또는 `DogFightEnv/Release`에서 같은 명령을 실행한다. 두 서버를 동시에 비교하면
Release 포트를 `7871`로 변경한다.

브라우저에서 다음 주소를 연다.

```text
http://127.0.0.1:7870/?tab=replay
```

Replay 목록에서 `pitch_rotation_validation` 로그를 선택한다.

## 수동 확인 순서

1. 속도를 `1x` 이하로 낮추고 카메라를 `Blue`로 선택한다.
2. 2초에 일시정지한다. Blue 기수는 북쪽 진행 방향을 보고 수평이어야 한다.
3. 7초에 일시정지한다. CSV pitch는 +30도이고 기수와 WEZ cone은 위쪽이어야 하며,
   trail은 1000 m에서 1250 m로 상승 중이어야 한다.
4. 12초에 일시정지한다. Blue는 1250 m에서 다시 수평이어야 한다.
5. 17초에 일시정지한다. CSV pitch는 -30도이고 기수와 WEZ cone은 아래쪽이어야 하며,
   trail은 1250 m에서 1000 m로 하강 중이어야 한다.
6. 22초에 일시정지한다. Blue는 1000 m에서 다시 수평이어야 한다.
7. Red를 선택한다. Red는 yaw 180도로 남쪽을 향해 수평 비행해야 한다.

## 실패 판정

- 7초에 Blue가 아래를 보면 pitch 회전 행렬 부호가 다시 반전된 것이다.
- 17초에 Blue가 위를 보면 같은 pitch 부호 회귀다.
- 항공기가 trail 진행 방향의 반대를 보거나 꼬리부터 이동하면 모델 yaw offset이
  다시 180도로 설정된 것이다.
- 항공기 기수와 WEZ cone이 반대 방향이면 시각 모델 회전과 전술 전방 벡터 계약이
  서로 불일치한 것이다.

## 자동 파서 확인

`DogFightEnv/MyTrainEnv`에서 다음 명령을 실행한다.

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe `
  validation_scenarios\web_log_viewer_pitch\verify_scenario.py `
  --env-root .
```

Release 파서를 확인할 때는 `DogFightEnv/Release`에서 같은 명령을 실행한다.

정상이면 다음 핵심 값이 출력된다.

```text
PASS env_root=...
frames=25 checkpoints=5 pair_count=1
north_climb=(..., 0.866025..., 0.5)
north_dive=(..., 0.866025..., -0.5)
south_level=(..., -1.0, 0.0)
```

## 판단 근거

- Blue의 위치 변화와 pitch 값을 함께 설계해 모델 자세와 실제 trail 경사를 직접
  대조할 수 있다.
- Red는 반대 heading의 수평 기준기로 사용해 180도 모델 반전 여부를 쉽게 판별한다.
- 로그는 viewer가 요구하는 Blue/Red 파일명 및 CSV 헤더 계약을 그대로 사용한다.