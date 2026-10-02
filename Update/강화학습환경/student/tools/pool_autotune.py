# -*- coding: utf-8 -*-
"""[MOD-OPPLOG 2026-09-06 사용자 지시] 못 이기는 상대를 더 만나게 하는 풀 자동 조정.

기존 env PFSP(`_prioritise`)는 **건드리지 않는다** — 그건 teacher 유지분에만 걸리고,
Elo 경로는 성장 스냅샷 풀용이다. 이건 별개 기구로, 밖에서 돌며 live_tune.json 의
target_pool 비중만 다시 쓴다(리셋마다 핫리로드되는 화이트리스트 키).

  1. env 가 판마다 남기는 opp_log/opp_<pid>.csv 를 읽는다 (iter, 상대, 결과, ...)
  2. 상대별 **최근 N판** 승률을 낸다 (승 = win / judge_win, 대회 판정 기준)
  3. f_hard(x) = (1 - 승률)^p 로 배수를 만들어 기준 비중에 곱한다
  4. 바닥(floor)·천장(cap)을 걸고 **총합을 보존**한 뒤 live_tune.json 에 쓴다

설계 근거 (env 주석에 기록된 실측 교훈을 그대로 따른다):
  - 바닥: 0 이 되면 그 상대는 측정이 끊겨 "회복했는지"를 영영 모른다.
  - 천장: 편차가 크면 한 상대가 판을 다 먹는다(80 Elo 차가 67.6% 를 몰아간 실측).
          균등 대비 배수로 제한한다(기본 3.0배).
  - 최소 표본: 판수가 적으면 건드리지 않는다(기본 8판).
  - 혼합: 순수 우선순위는 평범한 self-play 보다 나빴다는 보고가 있어, 기준 비중을
          완전히 갈아엎지 않고 곱셈 보정으로만 쓴다.

사용(측정·조정용, 학습 아님):
  python student/tools/pool_autotune.py --tag final_v7            # 한 번 계산해 보기만
  python student/tools/pool_autotune.py --tag final_v7 --apply    # live_tune.json 에 적용
  python student/tools/pool_autotune.py --tag final_v7 --apply --loop 1800   # 30분마다
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

# [2026-09-06 사용자 확정 "무승부는 패야"] 승은 격추/판정승뿐이다.
#   draw(동시격추, 실측 18.4%) · timeout · crash 는 전부 승이 아닌 것으로 센다.
#   즉 승률 = 승 / 전체이고, 무승부가 잦은 상대일수록 승률이 낮아 비중이 올라간다.
WIN = ("win", "judge_win")


def read_log(tag, window):
    """상대별 **최근** window 판의 결과. (승 리스트, 총 행수)

    [2026-09-06 사용자 질문 "누적이야 최근 기준이야"] 최근 창이 맞다. 다만 러너 17개가
    각자 파일에 쓰는데 파일을 통째로 이어붙인 뒤 뒤에서 자르면, glob 순서상 마지막 몇
    러너의 판만 뽑혀 시간순이 아니게 된다. 로그 줄에 iteration·타임스탬프가 없어
    전역 정렬이 불가하므로 **파일마다 뒤에서 균등하게** 가져와 동시대 표본을 만든다.
    러너들이 같은 속도로 도므로 각 파일의 끝부분은 서로 같은 시기다."""
    d = os.path.join("artifacts", "curriculum", "AeroFlyer", tag, "opp_log")
    files = sorted(glob.glob(os.path.join(d, "opp_*.csv")))
    per_file = []
    total = 0
    for f in files:
        per = collections.defaultdict(list)
        try:
            with io.open(f, encoding="utf-8", errors="ignore") as h:
                for line in h:
                    q = line.rstrip(chr(10)).split(",")
                    if len(q) < 3:
                        continue
                    per[q[1]].append(1.0 if q[2] in WIN else 0.0)
                    total += 1
        except Exception:
            continue
        per_file.append(per)
    if not per_file:
        return {}, 0
    take = max(1, -(-window // len(per_file)))      # 파일당 올림 분배
    out = collections.defaultdict(list)
    for per in per_file:
        for k, v in per.items():
            out[k].extend(v[-take:])
    return {k: v[-window:] for k, v in out.items()}, total


def current_iter(tag):
    """training_log.csv 의 마지막 total_iter. 없으면 None."""
    p = os.path.join("artifacts", "curriculum", "AeroFlyer", tag, "training_log.csv")
    try:
        with io.open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return int(float(rows[-1]["total_iter"])) if rows else None
    except Exception:
        return None


def base_pool(tag):
    """커리큘럼이 만드는 기준 풀(확장 136항목)을 그대로 가져온다."""
    os.environ["FINAL_SP_TAG"] = tag
    sys.path.insert(0, "."); sys.path.insert(0, "src")
    for m in list(sys.modules):
        if m.startswith("student.my_curriculum"):
            del sys.modules[m]
    import importlib
    cur = importlib.import_module("student.my_curriculum")
    st = [x for x in cur.get_stages() if x.index == 35][0]
    for k, v in st.env_overrides.items():
        if "pool" in k and isinstance(v, list):
            return v
    raise SystemExit("풀을 못 찾음")


def is_self(entry):
    """자기 자신 스냅샷 슬롯 — PFSP/사이드카가 맡는다. 여기서는 절대 건드리지 않는다."""
    return "/snapshots/" in str(entry.get("bundle", "")).replace("\\", "/")


def name_of(entry):
    """env `_opponent_name` 과 같은 이름을 만든다. 로그와 키가 맞아야 승률이 붙는다.
    실측: 로그는 "frozen_<leaf>" / "cutoff_bt", 번들 basename 만 쓰면 0판으로 읽힌다."""
    mode = str(entry.get("mode", "?"))
    if mode == "cutoffbt":
        return "cutoff_bt"
    b = entry.get("bundle")
    if b:
        return "frozen_" + os.path.basename(str(b).replace("\\", "/").rstrip("/"))
    return mode


def retune(pool, hist, exponent, floor_mult, cap_mult, min_games):
    """상대별 배수를 만들어 항목 가중치에 곱하고, 총합을 보존한다."""
    groups = collections.defaultdict(list)
    for i, e in enumerate(pool):
        if is_self(e):          # 자기 슬롯은 PFSP 몫 — 비중 재분배에서 뺀다
            continue
        groups[name_of(e)].append(i)
    names = sorted(groups)
    base = {n: sum(pool[i]["weight"] for i in groups[n]) for n in names}
    total = sum(base.values())
    mult, wr, ng = {}, {}, {}
    for n in names:
        w = hist.get(n, [])
        ng[n] = len(w)
        if len(w) < min_games:
            mult[n] = 1.0; wr[n] = None
            continue
        p = sum(w) / len(w)
        wr[n] = p
        mult[n] = (1.0 - p) ** exponent
    raw = {n: base[n] * mult[n] for n in names}
    # 배수가 전부 0 이 되는 경우(전승) 방지
    if sum(raw.values()) <= 0:
        raw = dict(base)
    scale = total / sum(raw.values())
    new = {n: raw[n] * scale for n in names}
    # 바닥·천장 — 균등(total/len) 대비 배수로 건다
    uni = total / len(names)
    lo, hi = floor_mult * uni, cap_mult * uni
    for _ in range(12):
        clipped = {n: min(max(v, lo), hi) for n, v in new.items()}
        s = sum(clipped.values())
        if abs(s - total) < 1e-9:
            new = clipped; break
        free = [n for n in names if lo < clipped[n] < hi]
        if not free:
            new = {n: v * total / s for n, v in clipped.items()}; break
        diff = total - s
        fs = sum(clipped[n] for n in free)
        new = dict(clipped)
        for n in free:
            new[n] += diff * (clipped[n] / fs)
    return base, new, wr, ng, groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.environ.get("FINAL_SP_TAG", "final_v7"))
    ap.add_argument("--window", type=int, default=60, help="상대별 최근 몇 판을 볼지")
    ap.add_argument("--exponent", type=float, default=2.0, help="f_hard 지수 p")
    ap.add_argument("--floor-mult", type=float, default=0.25, help="균등 대비 최소 배수")
    # [2026-09-06 사용자 지시 "뭐하나 비중이 10프로 넘게하지마"] 고정 17종은 전체의 0.85 를
    #   나눠 가지므로 균등이 0.05 = 5%. 천장 2.0배 = 0.10 = 정확히 10%.
    ap.add_argument("--cap-mult", type=float, default=2.0, help="균등 대비 최대 배수(2.0 = 전체의 10%)")
    ap.add_argument("--min-games", type=int, default=8)
    # [2026-09-06 실측] 새 태그를 열면 iter 3 에 첫 배수가 나가는데, 그때는 러너별 표본이
    #   몇 판뿐이라 우연히 min-games 를 넘긴 상대만 극단 승률(0.0/1.0)로 계산돼 **비중이
    #   거꾸로 뒤집힌다**(v8 실측: symmetric 0.23배인데 풀에서는 9.3%). 판 수만으로는 못 막는다.
    #   iteration 하한을 같이 걸어 초기 구간을 통째로 건너뛴다.
    ap.add_argument("--min-iter", type=int, default=150,
                    help="이 iteration 전에는 배수를 발행하지 않는다(초기 표본 왜곡 방지)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--loop", type=int, default=0, help="폴링 간격(초). 0 = 1회만")
    # [2026-09-06 사용자 지시 "30분마다는 오반데 100이터마다 자동적으로"]
    #   벽시계가 아니라 학습 진행을 따라간다. 사이드카 스냅샷이 100 iter 마다이므로
    #   같은 박자로 발행해야 헛돌거나 같은 배수가 두 번 반영되는 일이 없다.
    ap.add_argument("--every-iters", type=int, default=100,
                    help="이만큼 iteration 이 진행될 때마다 재계산(0 = 폴링마다)")
    a = ap.parse_args()

    last_iter = None
    while True:
        cur_iter = current_iter(a.tag)
        if a.every_iters > 0 and a.loop:
            if last_iter is not None and cur_iter is not None                     and cur_iter - last_iter < a.every_iters:
                time.sleep(a.loop)
                continue
        if a.min_iter and cur_iter is not None and cur_iter < a.min_iter:
            print("[iter %d] 표본 부족 구간 — 배수 발행 보류 (min-iter %d)" % (cur_iter, a.min_iter), flush=True)
            last_iter = cur_iter
            if not a.loop:
                return
            time.sleep(a.loop); continue
        hist, nrows = read_log(a.tag, a.window)
        pool = base_pool(a.tag)
        base, new, wr, ng, groups = retune(pool, hist, a.exponent, a.floor_mult,
                                           a.cap_mult, a.min_games)
        print("[%s] %s · iter %s · 로그 %d판 · 상대 %d종"
              % (time.strftime("%H:%M:%S"), a.tag,
                 ("%d" % cur_iter) if cur_iter is not None else "?", nrows, len(base)))
        print("%-30s %6s %6s %8s %8s %7s" % ("상대", "판수", "승률", "기준", "새비중", "배수"))
        for n in sorted(base, key=lambda x: -new[x]):
            print("%-30s %6d %6s %8.3f %8.3f %6.2fx"
                  % (n[:30], ng[n], ("%.2f" % wr[n]) if wr[n] is not None else "-",
                     base[n], new[n], new[n] / max(base[n], 1e-9)))
        if a.apply:
            # 배수만 발행한다. live_tune 의 target_pool 은 사이드카가 단독으로 쓴다
            # (둘이 같이 쓰면 20 iter 마다 서로를 덮어써 경쟁한다 — 실측 전례).
            mp = os.path.join("artifacts", "curriculum", "AeroFlyer", a.tag, "pool_weights.json")
            payload = {"updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "window": a.window, "exponent": a.exponent,
                       "floor_mult": a.floor_mult, "cap_mult": a.cap_mult,
                       "mult": {n: round(new[n] / max(base[n], 1e-9), 6) for n in base},
                       "win_rate": {n: (round(wr[n], 3) if wr[n] is not None else None) for n in base},
                       "games": {n: ng[n] for n in base}}
            tmp = mp + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            os.replace(tmp, mp)
            print("-> pool_weights.json 발행 (iter %s · %d종). 사이드카가 다음 스냅샷에 반영한다."
                  % (("%d" % cur_iter) if cur_iter is not None else "?", len(base)))
        last_iter = cur_iter
        if False:
            lt = os.path.join("artifacts", "curriculum", "AeroFlyer", a.tag, "live_tune.json")
            cur = {}
            if os.path.exists(lt):
                try:
                    cur = json.load(io.open(lt, encoding="utf-8"))
                except Exception:
                    cur = {}
            out = [dict(e) for e in pool]
            for n, idxs in groups.items():
                b = base[n]
                if b <= 0:
                    continue
                k = new[n] / b
                for i in idxs:
                    out[i]["weight"] = round(out[i]["weight"] * k, 6)
            cur["target_pool"] = out          # 병합 — 다른 키는 보존한다
            tmp = lt + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                json.dump(cur, f, ensure_ascii=False, indent=1)
            os.replace(tmp, lt)
            print("-> live_tune.json 적용 (%d항목)" % len(out))
        if not a.loop:
            return
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
