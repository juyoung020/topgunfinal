# -*- coding: utf-8 -*-
"""[학생 파일] 컷오프(EasyModeCutoff) 행동트리 복원본.

출처: C:\\cutoff_model\\unreal_bt_client.exe (MinGW GCC 13, BehaviorTree.CPP v3).
디버그 심볼은 없고 RTTI 가 남아 있어 클래스 이름 -> type_info -> vtable -> tick() 으로
코드를 짚었다. 함수 경계는 .pdata(RUNTIME_FUNCTION) 5,903개에서 얻었다.
트리 XML 은 exe 안에 그대로 들어 있다(16,945 B).

좌표 규약: env 는 NED. state[0:3] = N, E, D(아래 양수), state[3:6] = roll, pitch, yaw(rad),
state[6:9] = 동체 속도. 컷오프 원본은 위쪽 양수 좌표라 D 를 뒤집어 넣는다.
"""
from __future__ import annotations

import math

import numpy as np

# ── exe 실측 상수 ──────────────────────────────────────────────────────────
SIGHT_CONE_DEG = 95.739166      # CheckSight: LOS 가 이 값 이하이면 "본다"
AIM_LOS_DEG = 10.0              # Pure: 조준모드 진입 LOS
AIM_RANGE_M = 1100.0            # Pure: 조준모드 진입 거리
LEAD_TIME_S = 0.12              # Pure 조준모드: 적 위치 앞 선행 시간
LAG_OFFSET_M = -40.0            # Lag: 적 뒤쪽 오프셋 계수
GUID_INTEG_N = 20               # guide_normal: 이동평균 링버퍼 길이
GUID_PITCH_DIV = 7.5            # guide_normal: 적분항 나눗수
GUID_PITCH_CAP = 0.25           # guide_normal: 적분항 상한
GUID_ROLL_DIV = 6.0             # guide_normal: 각도 -> 롤 나눗수
GUID_PITCH_MAX = 1.5            # guide_normal: 피치 합 상한
GUID_BANK_REF = 90.0            # guide_normal: 뱅크 정규화 기준
SC_DT = 0.016666666             # SpeedControl EMA 계수(=dt, +0x08)

# 국면 enum (Superior::tick 실측)
OBFM, HABFM, DBFM, DETECTING, SCISSORS = 0, 1, 2, 3, 4
PHASE_NAME = {0: "OBFM", 1: "HABFM", 2: "DBFM", 3: "DETECTING", 4: "SCISSORS"}


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])


def _dcm(roll, pitch, yaw):
    """기체 -> 월드(NED) 회전행렬. 열이 각각 nose / right / down 축."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array([
        [cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
        [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
        [-sp,     sr * cp,                cr * cp],
    ])


def _axes(roll, pitch, yaw):
    """위쪽 양수 좌표에서의 nose / right / up 축 (입력은 라디안)."""
    r = _dcm(roll, pitch, yaw)
    nose = np.array([r[0, 0], r[1, 0], -r[2, 0]])
    right = np.array([r[0, 1], r[1, 1], -r[2, 1]])
    up = -np.array([r[0, 2], r[1, 2], -r[2, 2]])
    return _unit(nose), _unit(right), _unit(up)


def frame_env(state):
    """학습 env 의 51칸 상태. state[2] = D(아래 양수), **자세는 도(deg)**,
    state[6:9] = 동체 속도. (my_observation.py 가 state[ROLL..YAW] 에 _D2R 을 곱한다)"""
    s = np.asarray(state, dtype=np.float64)
    nose, right, up = _axes(math.radians(float(s[3])), math.radians(float(s[4])),
                            math.radians(float(s[5])))
    speed = float(np.linalg.norm(s[6:9])) if s.size > 8 else 0.0
    return {"pos": np.array([s[0], s[1], -s[2]]), "nose": nose, "right": right,
            "up": up, "vel": nose * speed, "speed": speed}


def frame_server(state):
    """교전서버 경로(plane_info_to_state). state[2] = 고도(위 양수), 자세 deg,
    state[6:9] = 월드 속도. [MOD-ZUP] 과 같은 규약이다."""
    s = np.asarray(state, dtype=np.float64)
    nose, right, up = _axes(math.radians(float(s[3])), math.radians(float(s[4])),
                            math.radians(float(s[5])))
    vel = np.array([s[6], s[7], s[8]])
    return {"pos": np.array([s[0], s[1], s[2]]), "nose": nose, "right": right,
            "up": up, "vel": vel, "speed": float(np.linalg.norm(vel))}


_frame = frame_env


class Blackboard:
    """exe 의 블랙보드 필드(오프셋 실측)를 그대로 옮긴 것."""

    def __init__(self):
        self.dist = 0.0            # +0x170
        self.los = 0.0             # +0x180  내 기수와 적 방향의 각
        self.los_target = 0.0      # +0x184  적 기수와 내 방향의 각
        self.ao = 0.0              # +0x188  AngleOff
        self.aa = 0.0              # +0x18c  AspectAngle
        self.closure = 0.0         # +0x1a0
        self.in_sight = False      # +0x1dc
        self.in_sight_tgt = False  # +0x1dd
        self.aiming = False        # +0x1de
        self.phase = DETECTING     # +0x1e4
        self.aim = np.zeros(3)     # +0x78..0x88
        # TurnCheck @0x1400636b0 — 0.5초마다 yaw 차분을 갱신
        self.t = 0.0               # +0x00 시뮬 시각
        self.turn_last = 0.0       # +0x1a0
        self.prev_yaw_me = 0.0     # +0x190
        self.prev_yaw_foe = 0.0    # +0x194
        self.dyaw_me = 0.0         # +0x198
        self.dyaw_foe = 0.0        # +0x19c
        # DECO_MergeCheck @0x140038520 — 머지 순간 스냅샷을 5초 유지
        self.merge_timer = 0.0     # +0x1b0
        self.merge_dist = 0.0      # +0x1b4
        self.merge_los = 0.0       # +0x1c8
        self.merge_los_tgt = 0.0   # +0x1cc


class CutoffBT:
    """컷오프 BT 한 기체분. step() 이 [roll, pitch, yaw, throttle] 을 돌려준다."""

    def __init__(self):
        self.bb = Blackboard()
        self._ring20 = [0.0] * GUID_INTEG_N
        self._i20 = 0
        self._ring60 = [0.0] * 60
        self._i60 = 0
        self._ema = 0.0   # SpeedControl +0x178
        self._lead_scale = float(np.random.randint(2, 10))   # Lead 리드 배율 BB+0xf18 = rand()%8+2
        self._thr_scale = 1.0
        self._thr_fixed = None

    def reset(self):
        self.bb = Blackboard()
        self._ring20 = [0.0] * GUID_INTEG_N
        self._i20 = 0
        self._ring60 = [0.0] * 60
        self._i60 = 0
        self._ema = 0.0   # SpeedControl +0x178
        self._lead_scale = float(np.random.randint(2, 10))   # Lead 리드 배율 BB+0xf18 = rand()%8+2
        self._thr_scale = 1.0
        self._thr_fixed = None

    # ── 갱신 노드 (DistanceUpdate / CheckSight / AngleOffUpdate / …) ──────
    def _update(self, me, foe):
        bb = self.bb
        rel = foe["pos"] - me["pos"]
        bb.dist = float(np.linalg.norm(rel))
        u = _unit(rel)
        bb.los = math.degrees(math.acos(float(np.clip(np.dot(me["nose"], u), -1.0, 1.0))))
        bb.los_target = math.degrees(
            math.acos(float(np.clip(np.dot(foe["nose"], -u), -1.0, 1.0))))
        bb.ao = math.degrees(
            math.acos(float(np.clip(np.dot(me["nose"], foe["nose"]), -1.0, 1.0))))
        bb.aa = bb.los_target
        bb.closure = float(np.dot(foe["vel"] - me["vel"], u))
        bb.in_sight = bb.los <= SIGHT_CONE_DEG
        bb.in_sight_tgt = bb.los_target <= SIGHT_CONE_DEG

    # ── Superior: 국면 분류 ───────────────────────────────────────────────
    def _superior(self):
        bb = self.bb
        if bb.dist <= 1000.0 and 45.0 <= bb.los <= 135.0 and bb.ao <= 60.0:
            bb.phase = SCISSORS
        elif bb.in_sight and bb.in_sight_tgt:
            bb.phase = HABFM
        elif bb.in_sight:
            bb.phase = OBFM
        elif bb.in_sight_tgt:
            bb.phase = DBFM
        else:
            bb.phase = DETECTING

    # ── 액션: 조준점만 정한다 ─────────────────────────────────────────────
    def _pure(self, me, foe):
        bb = self.bb
        if bb.los < AIM_LOS_DEG and bb.dist <= AIM_RANGE_M:
            bb.aiming = True
            bb.aim = foe["pos"] + LEAD_TIME_S * foe["vel"]
        else:
            bb.aiming = False
            bb.aim = foe["pos"].copy()

    def _lead(self, me, foe):
        """Lead @0x14006c750 — 적기 예측 궤적 테이블에서 뽑는다.
        테이블은 0.1초 간격 30칸(@0x140050db0 의 `(float)i * 0.1`, i==0x1e 종료).
        인덱스 = clamp(int(t*30), 0, 29), t = (4^(AO/180) - 1) / 리드배율.
        리드배율(BB+0xf18)은 BB 생성 시 rand()%8+2 (2~9)."""
        self.bb.aiming = False
        t = (4.0 ** (self.bb.ao / 180.0) - 1.0) / self._lead_scale
        idx = 29 if not (0.0 <= t <= 1.0) else min(max(int(t * 30.0), 0), 29)
        self.bb.aim = foe["pos"] + (idx * 0.1) * foe["vel"]

    def _lag(self, me, foe):
        """Lag @0x14006b5e0 — 적 뒤 0~160 m."""
        self.bb.aiming = False
        t = min(max(self.bb.ao / 20.0 - 1.0, 0.0), 4.0)
        self.bb.aim = foe["pos"] - 40.0 * t * foe["nose"]

    def _rot2d(self, me, deg):
        """XY 평면 CCW 회전 (asm: fx*c - fy*s, fy*c + fx*s), deg 나눗수 57.2958."""
        a = deg / 57.2958
        c, sn = math.cos(a), math.sin(a)
        fx, fy = me["nose"][0], me["nose"][1]
        return np.array([fx * c - fy * sn, fy * c + fx * sn, 0.0])

    def _merge_turn(self, me, foe, reverse, angle=45.0):
        """MergeTurn @0x140074aa0 — 자기 위치에서 ±각으로 50 km 앞, 2000 m 위.
        고도우위가 100 m 이상이면 조준점을 적 위치로 덮어쓴다."""
        self.bb.aiming = False
        sgn = -1.0 if reverse else 1.0
        d = self._rot2d(me, sgn * angle)
        self.bb.aim = np.array([me["pos"][0] + 50000.0 * d[0],
                                me["pos"][1] + 50000.0 * d[1],
                                me["pos"][2] + 2000.0])
        if me["pos"][2] - foe["pos"][2] >= 100.0:
            self.bb.aim = foe["pos"].copy()

    def _high_yoyo_up(self, me, foe):
        """HighYoYoUp @0x140055d70 — LOS>30 이면 적 위로 (2 - d/1000)*d 올린 점. 스로틀 0.5배."""
        self.bb.aiming = False
        d = self.bb.dist
        dz = (2.0 - d / 1000.0) * d if self.bb.los > 30.0 else 0.0
        self.bb.aim = np.array([foe["pos"][0], foe["pos"][1], foe["pos"][2] + dz])
        self._thr_scale = 0.5

    def _maintain(self, me, foe):
        """Maintain @0x140070a10 — 적 위치, 스로틀 0.9."""
        self.bb.aiming = False
        self.bb.aim = foe["pos"].copy()
        self._thr_fixed = 0.9

    # ── 판정 데코레이터 (실측) ────────────────────────────────────────────
    def _turn_check(self, me, foe):
        """TurnCheck @0x1400636b0 — 0.5초마다 yaw 차분 갱신. 항상 SUCCESS."""
        if self.bb.t - self.bb.turn_last >= 0.5:
            my = math.degrees(math.atan2(me["nose"][1], me["nose"][0]))
            fy = math.degrees(math.atan2(foe["nose"][1], foe["nose"][0]))
            self.bb.dyaw_me = self.bb.prev_yaw_me - my
            self.bb.dyaw_foe = self.bb.prev_yaw_foe - fy
            self.bb.prev_yaw_me, self.bb.prev_yaw_foe = my, fy
            self.bb.turn_last = self.bb.t

    def _speed_dif(self, me, foe):
        """SpeedDifCheck @0x14005e190 — 오버슛 가능성."""
        bb = self.bb
        return (bb.dyaw_foe > bb.dyaw_me and me["speed"] >= foe["speed"]
                and bb.dist < 1200.0)

    @staticmethod
    def _vertical(foe):
        """VerticalCheck @0x140064780 — 적 기수와 월드 상방의 각 <= 45도."""
        c = float(np.clip(foe["nose"][2], -1.0, 1.0))
        return math.degrees(math.acos(c)) <= 45.0

    def _merge_check(self, me, foe):
        """DECO_MergeCheck @0x140038520 — 머지 진입 시 스냅샷을 5초 래치."""
        bb = self.bb
        if bb.merge_timer > 0.0:
            return True
        d = bb.dist
        if d > 1200.0 or d == 0.0:
            return False
        if bb.los < 60.0 and d > 120.0:
            return False
        bb.merge_dist = d
        bb.merge_los, bb.merge_los_tgt = bb.los, bb.los_target
        bb.merge_timer = 5.0
        return True

    # ── 트리 (exe 내장 XML 그대로) ────────────────────────────────────────
    # 1v1 에서 DECO_FriendlyCheck 는 항상 실패한다(아군 2기 필요) -> Split 갈래는 안 탄다.
    def _tree(self, me, foe):
        bb = self.bb
        if bb.phase == OBFM:
            self._turn_check(me, foe)
            if bb.dist > 2000.0:
                (self._lead if bb.ao > 30.0 else self._pure)(me, foe)
            elif bb.los > 15.0:
                if not self._vertical(foe) and self._speed_dif(me, foe):
                    self._high_yoyo_up(me, foe)
                else:
                    (self._lead if bb.ao > 30.0 else self._pure)(me, foe)
            else:
                if not self._vertical(foe) and self._speed_dif(me, foe):
                    self._high_yoyo_up(me, foe)
                else:
                    self._pure(me, foe)
        elif bb.phase == HABFM:
            if not self._merge_check(me, foe):
                self._pure(me, foe)          # FriendlyCheck 실패 -> Split 대신 Pure
            elif bb.merge_dist > 1000.0:
                self._merge_turn(me, foe, reverse=False)
            else:
                self._merge_turn(me, foe, reverse=self._speed_dif(me, foe))
        elif bb.phase == DETECTING:
            if not self._merge_check(me, foe):
                if bb.ao < 120.0:
                    self._pure(me, foe)
                else:
                    self._merge_turn(me, foe, reverse=False)
            elif bb.merge_dist < 350.0:
                self._merge_turn(me, foe, reverse=False)
            else:
                # DECO_MergeSpeedDifCheck: 머지시각 LOS > 1.1 * LOS_Target
                self._merge_turn(me, foe,
                                 reverse=bb.merge_los > 1.1 * bb.merge_los_tgt)
        elif bb.phase == SCISSORS:
            # ReducePower 뒤 속도 220 기준: 빠르면 Pure, 느리면 Maintain
            (self._pure if me["speed"] > 220.0 else self._maintain)(me, foe)
        else:   # DBFM
            self._pure(me, foe)

    # ── 스로틀 (SpeedControl 계열, 전부 +0x174 에 쓴다) ───────────────────
    # OBFM      -> SpeedControl @0x14005a0e0
    # HABFM/DET -> SpeedControl_HABFM @0x14005c2a0 : phase 가 1 또는 3 이면 1.0
    # SCISSORS  -> ReducePower @0x1400726f0 : 0.5 고정
    # DBFM      -> SpeedControll_DBFM @0x14005d250 : 1.0 고정
    def _throttle(self, me, foe):
        bb = self.bb
        if self._thr_fixed is not None:
            return self._thr_fixed
        if bb.phase in (HABFM, DETECTING):
            return 1.0
        if bb.phase == SCISSORS:
            return 0.5
        if bb.phase == DBFM:
            return 1.0
        # SpeedControl (OBFM)
        if not bb.in_sight:
            return 1.0
        vs, ve, d = me["speed"], foe["speed"], bb.dist
        if d <= 500.0:
            return 1.0 if vs <= ve else 0.0
        if d > 1200.0:
            return 1.0
        e = d - 500.0
        dv = min(max(0.0024 * (ve - vs), -0.15), 0.35)
        self._ema = self._ema * (1.0 - SC_DT) + SC_DT * e
        return float(min(max(0.0002 * e + 0.003 * self._ema + dv, 0.0), 1.0))

    # ── 공통 각도 ─────────────────────────────────────────────────────────
    # off  = 기수와 조준점 사이 각(deg, acos)
    # bank = 조준점의 기체 right/up 성분이 이루는 각(rad). 원본은 조준점의 기수수직
    #        성분을 정규화해 acos 하고 삼중곱 부호를 붙인다 — atan2(right, up) 과 동치.
    def _angles(self, me):
        rel = self.bb.aim - me["pos"]
        if float(np.linalg.norm(rel)) < 1e-6:
            return None
        u = _unit(rel)
        off = math.degrees(math.acos(float(np.clip(np.dot(me["nose"], u), -1.0, 1.0))))
        bank = math.atan2(float(np.dot(u, me["right"])), float(np.dot(u, me["up"])))
        return off, bank

    def _helper60(self, off):
        """pitch_helper @0x14007c490 — off 이 10 이하일 때만 60칸 링에 넣고,
        정수 절단으로 누적한 뒤 60 으로 나눈다."""
        self._ring60[self._i60 % 60] = off if off <= 10.0 else 0.0
        self._i60 += 1
        acc = 0
        for v in self._ring60:
            acc = int(acc + v)
        return float(int(acc / 60))

    # ── guide_normal @0x14007c620 ────────────────────────────────────────
    def _guide_normal(self, me):
        a = self._angles(me)
        if a is None:
            return 0.0, 0.0, 0.0
        off, bank = a
        sb = math.sin(bank)
        abank = abs(math.degrees(bank))

        if abank <= 90.0:                       # 0x14007ccf0
            if sb <= -1.0:
                roll = -2.0                     # 0x14007ce39 (뒤에서 클립)
            elif sb < 1.0:
                roll = abs(sb) * sb             # 0x14007ce61  sign(sb)*sb^2
                if roll < 0.1:
                    roll += roll
            else:
                roll = 1.0
        elif off > 3.0:                         # 0x14007cd50
            if sb <= -1.0:
                roll = -2.0                     # 0x14007ce85
            elif sb >= 1.0:
                roll = 1.0
            else:
                roll = sb
                if sb < 0.1:
                    roll += roll
        else:                                   # 0x14007ca7c  |bank|>90 이고 off<=3
            roll = -0.1 * off * sb
            if roll < 0.1:
                roll += roll

        if off <= 0.0:                          # 0x14007cd30
            roll = 0.0
            k = 0.0
        elif off < 1.0:                         # 0x14007cad5 -> 0x14007cadf
            roll *= off
            k = off
        else:                                   # 0x14007cd98
            k = min(off, GUID_ROLL_DIV)

        q = k * (-sb)
        self._ring20[self._i20 % GUID_INTEG_N] = q
        self._i20 += 1
        acc = 0
        for v in self._ring20:
            acc = int(acc + v)
        yaw = (float(int(acc / GUID_INTEG_N)) + q) * 0.5

        p = self._helper60(off) / GUID_PITCH_DIV
        p = min(max(p, 0.0), GUID_PITCH_CAP)
        p = min(p + off / GUID_ROLL_DIV, GUID_PITCH_MAX)
        s2 = 1.0 if abank <= 0.0 else (0.0 if abank / GUID_BANK_REF >= 1.0
                                       else 1.0 - abank / GUID_BANK_REF)
        s3 = 1.0 if abank <= GUID_BANK_REF else 0.5

        if off < 90.0:                          # 0x14007cdc0
            pitch = -(p * s2 * s3)
        else:                                   # 0x14007cc29  90도 넘으면 최대 당김
            pitch = -1.0
        return (float(np.clip(roll, -1.0, 1.0)), float(np.clip(pitch, -1.0, 1.0)),
                float(np.clip(yaw, -1.0, 1.0)))

    # ── guide_aiming @0x14007cee0 (AimingMode) ───────────────────────────
    def _guide_aiming(self, me):
        a = self._angles(me)
        if a is None:
            return 0.0, 0.0, 0.0
        off, bank = a
        sb = math.sin(bank)
        abank = abs(math.degrees(bank))

        if 0.888889 * abank > 80.0:             # |bank| > 90
            roll = -0.1 * off * sb
        elif sb <= -1.0:                        # 0x14007d560
            roll = -1.0
        elif sb >= 1.0:
            roll = 1.0
        else:
            roll = abs(sb) * sb                 # sign(sb)*sb^2

        if off <= 0.0:                          # Ghidra: roll = roll * 0.0, yaw 0
            roll = 0.0
            k = 0.0
        elif off < 1.0:                         # 0x14007d550
            roll *= off
            k = off
        elif off < 12.0:                        # 0x14007d555
            k = off
        else:
            k = 12.0
        yaw = -sb * k

        h = self._helper60(off) * 0.5
        t = 0.0 if h <= 0.0 else (0.4 if h >= 0.4 else h)
        p = t + off * 0.25
        p = 0.0 if p <= 0.0 else min(p, 1.0)

        w = (math.degrees(bank) / 80.0) ** 2    # 0x14007d43a
        if w > 0.0:
            p = p * (1.0 - w) if w < 1.0 else 0.0
        if abank > 80.0:                        # 0x14007d600
            p *= 0.1
        return (float(np.clip(roll, -1.0, 1.0)), float(np.clip(-p, -1.0, 1.0)),
                float(np.clip(yaw, -1.0, 1.0)))

    def _guide(self, me):
        return (self._guide_aiming(me) if self.bb.aiming else self._guide_normal(me))

    # ── 한 스텝 ───────────────────────────────────────────────────────────
    def step(self, own_state, tgt_state, frame=None):
        f = frame or _frame
        me = f(own_state)
        foe = f(tgt_state)
        self.bb.t += SC_DT                      # +0x00, dt = 1/60
        if self.bb.merge_timer >= 0.0:          # CoolTimer @0x14004d3a0
            self.bb.merge_timer -= SC_DT
        self._update(me, foe)
        self._superior()
        self._thr_scale, self._thr_fixed = 1.0, None
        self._tree(me, foe)
        roll, pitch, yaw = self._guide(me)
        thr = self._throttle(me, foe) * self._thr_scale
        self._thr_scale, self._thr_fixed = 1.0, None
        return np.array([roll, pitch, yaw, thr], dtype=np.float32)


class CutoffBTProvider:
    """env 의 적기 슬롯에 붙이는 provider. 컷오프 원본과 같은 10 Hz(--action-repeat 6).

    부호 규약: guide_normal 이 이미 pitch 음수 = 당김으로 낸다(원본 xorps 부호 반전).
    스로틀은 적기 경로가 [0,1] 을 그대로 받는다.
    """

    def __init__(self, step_ratio: int = 6, frame=None):
        self.bt = CutoffBT()
        self.frame = frame or frame_env
        self.step_ratio = int(step_ratio)
        self._hold = None
        self._count = 0

    def reset(self, context=None) -> None:
        self.bt.reset()
        self._hold = None
        self._count = 0

    def compute_action(self, context):
        from dogfight.ai.action_provider import ActionResult
        if self._hold is None or self._count % self.step_ratio == 0:
            a = self.bt.step(context.ownship_state, context.target_state, self.frame)
            self._hold = np.array(a, dtype=np.float32)
        self._count += 1
        return ActionResult(action=self._hold, source="cutoff_bt",
                            info={"phase": PHASE_NAME[self.bt.bb.phase]})

    def close(self) -> None:
        return None
