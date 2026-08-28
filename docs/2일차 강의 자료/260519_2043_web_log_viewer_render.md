<!--
원본 파일: 2일차 강의 자료/260519_2043_web_log_viewer_render.png
원본 형식: PNG 스크린샷 (Web Log Viewer 렌더 화면)
변환 방식: Claude 비전 전사 (화면 내 모든 텍스트·수치를 그대로 전사 + UI 배치 서술)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# 260519_2043_web_log_viewer_render (웹 로그 뷰어 화면)

**전체 개요:** 웹 기반 "DogFight Log Playback" 뷰어의 재생 화면 스크린샷. 3D 씬에 파란(ownship)·빨간(target) 궤적이 그려져 있고, 상·우측에 HUD/지표 오버레이와 사이드바가 있음. 화면의 모든 텍스트·수치를 위치별로 그대로 전사하면:

## 상단 바
- 제목: **DogFight Log Playback**
- 로그 선택 드롭다운: `2025_7_9_12_28_18`
- 버튼: `Reload` · `Pause`
- `Speed` 슬라이더 — 표시값 **5.0x**
- 우측 상태: `Loaded 2025_7_9_12_28_18…`

## 좌측 상단 오버레이 (재생 상태)
```
PLAY  t=7.50s  x5.0
Own  alt= 4684m  v= 209.0m/s  hp=n/a
Tgt  alt= 4683m  v= 211.2m/s  hp=n/a
```

## 우측 상단 오버레이 (교전 지표)
| 항목 | 값 |
| --- | --- |
| Range | 2745 m |
| Closure | -141.7 m/s |
| Rel Alt | -1 m |
| Own ATA | 94.3 deg |
| Target AA | 94.5 deg |
| Own WEZ | out |
| Threat | out |

## 우측 사이드바
**DISPLAY** (체크박스, 모두 체크됨 ☑)
- ☑ HUD
- ☑ Sea
- ☑ Trails
- ☑ WEZ

**REPLAY** — 진행 슬라이더 (재생 초반 위치)

| 항목 | 값 |
| --- | --- |
| Time | 7.50s |
| Range | 2745 m |
| Closure | -141.7 m/s |
| Rel Alt | -1 m |

**LOGS** (JSON)
```json
{
  "ownship": "2025_7_9_12_28_18_ownship_(F-16)[Blue].csv",
  "target": "2025_7_9_12_28_18_target_(F-16)[Red].csv",
  "metadata": null,
  "end": "n/a"
}
```

**DEBUG**
- WebGL: ok
- Frames: 7165
- Samples: 5796  *(화면 하단에서 잘림 — 값 일부만 보임)*

## 하단 중앙 파일 정보 박스
```
2025_7_9_12_28_18_ownship_(F-16)[Blue].csv
2025_7_9_12_28_18_target_(F-16)[Red].csv
End: n/a
```

## 중앙 3D 씬 서술
- 파란색 바다/지형(삼각형 형태의 수평선)이 배경.
- **파란 궤적**(ownship): 좌측에서 아래로 완만하게 내려갔다가 중앙으로 이어지는 곡선.
- **빨간 궤적**(target): 중앙에서 우측 상단의 한 점까지 올라가는 직선에 가까운 곡선. 두 궤적 모두 옅은 잔상(trail)이 함께 표시됨.
