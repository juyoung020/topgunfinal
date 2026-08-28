<!--
원본 파일: 1일차 강의 자료/2026 AI Pilot Top Gun Challenge.pptx
원본 형식: PPTX (slides=61, pictures=85)
변환 방식: python-pptx(텍스트·표·노트 무손실) + 슬라이드 렌더 비전 서술
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# 2026 AI Pilot Top Gun Challenge


---

## Slide 1

2026 AI Pilot Top Gun Challenge

AI Takes Flight

Competition Technology Partner

REALTIMEVISUAL


> 🖼️ **[이미지 11개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 소개


> 🔍 **시각 서술:** 표지. 검은 배경에 대형 흰 제목 '2026 AI Pilot Top Gun Challenge', 부제 'AI Takes Flight'. 우하단 'Competition Technology Partner / REALTIMEVISUAL'. 하단에 후원기관 로고 띠: 과학기술정보통신부, KASA 우주항공청, 방위사업청, KAI 한국항공우주산업(주), 한화시스템, LIG Defense&Aerospace, KOREAN AIR, 대한민국공군(REPUBLIC OF KOREA AIR FORCE), HYUNDAI Rotem 현대로템, REALTIMEVISUAL(Reality & Dream), IT dongA.


---

## Slide 2

- 특강 1일차:

- #Orientation

- - 대회 소개

- - 교전 룰 소개

- - 개발 환경 & 대회 경기 환경 소개

- #전투기 AI에 대하여

- #Behavior Tree 기반 AI

- #실습


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 목차 슬라이드. 좌측에 원형 전투기 아이콘(청록 그라데이션). 우측 목차: 01 Orientation(하위: 대회 소개 / 교전 룰 소개 / 개발 환경 & 대회 경기 환경 소개), 02 전투기 AI에 대하여, 03 Behavior Tree 기반 AI, 04 실습.


---

## Slide 3

대회소개

총 참여 신청 팀 : 288팀

Sponsors


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 대회소개. '총 참여 신청 팀 : 288팀'. 'Sponsors' 라벨 아래 후원 로고 3열 그리드: (1행) 과학기술정보통신부 / KASA 우주항공청 / 방위사업청, (2행) 대한민국공군 / KOREAN AIR / KAI 한국항공우주산업(주), (3행) 한화시스템 / HYUNDAI Rotem 현대로템 / LIG Defense&Aerospace, (4행) REALTIMEVISUAL(Reality&Dream) / IT dongA / (빈칸).


---

## Slide 4

대회 소개 : 수상 체계

| 명칭 | 후원 기관 명의 시상 | 상금(만원) | 비고 |
| --- | --- | --- | --- |
| 대상 | 과학기술정보통신부장관상 <br> &한국항공대학교 총장상 | 1000 | 우승팀 |
| 최우수상 | 공군참모총장상 | 500 | 준우승팀 |
| 우수상 | 방위사업청장상, <br> 우주항공청장상 | 200 | 3,4위팀 |
| 학술상 | 대한항공 사장상 | 200 | 학술 발표 세션 최우수 팀 |
| 장려상 | KAI, 한화시스템,  <br> 현대로템, LIG D&A  <br> 사장상 | 100 | 8강 진출팀 |
| 본선진출상 | 한국항공대학교 <br> SW중심대학사업단장상 | 50 | 본선 진출팀 |


**발표자 노트:**


> 순간적으로 대학원 졸업후 한번도 연락 안드린 교수님께 연락해서 박사과정 해볼까 하는 위험한 충동을 정말 짧게 느낄 만큼 매력적인 수상 체계


> 🔍 **시각 서술:** 대회 소개 : 수상 체계. 보라 헤더 표. [명칭 | 후원 기관 명의 시상 | 상금(만원) | 비고] — 대상 | 과학기술정보통신부장관상 & 한국항공대학교 총장상 | 1000 | 우승팀 // 최우수상 | 공군참모총장상 | 500 | 준우승팀 // 우수상 | 방위사업청장상, 우주항공청장상 | 200 | 3,4위팀 // 학술상 | 대한항공 사장상 | 200 | 학술 발표 세션 최우수 팀 // 장려상 | KAI, 한화시스템, 현대로템, LIG D&A 사장상 | 100 | 8강 진출팀 // 본선진출상 | 한국항공대학교 SW중심대학사업단장상 | 50 | 본선 진출팀.


---

## Slide 5

대회소개 : 배경

| 국가/권역 | 공개 사례 | 성격 |
| --- | --- | --- |
| 중국 | PLA 조종사 vs AI 모의 공중전, Red Eye AI, 다수 UCAV 공중전 논문 | 시뮬레이션/훈련/자율기동 연구 |
| 러시아 | Su-57 AI co-pilot 보도 | 조종사 보조/전술지원 |
| 스웨덴+독일 | Saab + Helsing Project Beyond, AI Gripen E vs human Gripen D | 실제 전투기급 플랫폼 AI 조종 시험 |
| 독일/유럽 | Helsing CA-1 Europa | 자율 전투 UCAV/윙맨 |
| 인도 | Kaal Bhairava AI combat aircraft/drone | 자율 전투 드론/UCAV |
| 영국/프랑스/일본 | GCAP/FCAS/무인 윙맨/자율 임무 시스템 | 차세대 전투체계 일부 |

- 천조국 행님들이랑 다른 나라들은 저렇게 개발중인데…

- 우리나라는 뭐하고 있냐?


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 관심있는 사람은 한번쯤 봤을수도 있는 기사미국은 1000조국이라는 별명처럼 국방비로 전투기를 테스트로 추락시켜도 되는 나라라 빠르게 적용 실험중


> 🔍 **시각 서술:** 대회소개 : 배경. 뉴스 기사 스크린샷 콜라주. 상단 기사 제목 'AI 조종사 vs 인간 조종사… F-16 전투기로 첫 실제 \'도그 파이트\'' (부제: 작년 9월 미 에드워즈 공군기지 상공에서 / 미 공군 장관 "AI 요원, 실제 전투 비행의 가장 중요한 장벽 깨", 이철민 기자, 업데이트 2024.04.19. 19:32). 하단 사진: X-62A 비스타(VISTA) 전투기가 산악 상공에서 배면 비행하는 모습(캡션: 기계학습 AI 요원이 조종하는 X-62A 비스타 전투기가 에드워즈 공군기지 상공에서 배면 비행). 겹쳐진 표 [국가/권역 | 공개 사례 | 성격]: 중국(PLA 조종사 vs AI 모의 공중전…, 다수 UCAV 공중전), 러시아, 스웨덴+독일, …AI combat aircraft/drone(자율 전투 UCAV/윙맨·자율 전투 드론/UCAV), GCAP/FCAS/무인 윙맨/자율 임무 시스템(차세대 전투체계 일부). 빨간 손글씨 오버레이: '천조국 행님들이랑 다른 나라들은 저렇게 개발중인데… 우리나라는 뭐하고 있냐?'.


---

## Slide 6

대회소개 : 배경

- 중간 개발 결과물을

- 활용한 훈련용 시뮬레이터


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 우리나라 역시 미국보다는 늦게 시작했지만 관련 연구를 진행중에 있음
> 
> 그리고 해당 연구의 중간 결과물로 나온게 오른쪽의 시뮬레이터
> 
> 오른쪽의 시뮬레이터는 ADEX같은 행사에도 공군이 가져나온적이 있어서 보신적이 있는 분들도 계실수도 있음
> 
> 공군은 우리회사한테 저 AI 탑재된 시뮬레이터를 무상으로 받아가서 국방부장관이나 대통령 앞에서도 시연했으면서 한번도 우리회사 언급도 안해줌… 나쁜놈들임…


> 🔍 **시각 서술:** 대회소개 : 배경. 두 개의 뉴스 기사 스크린샷. (좌) '국방부 \'국방 AI 발전 TF 구성…ADD는 \'AI 조종사\' 개발' — 신태수 기자, 입력 2021.06.21, 본문 요지: 국방과학연구소(ADD)가 'AI 전투기 조종사' 개발에 착수, 국방부가 '국방 AI 발전 전담팀(태스크포스·TF)' 구성. 좌측 삽화는 헤드셋 낀 3D 인물들이 콘솔 앞에 앉은 이미지(© News1). (우, 노란 테두리 강조) '국방부 청사서 가상 전투기와 교전…데이터·인공지능 성과물 전시' — 허고운 기자, 2024.7.3. 사진 2장: 태극기 부착 헬멧·VR HMD를 쓴 조종사가 모의비행 시뮬레이터에 탑승해 시연하는 모습. 노란 화살표 라벨: '중간 개발 결과물을 활용한 훈련용 시뮬레이터'.


---

## Slide 7

대회소개 : 배경

어떤 국가 기관

＆

REALTIMEVISUAL

- AI Pilot ( 2020 ~ 2023)

- 국방과학연구소(ADD)와 REALTIMEVISUAL에서 진행한 프로젝트.

- 미국의 AlphaDogFight와 같은 컨셉의 프로젝트로 F16 전투기에 AI를 탑재하는 것을 목표로 하는 프로젝트

- 지식&규칙 기반 AI, 지도학습형 AI, 강화학습형 AI를 개발.

- 공군의 베테랑 파일럿, 공군사관학교의 훈련교관 파일럿들을 상대로

- 1차 교전 평가에서 90%의 승률 달성.

- 최종 교전 평가에서 100%의 승률 달성.

어떤 국가 기관

- 참가팀 여러분은 해당 프로젝트에서 진행중에 사용됐던 AI 개발 툴을 제공 받아

- 전투기 AI를 개발하고 상대를 탈락시키면 됩니다


**발표자 노트:**


> 우리나라에서 수행한 연구에 대해 자세하게 설명하면
> 미국보다 쪼금 늦게 시작했고 컨셉 자체는 미국의 연구 과제인
> Alpha Dog Fight와 동일한 컨셉으로 진행
> 
> 지식&규칙 기반 AI를 만들고
> 이 규칙 기반 AI를 학습하여 강화학습 AI를 만드는 프로세스
> 
> 뭐 지금까지 엄청 진부하고 지루한 설명이었을겁니다.
> 그래서 뭐 어쩌라고 하는 표정도 보이네요.
> 
> 그래서 바로 본론으로 넘어가자면 여러분은 리얼타임비쥬얼에서 진행한 프로젝트의 일부 부분을 제공받아 최선의 AI를 만들고 서로 죽이면 됩니다


> 🔍 **시각 서술:** 대회소개 : 배경. 기울어진 노란 박스 '어떤 국가 기관' & 빨간 대형 텍스트 'REALTIMEVISUAL'. 아래 설명 박스: 'AI Pilot ( 2020 ~ 2023) [어떤 국가 기관]와 REALTIMEVISUAL에서 진행한 프로젝트. 미국의 AlphaDogFight와 같은 컨셉의 프로젝트로 F16 전투기에 AI를 탑재하는 것을 목표로 하는 프로젝트. 지식&규칙 기반 AI, 지도학습형 AI, 강화학습형 AI를 개발. 공군의 베테랑 파일럿, 공군사관학교의 훈련교관 파일럿들을 상대로 1차 교전 평가에서 90%의 승률 달성. 최종 교전 평가에서 100%의 승률 달성.' 하단 노란 글씨: '참가팀 여러분은 해당 프로젝트에서 진행중에 사용됐던 AI 개발 툴을 제공 받아 전투기 AI를 개발하고 상대를 탈락시키면 됩니다'.


---

## Slide 8

대회소개 : AlphaDogfight? Dogfight?? 그게 뭔데?


**발표자 노트:**


> 일단 도그파이트란 전투기간 초근접 교전을 말합니다.
> 지금 보실 영상은 알파도그파이트의 영상의 일부이고 여러분이 수행할 도그파이트의 예시를 보여줍니다.
> F16을 제작한 록히드 마틴과 Heron이라는 스타트업 기업이
> F16 동역학 모델을 사용한 AI들을 이용한 교전을 하는 모습입니다.
> 
> 그리고 우승은 Heron이 차지 했습니다.
> 
> 여러분은 대충 이런 환경에서 교전을 하게 되고 오늘 목표가 이 시뮬레이션 환경까지 실행하여 규칙기반AI모델을 띄워보는겁니다


> 🔍 **시각 서술:** 대회소개 : AlphaDogfight? Dogfight?? 그게 뭔데? — 제목만 있는 섹션 전환 슬라이드(본문 없음).


---

## Slide 9

대회소개 : 그래서 뭘 해야하나?

- 각 참여팀은 REALTIMEVISUAL이 제공하는 AI 전투기 개발 환경을 통하여 AI 전투기 모델을 개발

- 각 참여팀의 AI 전투기들을 교전을 통해 가장 성능 좋은, 정확하게 말해 가장 잘싸우는 AI를 선발하는 대회

- 미국 DARPA의 Alpha Dog Fight 프로젝트와 국내에서 진행한 관련 프로젝트의 교전방식을 채용

- 하지만 학생들의 실력 및 개발 시간을 고려하여 난이도를 낮춘 방식으로 진행

- 8월말에 예선전을 통해 8팀 + 4팀을 선출

- 9월 중순에 토너먼트를 통해 1등팀을 결정

- 제공하는 AI 개발환경은 일정 부분이 열화, 제거된 상태로 제공


> 🔍 **시각 서술:** 대회소개 : 그래서 뭘 해야하나? — 텍스트 위주 슬라이드(별도 시각 요소 없음). 강조 색상: 'AI 전투기 모델을 개발'(빨강), '가장 잘싸우는 AI를 선발하는 대회'(파랑), '난이도를 낮춘 방식으로 진행'(초록), '제공하는 AI 개발환경은 일정 부분이 열화, 제거된 상태로 제공'(빨강 이탤릭).


---

## Slide 10

대회 룰 : 개요

- Perfect State Information(Ground-truth state information)

- 센서 오차, 탐지 지연, 노이즈, 가시성 제한 없이 시뮬레이터가 알고 있는 실제 정답, 상태값을 그대로 에이전트에게 제공

- 간단하게 말해서 나는(내 전투기는) 적의 실시간 위치, 자세, 속도를 제공 받음

- 순수하게 AI의 상황인지->전투기 조종 성능만을 평가

- Frame Rate 60Hz(DeltaTime : 0.016666)로 진행

- 0.016666초에 한번씩 계산을 하는 구조를 기본으로 진행. 교전 서버는 AI 클라이언트에게 60HZ 로 전장 정보를 전송

- 전장 정보를 받은 AI 클라이언트는 해당 정보를 활용하여 가장 적절한 판단을 수행하는 전투기 조종명령을 서버로 전송

- 네트워크 연결에 의한 응답시간이 아닌 순수 AI연산 과정으로 인한 응답시간이 0.1667 초를 넘어가는 경우 패널티 적용

- 여러분의 AI

- 상황인식,

- 최적의 행동 추론

- 명령값 생성 등

전장정보

- 교전

- 서버

- 접속

- 클라이언트

- 꼭 1/60초로 AI의 판단을 안내려도 괜찮지만

- 조종명령은 전장정보에 대한 답으로 꼭 60hz로 답해야함

조종명령

- 기총(전투기에 달린 기관총)만 사용하는 초근접 교전

- 미사일이 아닌 기총의 범위를 아주 러프하게 확률적으로 모의하는 방식을 사용

- 주어진 시간내에 더 많은 대미지를 입히거나 격추 시키면 승리


**발표자 노트:**


> 여러분들의 팀소개나 포부를 모두 읽어봤습니다.
> 거의 국방연구를 위한 열사들이 되어 계시던데..
> 아무튼 가끔 센서오차같은 내용이 나와서 확실하게 정하고 넘어갑니다.


> 🔍 **시각 서술:** 대회 룰 : 개요. 하단에 데이터 흐름 다이어그램: [교전 서버](보라 상자) ──전장정보(초록 화살표)──▶ [접속 클라이언트](빨강 상자) ──▶ [여러분의 AI](흰 상자: 상황인식, 최적의 행동 추론, 명령값 생성 등), 그리고 역방향으로 [여러분의 AI] ──▶ [접속 클라이언트] ──조종명령(노랑 화살표)──▶ [교전 서버]. 우측 주석: '꼭 1/60초로 AI의 판단을 안내려도 괜찮지만 조종명령은 전장정보에 대한 답으로 꼭 60hz로 답해야함'. (핵심 텍스트: Perfect State Information, Frame Rate 60Hz DeltaTime 0.016666, 응답시간 0.1667초 초과 시 패널티, 기총만 사용하는 초근접 교전.)


---

## Slide 11

대회 룰 : 교전 룰

- 교전 시간 200초동안 상대에게 더 많은 대미지를 입히거나

- 상대를 격추 시키면 승리

ㅠㅠ

교전 공간

1000ft 이하 고도 도달시 추락 처리

1000ft(약 300미터)

지면(해수면 고도 0ft)


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 앞서 말한것 처럼 상대를 격추, 최대한 많은 대미지를 주는것을 목표로함
> 
> 교전 공간은 해수면 고도 1000ft 이상, 1000ft 이하 고도 도달 시 추락 처리
> 
> 200초간 교전을 진행하고 더 많은 체력을 보유한 팀이 승리


> 🔍 **시각 서술:** 대회 룰 : 교전 룰. 상단에 파랑·빨강 F-16 실루엣 아이콘. 중앙 텍스트 '교전 시간 200초동안 상대에게 더 많은 대미지를 입히거나 상대를 격추 시키면 승리'. 하단 고도 다이어그램: 위쪽 하늘색 선 '교전 공간', 아래쪽 주황색 선 '지면(해수면 고도 0ft)', 그 사이 초록 양방향 화살표에 '1000ft(약 300미터)'. 교전 공간 선 부근에 빨간 X 표시된 적기 + 라벨 '1000ft 이하 고도 도달시 추락 처리'.


---

## Slide 12

대회 룰 : 교전 대미지 룰(AIP, AlphaDogFight)

- 적기의 중심을 나의 공격 범위 Cone안에 넣으면 대미지 발생

- 거리에 비례하여 더 높은 데미지가 발생함

전투기 1인칭 시점에서 공격 범위 단면

- Damage 판단용 HitBox Cone

- Damage 판단 거리 : 500ft ~ 3000ft

- LOS : 1(Degree) 이하

- 상대 비행기가 해당 범위안에 들어오면 거리 비례 Damage를 입음


> 🖼️ **[이미지 4개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 알파도그 파이트나 AIP에서 사용한 대미지 알고리즘
> 범위
> 거리 비례 대미지


> 🔍 **시각 서술:** 대회 룰 : 교전 대미지 룰(AIP, AlphaDogFight). 좌측 파란 기체의 기수에서 원뿔(cone)이 뻗어 우측 빨간 기체를 향함(원뿔은 apex 근처 분홍, 바깥쪽 연하늘). 초록 텍스트: '적기의 중심을 나의 공격 범위 Cone안에 넣으면 대미지 발생 / 거리에 비례하여 더 높은 대미지가 발생함'. 설명 박스: 'Damage 판단용 HitBox Cone / Damage 판단 거리 : 500ft ~ 3000ft / LOS : 1(Degree) 이하 / 상대 비행기가 해당 범위안에 들어오면 거리 비례 Damage'. 우측 원 안 기체 = '전투기 1인칭 시점에서 공격 범위 단면'. 하단 공식: d_wez = { 0 (r > 3000 ft); (3000−r)/2500 (500 ft ≤ r ≤ 3000 ft); 0 (r < 500 ft) }.


---

## Slide 13

1 : 2.72 : 5.34

개요 : 교전 대미지 룰(경진대회)

Los < 2°, 3500ft

Los < 3°, 4000ft

Los < 1°, 3000ft

Phase 2(100~150s)

Phase 1(0~100s)

Phase 3(150~200s)

- 교전 경과 시간에 따라 공격 성공 판정 방식이 추가

- -phase 1 : LOS < 1°, 500ft < Distance < 3000ft, 대미지 계수 1

- -phase 2 : LOS < 2°, 500ft < Distance < 3500ft, 대미지 계수 0.3

- -phase 3 : LOS < 3°, 500ft < Distance < 4000ft, 대미지 계수 0.1

- 하위 Phase에 적이 위치하는 경우 하위 phase의 대미지 적용

- Ex) Phase 3 상황에서 적기가 Phase 1의 범위 안에 있는 경우 Phase 1의 대미지 적용

- Damge Con 부피

- 1 : 6.36 : 21.37


**발표자 노트:**


> 여러분은 어린이 난이도로 진행함
> 따라서 시간에 따라 점점 공격 범위가 늘어남
> 대신 Phase1에 적기를 위치 시킨다면 Phase1의 대미지가 들어가는 형식
> 
> 어떻게든 여러분의 전투기가 공격을하고 무승부가 안나게 하기 위한 조치


> 🔍 **시각 서술:** 개요 : 교전 대미지 룰(경진대회). 겹친 3중 원뿔 다이어그램(안→밖): 'Los < 1°, 3000ft — Phase 1(0~100s)'(하늘색), 'Los < 2°, 3500ft — Phase 2(100~150s)'(보라), 'Los < 3°, 4000ft — Phase 3(150~200s)'(빨강). 텍스트: 교전 경과 시간에 따라 공격 성공 판정 방식이 추가. -phase 1: LOS<1°, 500ft<Distance<3000ft, 대미지 계수 1. -phase 2: LOS<2°, 500ft<Distance<3500ft, 대미지 계수 0.3. -phase 3: LOS<3°, 500ft<Distance<4000ft, 대미지 계수 0.1. 하위 Phase에 적이 위치하면 하위 phase의 대미지 적용(Ex: Phase 3 상황에서 적기가 Phase 1 범위 안이면 Phase 1 대미지 적용). 우하단: 'Damge Con 부피  1 : 6.36 : 21.37'.


---

## Slide 14

1 : 2.72 : 5.34

개요 : 교전 룰

Los < 2°, 3500ft

Los < 3°, 4000ft

Los < 1°, 3000ft

Phase 2(100~150s)

Phase 1(0~100s)

Phase 3(150~200s)

- 교전 경과 시간에 따라 공격 성공 판정 방식이 추가

- -phase 1 : LOS < 1°, 500ft < Distance < 3000ft, 대미지 계수 1

- -phase 2 : LOS < 2°, 500ft < Distance < 3500ft, 대미지 계수 0.3

- -phase 3 : LOS < 3°, 500ft < Distance < 4000ft, 대미지 계수 0.1

- 하위 Phase에 적이 위치하는 경우 하위 phase의 대미지 적용

- Ex) Phase 3 상황에서 적기가 Phase 1의 범위 안에 있는 경우 Phase 1의 대미지 적용

- Damge Con 부피

- 1 : 6.36 : 21.37


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 이것은 이미지로 위치에 따른 대미지를 표현한것


> 🔍 **시각 서술:** 개요 : 교전 룰 – 통합 픽셀 데미지 맵 (Phase 1 + Phase 2 + Phase 3). 중심선(LOS 0°) 기준 ±1°/±2°/±3° 각도 밴드로 나뉜 원뿔을 그레이스케일 픽셀맵으로 시각화(안쪽 Phase가 밝음=고데미지). 거리 눈금: r=0ft(Apex), 500ft(무데미지 끝), 3000ft, 3500ft, 4000ft(최대 거리). 밴드 라벨: Phase 1(LOS<1°) 500~3000ft 계수 1.0 / Phase 2(LOS<2°) 500~3500ft 계수 0.3 / Phase 3(LOS<3°) 500~4000ft 계수 0.1. 우선순위: Phase 1 > Phase 2 > Phase 3 (내부 Phase가 외부 Phase를 덮어씀). 데미지 계산 공식: 1) Phase 1(최우선) 500≤r≤3000 그리고 |θ|<1°: Damage = 1.0 × (3000−r)/2500. 2) Phase 2 500≤r≤3500 그리고 |θ|<2°: Damage = 0.3 × (3500−r)/3000. 3) Phase 3 500≤r≤4000 그리고 |θ|<3°: Damage = 0.1 × (4000−r)/3500. 4) 그 외(r<500 또는 |θ|≥3°): Damage = 0. 픽셀 변환: Gray = round(255 × Damage). 예시 변환값 표 [Damage | Gray(0~255)]: 0|0, 0.10|26, 0.30|77, 1.00|255. 하단 그레이스케일 범례(0=Damage 0, 26=0.10, 77=0.30, 255=1.00). r: 전방 거리(ft, 중심선 방향), θ: LOS 각도(°, 중심선 기준). 각 픽셀은 (r, θ) 위치의 데미지를 그레이 값으로 표현.


---

## Slide 15

개요 : 교전 시나리오 룰(예선)

2000ft ~ 3000ft

1 Round

AlphaDogFight 의 교전 방식을 채용

- 단판으로 진행되며 정확한 수치(시작거리, 고도, 속력 등)는 차후 공개

- #컷오프가 적용되는 경우 컷오프에서도 동일한 룰 적용

- 컷오프 방법 : 예상보다 너무 많은 참여팀이 지원하여 현재 방법에 대한 논의중

- 제 1안 ) 경진대회 운영팀에서 만든 적당한 성능의 모델을 이기는 팀만 예선 진출

- 제 2안 ) 경진대회 운영팀에서 만든 적당한 성능의 모델을 각 참여팀에게 전달하고 예선 참여 여부를 각 팀에서 스스로 결정


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 제 2안으로 거의 결정됨


> 🔍 **시각 서술:** 개요 : 교전 시나리오 룰(예선). 상단 초록 테두리 박스 '1 Round': 파랑 기체 ↔(2000ft~3000ft, 초록 화살표)↔ 빨강 기체, 우측 'AlphaDogFight 의 교전 방식을 채용'. 텍스트: 단판으로 진행되며 정확한 수치(시작거리, 고도, 속력 등)는 차후 공개 / #컷오프가 적용되는 경우 컷오프에서도 동일한 룰 적용. 컷오프 방법(참여팀 과다로 논의중): 제1안) 운영팀이 만든 적당한 성능의 모델을 이기는 팀만 예선 진출, 제2안) 그 모델을 각 참여팀에 전달하고 예선 참여 여부를 각 팀이 스스로 결정.


---

## Slide 16

개요 : 교전 시나리오 룰(본선)

Base

2000ft ~ 3000ft

1~3 Round

1,2,3 라운드는 AlphaDogFight 의 교전 방식을 채용

3라운드 까지 동률 또는 승부가 안났다면 운명을 건 마지막 한타 싸움 진행

- 3라운드 이내에 승부가 갈리지 않은 경우

- 서로 마주본 상태에서 정면 교전 수행

4 Round+

10000ft 이상


> 🖼️ **[이미지 4개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개요 : 교전 시나리오 룰(본선). 상단 초록 박스 'Base 1~3 Round': 파랑↔(2000ft~3000ft)↔빨강, '1,2,3 라운드는 AlphaDogFight 의 교전 방식을 채용'. 빨간 텍스트: '3라운드 까지 동률 또는 승부가 안났다면 운명을 건 마지막 한타 싸움 진행'. 하단 빨강 박스 '4 Round+': 파랑↔(10000ft 이상)↔빨강, '3라운드 이내에 승부가 갈리지 않은 경우 서로 마주본 상태에서 정면 교전 수행'.


---

## Slide 17

개요 : 대회 일정

- 컷 오프 진행

- 대회 운영위원회가 지정한 기체를 대상으로 승리한 팀만 예선으로 진출

- 예선

- -스위스 리그 형태로 진행

- -단판 경기

- -최소 3회 이상의 교전

- -8개의 상위팀 + 4팀의 와일드카드팀 선발

- 본선 조별 라운드

- -3 : 3 : 3 : 3 으로 나눠진 리그

- -3판 2선승제, 풀리그 진행

- -조별 상위 2팀 본선 진출

#와일드 카드 팀은 출신 학교가 겹치지 않는 팀만을 대상으로 하고 대학당 최대 1팀만 가능

참여팀 자체 컷 오프

- 본선

- -8강으로 진행되는 토너먼트

- -5판 3선승제

대회 규칙 및 일정은 대회 사정에 의해 변경 될 수 있습니다


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개요 : 대회 일정. 4단계 프로세스 카드(좌→우, 화살표 연결). 01 컷오프 진행: '대회 운영위원회가 지정한 기체를 상대로 승리한 팀만 예선으로 진출'(하단 라벨 '참여팀 자체 컷 오프'). 02 예선: 스위스 리그 형태로 진행 / 단판 경기 / 최소 3회 이상의 교전 / 상위 8팀 + 와일드카드 4팀 선발 (주석: '와일드카드 팀은 출신 학교가 겹치지 않는 팀을 대상으로 하며, 대학당 최대 1팀 선발'). 03 본선 조별 라운드: 12개 팀을 4개 조(3팀씩)로 구성 / 3판 2선승제 풀리그 진행 / 조별 상위 2팀 본선 진출. 04 본선: 8강 토너먼트 진행 / 5판 3선승제. 하단 빨강: '대회 규칙 및 일정은 대회 사정에 의해 변경 될 수 있습니다'.


---

## Slide 18

대회 환경 소개 : 개발 환경

Behavior Tree개발환경

- 역할

- -Behavior Tree(BT) 를 통한 지식/규칙 기반 AI를 개발하는 환경

- 결과물

- -DLL, XML

- 개발언어 및 라이브러리

- -C++, CPP Behavior Tree(https://www.behaviortree.dev)

학습환경

- 역할

- -강화학습기반 AI 학습 환경

- -AI 교전 테스트 환경

- 결과물

- -학습 CheckPoint

- 개발언어 및 라이브러리

- -Python

교전 뷰어

- 역할

- -학습환경에서 AI 교전 테스트를 가시화를 해주는 툴


> 🔍 **시각 서술:** 대회 환경 소개 : 개발 환경. 3개 블록. [Behavior Tree 개발환경](보라 라벨) — 역할: Behavior Tree(BT)를 통한 지식/규칙 기반 AI를 개발하는 환경 / 결과물: DLL, XML / 개발언어 및 라이브러리: C++, CPP Behavior Tree(https://www.behaviortree.dev). [학습환경](하늘색) — 역할: 강화학습기반 AI 학습 환경, AI 교전 테스트 환경 / 결과물: 학습 CheckPoint / 개발언어 및 라이브러리: Python. [교전 뷰어](초록) — 역할: 학습환경에서 AI 교전 테스트를 가시화를 해주는 툴.


---

## Slide 19

대회 환경 소개 : 대회 경기 환경

교전 서버

- 역할

- -대회용 시뮬레이터

- -팀원, 팀간의 온라인 교전용 시뮬레이터

- -전투기의 물리 연산

- -공격 대미지 연산

교전 서버 접속기

- 역할

- -참여 팀이 개발한 AI 모델을 탑재하여 교전 서버에 접속하는 역할

- -교전 서버에서 동작하는 전투기 물리 모델을 원격 조종하는 역할


> 🔍 **시각 서술:** 대회 환경 소개 : 대회 경기 환경. 2개 블록. [교전 서버](보라) — 역할: 대회용 시뮬레이터 / 팀원, 팀간의 온라인 교전용 시뮬레이터 / 전투기의 물리 연산 / 공격 대미지 연산. [교전 서버 접속기](하늘색) — 역할: 참여 팀이 개발한 AI 모델을 탑재하여 교전 서버에 접속하는 역할 / 교전 서버에서 동작하는 전투기 물리 모델을 원격 조종하는 역할.


---

## Slide 20

대회 환경 소개 : 개발 환경 개요

Behavior Tree개발환경

- -지식/규칙 기반 모델, BehaviorTree기반의 모델 사용하여 개발

- -지식/규칙 기반 모델을 통해 강화 학습 학습 상대로 활용 가능

- Behavior Tree AI 모델

- DLL & XML

- 강화 학습 방법에 따라 필요 없을 수도 있음

- 교전서버

- 클라이언트

교전서버

개발된 최종 AI 모델

교전 테스트

학습환경

- 교전 로그

- 뷰어

AI 전투기들의 교전 상황 가시화

학습

-교전 테스트를 통해 현재 개발/학습 중인 AI 모델의 성능 테스트

- 강화 학습 AI 모델

- CheckPoint

-강화학습을 통해 AI 생성

웬만하면 지식/규칙 AI모델과 강화학습 AI 모델을 2트랙으로 동시 개발하는 것을 추천 드립니다


> 🔍 **시각 서술:** 대회 환경 소개 : 개발 환경 개요. 전체 파이프라인 다이어그램. [Behavior Tree 개발환경](노랑 상자, 주석: 'Behavior Tree AI 모델 DLL & XML — 강화 학습 방법에 따라 필요 없을 수도 있음') → [학습환경](하늘 상자, 자기 순환 화살표 '학습' + 하단 '강화 학습 AI 모델 CheckPoint', 주석 '-강화학습을 통해 AI 생성') → '교전 테스트'(초록 라벨 'AI 전투기들의 교전 상황 가시화') → [교전 로그 뷰어](초록 상자). 우측: '개발된 최종 AI 모델' → [교전서버 클라이언트](하늘 상자) ↔ [교전서버](보라 상자). 상단 텍스트: 지식/규칙 기반 모델·BehaviorTree기반 모델 사용하여 개발 / 지식/규칙 기반 모델을 통해 강화 학습 학습 상대로 활용 가능 / 교전 테스트를 통해 현재 개발·학습 중인 AI 모델의 성능 테스트. 하단 빨강: '웬만하면 지식/규칙 AI모델과 강화학습 AI 모델을 2트랙으로 동시 개발하는 것을 추천 드립니다'.


---

## Slide 21

대회 환경 소개 : 대회 경기 환경

교전 서버

- 시뮬레이션 서버

- 물리 연산 및 대미지 연산 처리

CMD 요청에 대한 응답

CMD 요청에 대한 응답

3

2

2

- Plane2

- Roll Command

- Pitch Command

- Yaw Command

- Throttle Command

- Plane1

- Roll Command

- Pitch Command

- Yaw Command

- Throttle Command

교전 서버

1

교전 서버 접속기

교전 서버 접속기

Team AAI Model

Team BAI Model

전투기들의 위치, 자세, 속도 정보

- CMD 요청 메세지

- 0.01666초마다(60hz) 요청


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 대회 환경 소개 : 대회 경기 환경(교전 흐름 다이어그램). 중앙 상단 [물리 연산 및 데미지 연산 처리 = 교전 서버] 안에 파랑·빨강 F-16. 좌측 [Plane1] 패널: Roll Command / Pitch Command / Yaw Command / Throttle Command. 우측 [Plane2] 동일. 하단 좌 [교전 서버 접속기 — Team A AI Model](파랑 타원), 하단 우 [교전 서버 접속기 — Team B AI Model](빨강 타원). 번호 화살표: ① 전투기들의 위치·자세·속도 정보 (CMD 요청 메세지, 0.01666초마다(60hz) 요청), ② CMD 요청에 대한 응답(양측), ③ 서버의 물리/데미지 연산.


---

## Slide 22

대회 환경 소개 : 대회 경기 환경

교전 서버

교전 서버 접속기

- 전투기들의 위치, 자세, 속도 정보

- Plane1 : Location(X,Y,Z), Rotation(Roll, Pitch, Yaw), Velocity(u,v,w)

- Plane2 : Location(X,Y,Z), Rotation(Roll, Pitch, Yaw), Velocity(u,v,w)

여러분이 만들AI 모델

60hz 로 통신

- CMD

- Roll Command

- Pitch Command

- Yaw Command

- Throttle Command

F16 동역학(JSBSIM)

- -교전 서버 접속기는 교전 서버로 부터 전투기들의 정보를 수신

- -참여팀은 수신한 정보를 개발한 AI에게 전달하여 교전 서버에게 CMD 메시지를 송신

- -교전 서버는 수신한 CMD 값을 전투기 동역학 모델에 전달하여 1frame 연산

- 기본적으로 교전 서버 접속기는 제공.

- 개발하는 팀의 AI에 맞게 참여 팀이 접속기를 직접 개발/변형하여 사용하는 것도 네트워크 프로토콜만 유지한다면 허용

- 하지만 대회 당일 2번 이상 네트워크 불안정을 보이거나 네트워크 연결이 불가능한 경우 탈락 처리


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 대회 환경 소개 : 대회 경기 환경(프로토콜 상세). 좌 [교전 서버](빨강·파랑 기체) ↔ 우 [교전 서버 접속기 = 여러분이 만들 AI 모델]. 서버→AI 방향 데이터: '전투기들의 위치, 자세, 속도 정보 / Plane1 : Location(X,Y,Z), Rotation(Roll, Pitch, Yaw), Velocity(u,v,w) / Plane2 : (동일)'. AI→서버 방향: CMD = Roll Command / Pitch Command / Yaw Command / Throttle Command. '60hz 로 통신'. 텍스트: 교전 서버 접속기는 교전 서버로부터 전투기 정보를 수신 / 참여팀은 수신 정보를 AI에게 전달하여 교전 서버에게 CMD 메시지 송신 / 교전 서버는 수신한 CMD 값을 전투기 동역학 모델에 전달하여 1frame 연산. 하단: 기본적으로 교전 서버 접속기는 제공. 빨강: 접속기를 직접 개발/변형해도 네트워크 프로토콜만 유지하면 허용, 단 대회 당일 2번 이상 네트워크 불안정·연결 불가 시 탈락 처리.


---

## Slide 23

- 특강 1일차:

- #Orientation

- - 대회 소개

- - 교전 룰 소개

- - 개발 환경 & 대회 경기 환경 소개

- #전투기 AI에 대하여

- #Behavior Tree 기반 AI

- #실습


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 목차(특강 1일차) 재등장 — '02 전투기 AI에 대하여' 항목이 초록 밑줄로 강조된 섹션 전환 슬라이드. (좌측 원형 전투기 아이콘, 01 Orientation / 02 전투기 AI에 대하여 / 03 Behavior Tree 기반 AI / 04 실습.)


---

## Slide 24

인간의 전투기 조종

외부 자극

외부 자극

인간 인지/판단 능력

판단

전투기 조종 하드웨어

조작

Stick(Roll,Pitch)

Throttle

Rudder(Yaw)

전투기의 기동

전투기 동체 특성

위치, 자세, 속도, 가속도 ,등등


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 인간의 전투기 조종. 좌측 흐름도: [외부 자극](주황) → [인간 인지/판단 능력](하늘, 라벨 '판단') → [전투기 조종 하드웨어](Stick(Roll,Pitch) 빨강 · Rudder(Yaw) 노랑 · Throttle 파랑, 라벨 '조작') → [전투기 동체 특성](분홍, 라벨 '전투기의 기동'). 우측: [외부 자극](주황) → 뇌 아이콘(파랑) → F-16 실제 콕핏 사진 → 항공기 3축 다이어그램(Roll(φ) → X_I(North), Pitch(θ) → Y_I(East), Yaw(ψ) → Z_I(Down)).


---

## Slide 25

AI 전투기 모델의 구조

상대 비행기의 위치, 자세, 속도

AI

- AI : 자신의 정보와 상대의 정보를 입력하여 이기기 위한 최적의 조종값을 생성

- 입력값

- 자신의 비행기 정보

- 상대 비행기의 정보

- 출력값

- 조종값(Roll, Pitch, Yaw, Throttle)

- 조종값(CMD) :

- Roll, Pitch, Yaw, Throttle

내 위치, 자세, 속도

JSBSIM

- 동역학 모델 : 조종값을 입력받아 비행기의 비행 역학을 시뮬레이션

- 입력값

- Roll, Pitch, Yaw 조종값

- Throttle 조정값

- 출력값

- 위치, 자세, 속도 등의 전투기 시뮬레이션 정보

AI 전투기 모델


> 🔍 **시각 서술:** AI 전투기 모델의 구조. 순환 다이어그램: '상대 비행기의 위치, 자세, 속도'(하늘) → [AI](보라) → '조종값(CMD): Roll, Pitch, Yaw, Throttle'(초록) → [JSBSIM](분홍) → '내 위치, 자세, 속도'(빨강, 다시 AI로 순환). 우측 설명: AI = 자신의 정보와 상대의 정보를 입력하여 이기기 위한 최적의 조종값을 생성 (입력값: 자신의 비행기 정보 / 상대 비행기의 정보, 출력값: 조종값 Roll,Pitch,Yaw,Throttle). 동역학 모델 = 조종값을 입력받아 비행기의 비행 역학을 시뮬레이션 (입력값: Roll,Pitch,Yaw 조종값 / Throttle 조정값, 출력값: 위치·자세·속도 등의 전투기 시뮬레이션 정보). 하단 라벨: 'AI 전투기 모델'.


---

## Slide 26

AI 전투기 모델 종류

AI

- Advanced

- (Hybrid)

- 여러 AI를 혼합하여 사용

- Ex) Rule & Reinforcement

Reinforcement Learning AI

Rule-based AI

Supervised Learning AI

- 장점 :

- -고점이 높다

- -도메인 지식이 부족해도 가능(like Heron)

- 단점 :

- -학습 방법에 따라 이미 완성된 AI(Rule base)

- 가 필요할 수도 있다(학습 스파링 상대)

- -시간이 졸라 많이 필요하다

- -성능 좋은 PC가 필요할 수 있다

- 장점 :

- -성능적 저점이 높다(이 대회 한정 기준)

- -비교적 빠르게 성능을 보임(이 대회 한정 기준)

- -개발 난이도 쉬움(이 대회 한정 기준)

- 단점 :

- -고점이 상대적으로 낮다

- -도메인지식(전투기 교전)에 대한 지식 필요

- 장점 :

- -좋은 데이터를 통한 학습만 잘 시키면

- 어느정도 성능이 보장됨

- 단점 :

- -결국 원본의 카피 또는 하위호환 모델

- -학습의 정답 데이터가 될 데이터가 필요하다

- (P3D, DCS같은데서 로그를 가져와서 가공해서 사용 가능할지도?)

계룡대 공군본부 건물에 있음


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** AI 전투기 모델 종류. [AI]에서 4갈래 트리: Rule-based AI / Supervised Learning AI / Reinforcement Learning AI / Advanced(Hybrid). — Rule-based AI 장점: 성능적 저점이 높다(이 대회 한정 기준), 비교적 빠르게 성능을 보임(이 대회 한정 기준), 개발 난이도 쉬움(이 대회 한정 기준); 단점: 고점이 상대적으로 낮다, 도메인지식(전투기 교전)에 대한 지식 필요. — Reinforcement Learning AI 장점: 고점이 높다, 도메인 지식이 부족해도 가능(like Heron); 단점: 학습 방법에 따라 이미 완성된 AI(Rule base)가 필요할 수도 있다(학습 스파링 상대), 시간이 졸라 많이 필요하다, 성능 좋은 PC가 필요할 수 있다. — Advanced(Hybrid): 여러 AI를 혼합하여 사용 Ex) Rule & Reinforcement. (Supervised Learning AI 박스의 장·단점 텍스트 일부는 VR 시뮬레이터 사진에 가려져 부분만 보임: 장점 '좋은 데이…', 단점 '결국 원본S…, 학습의 정…(P3D, DCS같은…)'.) 중앙 하단 사진: VR HMD 착용 군인들의 모의비행훈련 시뮬레이터 + 빨강 캡션 '계룡대 공군본부 건물에 있음'.


---

## Slide 27

Rule Based 기반 모델

- Behavior Tree 기반 지식&규칙 기반 AI

- 역할

  - -현재의 상황에 가장 알맞은 목표점(VP : VirtualPoint)을 생성

  - -현재 상황에 가장 알맞은 Throttle을 생성

- 목표점을 바라 보도록 만드는 동역학 제어기 #가속도 유도 제어기 참고

- 역할

  - -Behavior Tree를 통해 생성된 VP를 바라보도록 만드는 제어값을 생성

JSBSIM 동역학 제어기는 AIP에서 사용한 제어기의 성능 열화 버전을 기본 제공합니다

Rule-Based AI 전투기 모델


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Rule Based 기반 모델. 좌측 순환 다이어그램: '상대 비행기의 위치, 자세, 속도'(보라) → [Behavior Tree](초록) → 'VirtualPoint: Location, Target Speed'(초록, 순환) → [JSBSIM Controller](하늘) → 'Cmd: roll, pitch, yaw' + 'Throttle Cmd' → [JSBSIM](분홍) → '위치, 자세, 속도'(순환). 우상단 스크린샷: 'BehaviorTree.CPP 4.6 — The C++ library to build Behavior Trees. Batteries included. Tutorials' + 예제 트리(Sequence / Fallback / EnterRoom / CloseDoor / IsDoorOpen / Retry attempts=5 / OpenDoor). 우측 설명: 'Behavior Tree 기반 지식&규칙 기반 AI — 역할: 현재의 상황에 가장 알맞은 목표점(VP: VirtualPoint)을 생성, 현재 상황에 가장 알맞은 Throttle을 생성'. '목표점을 바라 보도록 만드는 동역학 제어기 #가속도 유도 제어기 참고 — 역할: Behavior Tree를 통해 생성된 VP를 바라보도록 만드는 제어값을 생성'. 빨강 밑줄 이탤릭: 'JSBSIM 동역학 제어기는 AIP에서 사용한 제어기의 성능 열화 버전을 기본 제공합니다'. 라벨: 'Rule-Based AI 전투기 모델'.


---

## Slide 28

Rule Based 기반 모델

Rule-Based AI 전투기 모델


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Rule Based 기반 모델(기하 상세). 좌측은 s27과 동일한 Behavior Tree→JSBSIM Controller→JSBSIM 순환도. 우측 두 이미지: (상) 항공기 3축 다이어그램 위에 빨강·보라·노랑 벡터가 우상단 '목표점(VP: VirtualPoint)' 빨간 점을 향함. (하) VP 유도 기하 설명도 — 'Forward Vector를 법선 벡터, N 미터 거리에 떨어져 있는 점을 지나는 평면', '적기를 해당 평면으로 Projection 시킨 점', Alpha(초록 각도), Right Vector, 'RightVector에 Projection 시킨 점'(주황), 'VP: 목적지'(빨강), Beta(노랑), LOS(하늘), Up Vector, 실사 F-16과 하늘 배경.


---

## Slide 29

제어기(JSBSIM Controller)의 역할

BehaviorTree

제어기JSBSIM Controller

동역학

- VP : 목적점

- Vector(X, Y, Z)

- 목적점을 바라보기 위한

- 제어값 Roll,  Pitch, Yaw

Throttle

- 실제 AIP 프로젝트에서 사용한 제어기의 열화 버전.

- 성능의 고점을 보기 위해선 제어기의 수정 필요


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 제어기(JSBSIM Controller)의 역할. 3블록 흐름: [Behavior Tree](초록) ──'VP: 목적점 Vector(X, Y, Z)'──▶ [제어기 JSBSIM Controller](파랑) ──'목적점을 바라보기 위한 제어값 Roll, Pitch, Yaw'──▶ [동역학](빨강). 하단 경로로 Behavior Tree ──'Throttle'──▶ 동역학. 하단 경고 박스(! 아이콘): '실제 AIP 프로젝트에서 사용한 제어기의 열화 버전. 성능의 고점을 보기 위해선 제어기의 수정 필요'.


---

## Slide 30

학습 기반 모델의 구조

상대 비행기의 위치, 자세, 속도

AI

- AI : 자신의 정보와 상대의 정보를 입력하여 조종 최적의 조종값을 생성

- 입력값

- 자신의 비행기 정보

- 상대 비행기의 정보

- 출력값

- 조종값(Roll, Pitch, Yaw, Throttle)

- 조종값(CMD) :

- Roll, Pitch, Yaw, Throttle

내 위치, 자세, 속도

JSBSIM

- 동역학 : 조종값을 입력받아 비행기의 비행 역학을 시뮬레이션

- 입력값

- Roll, Pitch, Yaw 조종값

- Throttle 조정값

- 출력값

- 위치, 자세, 속도 등의 전투기 시뮬레이션 정보


> 🔍 **시각 서술:** 학습 기반 모델의 구조. s25와 동일한 순환 다이어그램(제목만 '학습 기반'): '상대 비행기의 위치, 자세, 속도' → [AI] → '조종값(CMD): Roll, Pitch, Yaw, Throttle' → [JSBSIM] → '내 위치, 자세, 속도'(순환). 우측 설명 박스: AI = 자신의 정보와 상대의 정보를 입력하여 (조종) 최적의 조종값을 생성; 동역학 = 조종값을 입력받아 비행기의 비행 역학을 시뮬레이션 (입출력은 s25와 동일).


---

## Slide 31

Advanced 모델 예시

Reinforcement Learning AI전술판단

Reinforcement Learning AI전술판단 2

Behavior Tree전술 판단 1

Behavior Tree전술 판단 1

Behavior Tree전술 판단

Reinforcement Learning AI전투기 조종

Reinforcement Learning AIThrottle 관리

JSBSIMController

JSBSIMController

JSBSIMController

JSBSIM

JSBSIM

JSBSIM

JSBSIM

- 여러 조합의 방법을 사용 가능, 무슨 수를 써서라도 접속기에 붙이기만 하면 됩니다.

- 참가팀 여러분의 익숙한 AI 방식, 생각하기에 좋아 보이는 방향성 등

- 가장 성능 좋을 것 같은 방향으로 준비하세요


> 🔍 **시각 서술:** Advanced 모델 예시. BT·RL·JSBSIM Controller·JSBSIM을 조합한 4가지 구성 예: (1) [Behavior Tree 전술 판단] → [Reinforcement Learning AI 전투기 조종] → [JSBSIM]. (2) [Behavior Tree 전술 판단 1] + [Reinforcement Learning AI 전술판단 2] → [JSBSIM Controller] → [JSBSIM]. (3) [Reinforcement Learning AI 전술판단] → [JSBSIM Controller] → [JSBSIM]. (4) [Behavior Tree 전술 판단 1] → [JSBSIM Controller] + [Reinforcement Learning AI Throttle 관리] → [JSBSIM]. 하단 텍스트: '여러 조합의 방법을 사용 가능, 무슨 수를 써서라도 접속기에 붙이기만 하면 됩니다. 참가팀 여러분의 익숙한 AI 방식, 생각하기에 좋아 보이는 방향성 등 가장 성능 좋을 것 같은 방향으로 준비하세요.'


---

## Slide 32

- 특강 1일차:

- #Orientation

- - 대회 소개

- - 교전 룰 소개

- - 개발 환경 & 대회 경기 환경 소개

- #전투기 AI에 대하여

- #Behavior Tree 기반 AI

- #실습


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 목차(특강 1일차) 재등장 — '03 Behavior Tree 기반 AI' 항목이 초록 밑줄로 강조된 섹션 전환 슬라이드.


---

## Slide 33

Behavior Tree ???

- AI가 뭘 해야 할지 정하는 일종의 할 일 리스트 & 선택기

- -AI가 지금 현 상황에서 뭘 해야하는지 결정하도록 하는 구조

- -단순하게 if문으로도 충분히 개발 가능하지만 유지보수가 힘들어지기 때문에 Behavior Tree를 사용

- -해야 할 일, 상태 확인 등을 노드로 구현

기억

중간고사 다 쳤나??

오늘 무슨 요일이지?

교수님이 칼을 들고 협박했던 기억 상기


> 🔍 **시각 서술:** Behavior Tree ??? — 텍스트: 'AI가 뭘 해야 할지 정하는 일종의 할 일 리스트 & 선택기 / -AI가 지금 현 상황에서 뭘 해야하는지 결정하도록 하는 구조 / -단순하게 if문으로도 충분히 개발 가능하지만 유지보수가 힘들어지기 때문에 Behavior Tree를 사용 / -해야 할 일, 상태 확인 등을 노드로 구현'. 하단 유머 예시 BT 다이어그램: [질문](빨강)→선택사항→ 두 갈래: '오늘 평일인가?'와 '주말/공강 인가?'. '오늘 평일인가?'→선택사항→ '시험 기간인가?'(→공부) / '시험기간 끝인가?'(→술). '주말/공강 인가?'→선택사항→ '교수님이 오늘 학교 나와라고 칼들고 협박했는가?'(→눈물..) / 'Happy~'. 우측 [기억] 상자(BlackBoard 은유)가 조건들에 정보를 공급: '중간고사 다 쳤나??', '오늘 무슨 요일이지?', '교수님이 칼을 들고 협박했던 기억 상기'.


---

## Slide 34

AIP Behavior Tree Tutorial

Unreal Engine Behavior Tree의 구성

XML

C++ Node Class

Unreal Engine Behavior Tree

C++ Behavior Tree

- 굳이 Unreal Engine의 Behavior Tree를 먼저 설명하는 이유

- UnrealEngine의 Behavior Tree가 훨씬 직관적이고 세분화된 노드로 구성됐기 때문에

- 설계를 UnrealEngine 형식으로 하고 개발을 CppBehaviorTree 형태로 하는 것이 좋음


> 🖼️ **[이미지 4개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


**발표자 노트:**


> 저는 언리얼엔진 개발자이기도 하고
> 프로젝트의 초기 개발을 언리얼엔진 BT를 이용해서 개발을 했기때문에
> 언리얼 엔진으로 이미 완성이된 BT를 학습에 활용하기 위하여 CPP 기반 트리로 재구현했습니다.


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial — Unreal Engine Behavior Tree의 구성. 좌: Unreal Engine Behavior Tree 노드 그래프 스크린샷. 우: C++ Behavior Tree 스크린샷(XML + C++ Node Class 코드). 두 이미지 사이 화살표. 하단 파란 텍스트: '굳이 Unreal Engine의 Behavior Tree를 먼저 설명하는 이유 — UnrealEngine의 Behavior Tree가 훨씬 직관적이고 세분화된 노드로 구성됐기 때문에 설계를 UnrealEngine 형식으로 하고 개발을 CppBehaviorTree 형태로 하는 것이 좋음'.


---

## Slide 35

AIP Behavior Tree Tutorial

Unreal Engine Behavior Tree의 구성

Tree

Unreal Engine에서 제공하는 Behavior Tree 제작 툴,	사고 회로

BlackBoard

Behavior Tree 가 정보를 저장하는 공간, 모든 노드에서 접근 가능, 기억

Selector

- 자손 노드중 성공한 노드를 실행, if else 문

- 왼(위)쪽부터 차례대로 검사하여 하나라도 성공하면 더 이상 더 진행하지 않음

Sequence

- 자손 노드를 모두 실행, if, if, if 문

- 왼(위)쪽부터 차례대로 검사하여 하나라도 실패하면 더 이상 더 진행하지 않음

Flow Control Node

- Task

- Node

객체의 행위 자체를 수행하는 노드, 이 프로젝트에서는 VP를 생성하는 역할

- Decorator

- Node

다른 노드들에 붙어서 실행 조건을 확인하는 노드, 트리의 조건문, if 문의 조건이라고 보면됨

ServiceNode

트리가 지나가는 경로 도중에 실행되는 노드, 주로 상태 업데이트를 위해 씀

Content Node


**발표자 노트:**


> AIP의 BT가 UE의 방식을 따르고 있기 때문에 설명


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial — Unreal Engine Behavior Tree의 구성(노드 종류 표). [Tree](주황): Unreal Engine에서 제공하는 Behavior Tree 제작 툴, '사고 회로'. [BlackBoard](하늘): Behavior Tree가 정보를 저장하는 공간, 모든 노드에서 접근 가능, '기억'. — Flow Control Node: [Selector](회색): 자손 노드중 성공한 노드를 실행, if else 문. 왼(위)쪽부터 차례대로 검사하여 하나라도 성공하면 더 이상 진행하지 않음. [Sequence](회색): 자손 노드를 모두 실행, if, if, if 문. 왼(위)쪽부터 차례대로 검사하여 하나라도 실패하면 더 이상 진행하지 않음. — Content Node: [Task Node](보라): 객체의 행위 자체를 수행하는 노드, 이 프로젝트에서는 VP를 생성하는 역할. [Decorator Node](파랑): 다른 노드에 붙어서 실행 조건을 확인하는 노드, 트리의 조건문(if 문의 조건). [Service Node](초록): 트리가 지나가는 경로 도중에 실행되는 노드, 주로 상태 업데이트를 위해 씀.


---

## Slide 36

AIP Behavior Tree Tutorial : Develop Tree

Unreal Engine Behavior Tree의 구성

BlackBoard

Root

Update Distance

Data Update

- Current State

- #적기와 거리 : 650m

- #적기에 대한 시야각(LOS) : 4.3

- Update

- LOS

Selector

Distance < 1000m

- Distance

- > 1000m

Selector

Lag Pursuit

LOS <= 1

LOS > 1

Pure Pursuit

Lag Pursuit


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial : Develop Tree — Unreal Engine Behavior Tree 예시 트리. 구조: Root(빨강) → [Update Distance / Update LOS](초록 Service) + Selector(회색). Selector의 두 자식: (좌) DECO 'Distance < 1000m'(파랑) + Selector → [DECO 'LOS <= 1' → Pure Pursuit / DECO 'LOS > 1' → Lag Pursuit], (우) DECO 'Distance > 1000m'(파랑) → Lag Pursuit(보라 Task). 우측 [BlackBoard] ← 'Data Update'로 상태 저장. Current State: '#적기와 거리 : 650m', '#적기에 대한 시야각(LOS) : 4.3'.


---

## Slide 37

AIP Behavior Tree Tutorial : Develop Tree

Unreal Engine Behavior Tree의 구성

BlackBoard

Root

1

Distance Update : 650m

Update Distance

Los Update : 4.3

- Update

- LOS

Selector

Distance : 650m

2

Distance < 1000m

- Distance

- >= 1000m

Selector

Lag Pursuit

Los : 4.3

3

4

LOS <= 1

LOS > 1

Los : 4.3

Pure Pursuit

Lag Pursuit


> 🔍 **시각 서술:** s36과 같은 Unreal BT 트리의 실행 추적(노란 하이라이트, 번호 ①~④). Update Distance → 'Distance Update : 650m', Update LOS → 'Los Update : 4.3'을 BlackBoard에 기록. 이후 Distance : 650m → 'Distance < 1000m'(②) 성공 경로로 진입, LOS : 4.3 → 'LOS <= 1'(③, 빨간 강조 = 4.3>1 이므로 실패) / 'LOS > 1'(④) 성공 → 결과적으로 Lag Pursuit 실행.


---

## Slide 38

AIP Behavior Tree Tutorial : Develop Tree

C++ Behavior Tree의 구성

- 라이브러리 참고는

- https://www.behaviortree.dev/

Tree

XML, 사고 회로

BlackBoard

Behavior Tree 가 정보를 저장하는 공간

Fallback

Unreal BT의 Selector 노드, 자손 노드중 성공한 노드를 실행, if else 문

Sequence

자손 노드를 모두 실행, if, if, if 문

- Decorator

- Node

트리의 조건문, 자식 노드의 실행 결과값을 판단 및 변환하는 노드

Flow Control Node

- Task

- Node

ActionNode

- 서비스 노드와 같은 역할 구분이 사라짐

- 트리의 말단 부분. 객체의 행위 자체를 구현하는 부분

ServiceNode

Content Node


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial : Develop Tree — C++ Behavior Tree의 구성(노드 종류). 라이브러리 참고: https://www.behaviortree.dev/. [Tree](주황): XML, 사고 회로. [BlackBoard](하늘): Behavior Tree가 정보를 저장하는 공간. — Flow Control Node: [Fallback](회색): Unreal BT의 Selector 노드, 자손 노드중 성공한 노드를 실행, if else 문. [Sequence](회색): 자손 노드를 모두 실행, if, if, if 문. [Decorator Node](파랑): 트리의 조건문, 자식 노드의 실행 결과값을 판단 및 변환하는 노드. — Content Node: [Task Node](보라) + [Service Node](초록) → [Action Node](보라): '서비스 노드와 같은 역할 구분이 사라짐. 트리의 말단 부분. 객체의 행위 자체를 구현하는 부분'.


---

## Slide 39

AIP Behavior Tree Tutorial : Develop Tree

C++ Behavior Tree의 구성

BlackBoard

Root

Sequence

Update Distance

- Update

- LOS

Fallback

Sequence

Sequence

DECO_ Distance < 1000m

Fallback

- DECO_ Distance

- > 1000m

Lag Pursuit

Sequence

Sequence

- Current State

- #적기와 거리 : 650m

- #적기의 상대적 위치(LOS) :4.3

DECO_LOS <= 1

Pure Pursuit

DECO_ LOS > 1

Lag Pursuit


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial : Develop Tree — C++ Behavior Tree 예시 트리(Unreal 트리를 CppBT 형식으로 변환). 구조: Root → Sequence → [Update Distance / Update LOS / Fallback]. Fallback → 두 Sequence: (좌) Sequence → [DECO_ 'Distance < 1000m' + Fallback → [Sequence(DECO_LOS <= 1 / Pure Pursuit) · Sequence(DECO_ LOS > 1 / Lag Pursuit)]], (우) Sequence → [DECO_ 'Distance > 1000m' / Lag Pursuit]. 우측 [BlackBoard]. Current State: '#적기와 거리 : 650m', '#적기의 상대적 위치(LOS) :4.3'.


---

## Slide 40

AIP Behavior Tree Tutorial : Develop Tree

C++ Behavior Tree의 구성

BlackBoard

Root

1

Sequence

2

3

4

Update Distance

- Update

- LOS

Fallback

5

Distance: 650m

Sequence

Sequence

Los : 4.3

6

7

DECO_ Distance < 1000m

Fallback

- DECO_ Distance

- > 1000m

Lag Pursuit

8

10

Sequence

Sequence

조건 실패

11

12

9

DECO_LOS <= 1

Pure Pursuit

DECO_ LOS > 1

Lag Pursuit


> 🔍 **시각 서술:** s39와 같은 C++ BT 트리의 실행 추적(노란 하이라이트, 번호 ①~⑫). DECO_LOS <= 1 노드에 빨간 '조건 실패' 표시(LOS 4.3 > 1). 우측 BlackBoard 값: Distance: 650m, Los: 4.3.


---

## Slide 41

AIP Behavior Tree Tutorial : Develop Tree

C++ Behavior Tree의 구성


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** AIP Behavior Tree Tutorial : Develop Tree — C++ Behavior Tree의 구성. 좌: CppBT 트리 다이어그램(빨강·초록 영역 오버레이로 XML과 매핑). 우: 대응 XML 코드. XML 요지: <root main_tree_to_execute="MainTree"> <BehaviorTree ID="MainTree"> <Sequence> <SelectTarget name="SelectTarget" BB="{BB}"/> <DirectionVectorUpdate name="DirectionVectorUpdate" BB="{BB}"/> <DistanceUpdate name="DistanceUpdateService" BB="{BB}"/> <Fallback> <Sequence> <DECO_DistanceCheck name="DistanceCheck" UpDown="Less" Distance="1000" BB="{BB}"/> <Fallback> <Sequence> <DECO_LOS_Check name="DECO_LOS_Check" UpDown="Less" Distance="1.0" BB="{BB}"/> <Pure name="Pure" BB="{BB}"/> </Sequence> <Sequence> <DECO_LOS_Check name="DECO_LOS_Check" UpDown="Greater" Distance="1.0" BB="{BB}"/> <Lag name="Lag" BB="{BB}"/> </Sequence> </Fallback> </Sequence> <Sequence> <DECO_DistanceCheck name="DistanceCheck" UpDown="Greater" Distance="1000" BB="{BB}"/> <Lag name="Lag" BB="{BB}"/> </Sequence> </Fallback> </Sequence> </BehaviorTree> </root>.


---

## Slide 42

- 특강 1일차:

- #Orientation

- - 대회 소개

- - 교전 룰 소개

- - 개발 환경 & 대회 경기 환경 소개

- #전투기 AI에 대하여

- #Behavior Tree 기반 AI

- #실습

- -개발환경 설치하기

- -Behavior Tree 만들어보기

- -학습환경에 넣고 테스트 해보기

- -교전 클라이언트에 넣고 교전 서버와 연동해보기


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 목차(특강 1일차) — '04 실습' 강조 섹션 전환. 04 실습 하위 항목: -개발환경 설치하기 / -Behavior Tree 만들어보기 / -학습환경에 넣고 테스트 해보기 / -교전 클라이언트에 넣고 교전 서버와 연동해보기.


---

## Slide 43

개발환경 설치하기


> 🔍 **시각 서술:** 개발환경 설치하기 — 제목만 있는 섹션 전환 슬라이드.


---

## Slide 44

설치 링크 OR QR 코드

- 다운 받은 압축 파일을 원하는 위치에 풀어주세요

- 이 PPT에서는 바탕화면에 AIP라는 폴더를 만들어서 해당 위치에 설치를 합니다

- Ex) C:\Users\[윈도우 유저네임]\Desktop\AIP


> 🔍 **시각 서술:** 설치 링크 OR QR 코드. 텍스트: '다운 받은 압축 파일을 원하는 위치에 풀어주세요. / 이 PPT에서는 바탕화면에 AIP라는 폴더를 만들어서 해당 위치에 설치를 합니다. / Ex) C:\Users\[윈도우 유저네임]\Desktop\AIP'. (실제 링크/QR 이미지는 슬라이드에 표시되지 않음.)


---

## Slide 45

개발환경 설치하기

Behavior Tree 개발 툴

교전 접속기 & 학습 환경

교전 서버


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 — 파일 탐색기 스크린샷(바탕 화면 > AIP, 8개 항목). 항목과 주석: [AIP_DCS](빨강 박스 = 'Behavior Tree 개발 툴'), bin(파일 폴더, 2026-05-18 오후 3:06), [DogFightEnv](초록 박스 = '교전 접속기 & 학습 환경'), PropertySheets(파일 폴더, 2026-05-18 오후 2:42), [Windows](보라 박스 = '교전 서버', 오후 9:57), Anaconda3-2025.12-2-Windows-x86_6…(응용 프로그램, 2026-05-18 오후 10:27, 1,172,541…KB), VisualStudioSetup.exe(응용 프로그램, 2025-10-29 오전 1:24, 4,358KB), VSCodeUserSetup-x64-1.120.0.exe(응용 프로그램, 2026-05-18 오후 10:21, 153,493KB).


---

## Slide 46

개발환경 설치하기 : Anaconda, VSCode, Visual Studio  설치

V143이 없다면 다음 과정을 통해 V143설치

개별구성요소

워크로드


> 🖼️ **[이미지 6개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 : Anaconda, VSCode, Visual Studio 설치. (상) Anaconda3 2024.10-1 Setup 스크린샷 2장 — 'Select Installation Type: ● Just Me (recommended)', 'Advanced Installation Options: ☑ Create shortcuts / ☑ Add Anaconda3 to my PATH environment variable(NOT recommended…) / ☑ Register Anaconda3 as my default Python 3.12 / ☑ Clear the package cache upon completion'. (하) 'V143이 없다면 다음 과정을 통해 V143 설치'. 워크로드: 'C++를 사용한 데스크톱 개발(MSVC, Clang, CMake 또는 MSBuild 등 …)'. 개별구성요소: '☑ 최신 v143 빌드 도구용 C++ ATL(x86 및 x64)', '☑ MSVC v143 - VS 2022 C++ x64/x86 빌드 도구(최신)'.


---

## Slide 47

개발환경 설치하기 : Anaconda  환경 설정

- 다음 명령어를 통해 aip라는 가상환경을 Anaconda에 생성

- conda create -n aip python=3.11

- 이 명령어를 통해 aip라는 가상환경이 python 3.11버전으로 생성

Anaconda Prompt 실행


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 : Anaconda 환경 설정. (좌) 'Anaconda Prompt 실행' — 시작 검색 스크린샷. (우) Anaconda Prompt 창: '(base) C:\Users\Codemist>conda create -n aip python=3.11'. 텍스트: '다음 명령어를 통해 aip라는 가상환경을 Anaconda에 생성 — conda create -n aip python=3.11 / 이 명령어를 통해 aip라는 가상환경이 python 3.11버전으로 생성'.


---

## Slide 48

개발환경 설치하기 : Anaconda  환경 설정

VS code를 실행하고 프로젝트 루트를 압축푼프로젝트위치\DogFightEnv\Release 로 설정

방법 1) Vscode에서 Expoler->Open Folder-> 압축푼프로젝트위치\DogFightEnv\Release

방법 2) 압축푼프로젝트위치\DogFightEnv\Release 폴더 열고 폴더 빈공간을 오른쪽 클릭해서 Code(으)로 열기

방법 2

방법 1


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 : Anaconda 환경 설정. 텍스트: 'VS code를 실행하고 프로젝트 루트를 [압축푼프로젝트위치]\DogFightEnv\Release 로 설정. 방법 1) Vscode에서 Expoler→Open Folder→ …\DogFightEnv\Release. 방법 2) …\DogFightEnv\Release 폴더 열고 폴더 빈공간을 오른쪽 클릭해서 Code(으)로 열기'. 스크린샷: (방법1) VS Code 'Open Folder' + 폴더 선택 창, (방법2) Release 폴더 탐색기(내용: __pycache__, aircraft, artifacts, assets, engine, experiments, logs, scripts, src, student, tools, AIP_DCS_base.dll, AIP_DCS_ownship.dll, AIP_DCS_target.dll, DogFightEnvWrapper.py, FighterSim.py) + 우클릭 메뉴 'Code(으)로 열기'.


---

## Slide 49

개발환경 설치하기 : Anaconda  환경 설정

- Powershell로 생성 될수도 있음.

- 동작이 잘 안되는 경우가 있음

V자(아래방향표시)버튼을 눌러 command prompt 터미널을 실행

위치 확인


> 🖼️ **[이미지 3개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 : Anaconda 환경 설정. VS Code Terminal 메뉴 스크린샷(New Terminal / Split Terminal / Run Task… 등). 터미널 패널: 'PS C:\Users\Codemist\Desktop\AIP\DogFightEnv\Release>' (라벨 '위치 확인'). 빨강 주석: 'Powershell로 생성 될수도 있음. 동작이 잘 안되는 경우가 있음'. 라벨: 'V자(아래방향표시)버튼을 눌러 command prompt 터미널을 실행'. cmd 터미널: 'Microsoft Windows [Version 10.0.26200.8457] … C:\Users\Codemist\Desktop\AIP\DogFightEnv\Release>'. 터미널 종류 드롭다운: powershell / cmd.


---

## Slide 50

개발환경 설치하기 : Anaconda  환경 설정

- 해당 터미널에서 다음 명령어 실행

- Conda activate aip

- 앞으로의 학습환경&교전환경 접속기를 사용할땐 이 명령어를 무조건 실행해야함. 생성한 가상환경을 실행하는 명령어

- 지금까지 똑바로 따라했다면 다음과 비슷한 문구가 뜰것

밑줄과 같이 (aip)라는 표시가 뜨면 성공

- 다음 명령어를 추가로 실행하여 가상환경에 프로젝트에 필요한 라이브러리 설치

- python -m pip install -r requirements.txt

- 설치가 완료 됐다면 가상환경 설치는 완료

- python -c "import JSBSimWrapper; print('ok')" 명령어로 설치 완료 상태 테스트


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** 개발환경 설치하기 : Anaconda 환경 설정. 텍스트: '해당 터미널에서 다음 명령어 실행 — Conda activate aip'. '앞으로의 학습환경&교전환경 접속기를 사용할땐 이 명령어를 무조건 실행해야함. 생성한 가상환경을 실행하는 명령어'. 성공 시 프롬프트: '(aip) C:\Users\Codemist\Desktop\AIP\DogFightEnv\Release>' (초록 주석: '밑줄과 같이 (aip)라는 표시가 뜨면 성공'). '다음 명령어를 추가로 실행하여 가상환경에 프로젝트에 필요한 라이브러리 설치 — python -m pip install -r requirements.txt'. '설치가 완료 됐다면 가상환경 설치는 완료'. 설치 확인: python -c "import JSBSimWrapper; print('ok')".


---

## Slide 51

간단한 Behavior Tree 만들어보기

- Anaconda 설치 및 환경 설정을 하는 동안

- VisualStudio 를 설치했다고 믿겠습니다..


> 🔍 **시각 서술:** 간단한 Behavior Tree 만들어보기 — 섹션 전환 슬라이드. 파란 농담 텍스트: 'Anaconda 설치 및 환경 설정을 하는 동안 VisualStudio 를 설치했다고 믿겠습니다..'.


---

## Slide 52

Behavior Tree 만들어보기 : 기존 컨셉 설명

- #AIP 구조에서는 Unreal 구조를 따랐기 때문에 같은 기능을 Action Node를 통해 구현함

- 굳이 안따라도 상관없고 더 좋은 구조가 있다고 생각한다면 그 구조대로 만들기를 바람

Unreal Content Nodes

- Task

- Node

객체의 행위 자체를 수행하는 노드, 이 프로젝트에서는 VP를 생성하는 역할

- Decorator

- Node

다른 노드들에 붙어서 실행 조건을 확인하는 노드, 트리의 조건문, if 문의 조건이라고 보면됨

ServiceNode

트리가 지나가는 경로 도중에 실행되는 노드, 주로 상태 업데이트를 위해 씀

ActionNode

Task, Service, Decorator 의 역할을 구현하여 사용


**발표자 노트:**


> 이건 제가 사용한 방법이지 정답은 아닙니다
> 그냥 여러분이 하고 싶은 방향대로 하는게 정답입니다


> 🔍 **시각 서술:** Behavior Tree 만들어보기 : 기존 컨셉 설명. 텍스트: '#AIP 구조에서는 Unreal 구조를 따랐기 때문에 같은 기능을 Action Node를 통해 구현함 / 굳이 안따라도 상관없고 더 좋은 구조가 있다고 생각한다면 그 구조대로 만들기를 바람'. Unreal Content Nodes: [Task Node](보라)=객체의 행위 자체를 수행(이 프로젝트에서는 VP를 생성하는 역할), [Decorator Node](파랑)=실행 조건을 확인(트리의 조건문, if 문의 조건), [Service Node](초록)=경로 도중 실행(주로 상태 업데이트). ↑ 화살표로 → [Action Node](보라) = 'Task, Service, Decorator 의 역할을 구현하여 사용'.


---

## Slide 53

Behavior Tree 만들어보기

C++ Behavior Tree Node를 추가하고 사용해보기

실습 순서

노드 Class 생성

Factory 등록

Tree에 추가

Run Tree

Tree XML에서 사용

- Test전장서버 접속

- 테스트 교전

C++ Class로 구현된 Action Node 생성

생성한 노드를 Behavior Tree에 등록


> 🔍 **시각 서술:** Behavior Tree 만들어보기 : C++ Behavior Tree Node를 추가하고 사용해보기. 실습 순서 4단계 흐름: [노드 Class 생성](초록, 'C++ Class로 구현된 Action Node 생성') → [Factory 등록](보라, '생성한 노드를 Behavior Tree에 등록') → [Tree에 추가](하늘, 'Tree XML에서 사용') → [Run Tree](흰, 'Test / 전장서버 접속 / 테스트 교전').


---

## Slide 54

Behavior Tree Tutorial : Create Node

Action Node 생성

프로젝트 설치 위치\ADF_BT_Tool\AIP_DCS\BehaviorTree\BT_Content\Task

헤더 이름은 Task_Pure 로 설정

프로젝트 설치 위치에서 프로젝트를 열고 솔루션 탐색기-> 추가 -> 새항목 -> 헤더(.h) -> 파일이름 원하는거(여기선 Task_Pure) -> 생성 위치 설정(Task 폴더)

- 똑같은 과정으로 .cpp 파일도 생성

- Task 노드라서 Task폴더에 생성한것, Decorator나 Service는 해당 폴더에 생성하는 것을 추천


> 🖼️ **[이미지 5개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : Create Node — Action Node 생성. 스크린샷 흐름: AIP_DCS 폴더 → BehaviorTree/Debug/Geometry/x64/AIP_DCS.sln/AIP_DCS.vcxproj → Visual Studio 솔루션 탐색기(AIP_DCS 프로젝트, BehaviorTree > Decorator/Service/Task, action_node.cpp/.h, always_failure, always_success, any.hpp) → 우클릭 '추가(D)' → '새 항목(W)' → '새 항목 추가: FileName.cpp, ☑ 모든 템플릿 표시(T), 추가(A)'. 경로: '프로젝트 설치 위치\ADF_BT_Tool\AIP_DCS\BehaviorTree\BT_Content\Task'. '헤더 이름은 Task_Pure 로 설정'. 텍스트: '프로젝트 설치 위치에서 프로젝트를 열고 솔루션 탐색기→ 추가 → 새항목 → 헤더(.h) → 파일이름 원하는거(여기선 Task_Pure) → 생성 위치 설정(Task 폴더). 똑같은 과정으로 .cpp 파일도 생성. Task 노드라서 Task폴더에 생성한것, Decorator나 Service는 해당 폴더에 생성하는 것을 추천'.


---

## Slide 55

Behavior Tree Tutorial : Create Node

C++ Behavior Tree Node의 기본 구조

Task_Empty를 복붙해서 작성 하면 편함


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : Create Node — C++ Behavior Tree Node의 기본 구조(Task_Pure.h / Task_Pure.cpp 코드 스크린샷). Task_Pure.h: '#pragma once / #include "../../behaviortree_cpp_v3/action_node.h" / #include "../../behaviortree_cpp_v3/bt_factory.h" / #include "../../../Geometry/Vector3.h" / #include "../Functions.h" / #include "../BlackBoard/CPPBlackBoard.h" / using namespace BT; / namespace Action { class Task_Pure : public SyncActionNode { private: public: Task_Pure(const std::string& name, const NodeConfiguration& config) : SyncActionNode(na…) { } ~Task_Pure() { } static PortsList providedPorts(); NodeStatus tick() override; }; }'. Task_Pure.cpp: '#include "Task_Pure.h" / PortsList Action::Task_Pure::providedPorts() { return { InputPort<CPPBlackBoard*>("BB") }; } / NodeStatus Action::Task_Pure::tick() { Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB"); Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian; (*BB)->VP_Cartesian = TargetLocation; return NodeStatus::SUCCESS; }'. 하단: 'Task_Empty를 복붙해서 작성 하면 편함'.


---

## Slide 56

Behavior Tree Tutorial : Add Node

생성한 노드를 BT Factory에 등록

TaskNodes.h

추가

CPPBehaviorTree.cpp

추가


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : Add Node — 생성한 노드를 BT Factory에 등록. TaskNodes.h: '#pragma once / #include "Task_Empty.h" / #include "Task_Pure.h"'(마지막 줄에 '추가' 표시). CPPBehaviorTree.cpp: '/* 노드 입력 : 구현해둔 노드들을 Factory 객체에 입력해주는 과정. 새로 생성한 노드를 여기에 입력해주세요!!!!! */' 이어서 Factory.registerNodeType 목록: SelectTarget, DistanceUpdate, CheckSight, AngleOffUpdate, DirectionVectorUpdate, AspectAngleUpdate, DECO_BFMCheck, DECO_DistanceCheck, EFSF_Selector("SelectEFSF"), Task_Empty, 그리고 마지막에 'Factory.registerNodeType<Action::Task_Pure>("Task_Pure");'('추가' 표시).


---

## Slide 57

Behavior Tree Tutorial : Add Node

생성한 노드를 BT Factory에 등록

CPPBehaviorTree.cpp

이름 불일치

- Rule.xml을 복사하여 CPPBehaviorTree.cpp 에서 설정한 이름, 여기서는 Rule_forTraining.xml 라는 이름으로 Rule.xml 을 복사해 주세요

- Rule_forTraining.xml => 차후 제출시 구분을 위해서 직접 개발에 들어갈 땐 반드시 여러분의 팀이름과 같이 유니크한 이름으로 바꿔주세요

- 빌드를 수행하여 생성되는 DLL와 CPPBehaviorTree.cpp 에서 설정한 XML 파일은 세트 입니다.

- 프로젝트를 진행하시면서 버전별로 DLL과 XML의 이름을 잘 설정하여 버전 관리를 잘하시기를 바랍니다.


> 🖼️ **[이미지 2개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : Add Node — 트리 파일 지정. CPPBehaviorTree.cpp: '//파일로 트리 구조 정의 //자신의 팀 이름으로 xml 파일 만들어서 입력해주세요!!!!!! (Rule_forTraining.xml은 예시입니다) / tree = Factory.createTreeFromFile("./Rule_forTraining.xml");'. 우측 폴더에는 'Rule.xml'만 존재 → 빨간 화살표 '이름 불일치'. 텍스트: 'Rule.xml을 복사하여 CPPBehaviorTree.cpp 에서 설정한 이름(여기서는 Rule_forTraining.xml)으로 복사해 주세요'. 빨강: 'Rule_forTraining.xml => 차후 제출시 구분을 위해서 직접 개발에 들어갈 땐 반드시 여러분의 팀이름과 같이 유니크한 이름으로 바꿔주세요'. '빌드를 수행하여 생성되는 DLL와 CPPBehaviorTree.cpp 에서 설정한 XML 파일은 세트 입니다. 버전별로 DLL과 XML의 이름을 잘 설정하여 버전 관리를 잘하시기를 바랍니다'.


---

## Slide 58

Behavior Tree Tutorial : Tree에 추가

생성한 노드를 BT Factory에 등록

Rule_forTraining.xml

복사해서 새롭게 만든 Rule_forTraing.xml을 수정

<Task_Pure name=“Task_Pure” BB={“BB”}/> 으로 변경

<Task_Pure name=“Task_Pure” BB={“BB”}/> 으로 변경


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : Tree에 추가 — Rule_forTraining.xml 수정. XML 코드: '<root main_tree_to_execute = "MainTree"> <BehaviorTree ID="MainTree"> <Sequence> <!-- EF 부분 트리--> <Sequence> <SelectTarget name="SelectTarget" BB="{BB}"/> <DirectionVectorUpdate name="DirectionVectorUpdate" BB="{BB}"/> <DistanceUpdate name="DistanceUpdateService" BB="{BB}"/> <CheckSight name="CheckSight" BB="{BB}"/> <AngleOffUpdate name="AngleOffUpdate" BB="{BB}"/> <AspectAngleUpdate name="AspectAngleUpdate" BB="{BB}"/> <Fallback> <Sequence> <DECO_DistanceCheck name="DistanceCheck" UpDown="Greater" Distance="2000" BB="{BB}"/> <Task_Empty name="Task_Empty" BB="{BB}"/> </Sequence> <Sequence> <DECO_DistanceCheck name="DistanceCheck" UpDown="Less" Distance="2000" BB="{BB}"/> <Task_Empty name="Task_Empty" BB="{BB}"/> </Sequence> </Fallback> </Sequence> </Sequence> </BehaviorTree> </root>'. 노란 주석 2곳: 각 <Task_Empty …/> 를 '<Task_Pure name="Task_Pure" BB={"BB"}/> 으로 변경'. 우측: '복사해서 새롭게 만든 Rule_forTraing.xml을 수정'.


---

## Slide 59

Behavior Tree Tutorial : 빌드

- 빌드를 하면

- 압축푼프로젝트위치/bin/debug.x64 폴더에 dll파일이 생성됨

DLL 파일과 트리 XML 파일을 학습환경(접속기) 폴더에 넣으면 Behavior Tree 개발하기 완료

압축푼프로젝트위치\DogFightEnv\Release

Vscode : run_unreal_inference.py


> 🖼️ **[이미지 4개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree Tutorial : 빌드. (상) 빌드 산출물 폴더: AIP_DCS.dll(빨강 박스), AIP_DCS.exp, AIP_DCS.lib, AIP_DCS.pdb. 텍스트: '빌드를 하면 압축푼프로젝트위치/bin/debug.x64 폴더에 dll파일이 생성됨'. '(빨강)DLL 파일과 트리 (초록)XML 파일을 학습환경(접속기) 폴더에 넣으면 Behavior Tree 개발하기 완료'. (하) 대상 폴더 AIP_DCS/bin/DogFightEnv/PropertySheets/Windows/Rule.xml/Rule_forTraing.xml(초록 박스) → '압축푼프로젝트위치\DogFightEnv\Release'. Vscode run_unreal_inference.py 코드: 'RELEASE_ROOT = ROOT / DEFAULT_BT_DLL = RELEASE_ROOT / "AIP_BASE.dll" / DEFAULT_BT_RULE_XML = RELEASE_ROOT / "Rule_forTraining.xml"'.


---

## Slide 60

Behavior Tree 기반 AI 테스트 해보기

1) 교전 서버 실행 : 같이 강의를 듣고 있는 팀원 중 아무나 한 명

2) 원하는 시나리오 설정(이번에는 HABFM 선택)

둘의 순서는 상관없지만 무조건 필요 과정

3) OpenServer 버튼 클릭

- 4) Vscode(학습환경&접속기)에서 접속기 실행

- 터미널에서 다음 명령어 실행

- python run_unreal_inference.py --mode bt --team-name TestLaptop --server-ip 123.456.789.529 --server-port 9999

팀 이름

교전 서버 IP

- 최소 2명 필요(서버+접속기, 접속기)

- 앞에 스위치 허브를 설치해뒀습니다. 서로서로 테스트를 해보시기 바랍니다.

- 지금부터 노드와 트리를 스스로 만들어서 테스트를 진행해주세요

- 문제가 있는 사람은 조교나 강사들을 호출해주세요


> 🖼️ **[이미지 1개]** (렌더 슬라이드 기준 시각 서술은 아래 참조)


> 🔍 **시각 서술:** Behavior Tree 기반 AI 테스트 해보기. 절차: 1) 교전 서버 실행 : 같이 강의를 듣고 있는 팀원 중 아무나 한 명. 2) 원하는 시나리오 설정(이번에는 HABFM 선택). 3) OpenServer 버튼 클릭. (2,3은 '둘의 순서는 상관없지만 무조건 필요 과정'). 4) Vscode(학습환경&접속기)에서 접속기 실행 — 터미널에서 실행: 'python run_unreal_inference.py --mode bt --team-name TestLaptop --server-ip 123.456.789.529 --server-port 9999' (팀 이름 = TestLaptop, 교전 서버 IP = 123.456.789.529 [예시 placeholder]). 안내: '최소 2명 필요(서버+접속기, 접속기). 앞에 스위치 허브를 설치해뒀습니다. 서로서로 테스트를 해보시기 바랍니다.' 보라 텍스트: '지금부터 노드와 트리를 스스로 만들어서 테스트를 진행해주세요 / 문제가 있는 사람은 조교나 강사들을 호출해주세요'. 우상단: 교전 뷰어 실행 화면 썸네일.


---

## Slide 61

대회 Discord 운영

- 교전 서버 및 개발 환경에 수정이 있는 경우 빠르게 공지하기 위하여 Discord 채널을 운영하려고 합니다.

- 참가팀간 스크림을 위한 채널도 설정해뒀으니 많은 참여 바랍니다.

- 채널에 참가 시 권한 대기방에 자신의 팀 이름과 본인의 이름을 적어주시길 바랍니다.

https://discord.gg/RagK27Av

대충 7일정도 있다가 초대 링크 만료됨..


> 🔍 **시각 서술:** 대회 Discord 운영. 텍스트: '교전 서버 및 개발 환경에 수정이 있는 경우 빠르게 공지하기 위하여 Discord 채널을 운영하려고 합니다. / 참가팀간 스크림을 위한 채널도 설정해뒀으니 많은 참여 바랍니다. / 채널에 참가 시 권한 대기방에 (파랑)자신의 팀 이름과 (초록)본인의 이름을 적어주시길 바랍니다.' 대형 링크: https://discord.gg/RagK27Av. 우하단 작은 글씨: '대충 7일정도 있다가 초대 링크 만료됨..' (즉 이 초대 링크는 만료되었을 가능성 높음).
