# -*- coding: utf-8 -*-
"""Delayed self-play plumbing for stage 32 (no changes to the trainer).

WHY
---
Self-play needs the opponent pool to include SNAPSHOTS OF THE CURRENT LEARNER.
The trainer's [MOD-KILLFLOOR] probe already writes a lightweight bundle of the
live weights to <stage_dir>/killfloor_probe/ every eval_kill_probe_interval
iters. This sidecar turns that byproduct into a rolling self-snapshot pool:

  1. watch <stage_dir>/killfloor_probe.json (written when the probe completes,
     i.e. the bundle beside it is fully flushed)
  2. on each advance, copy killfloor_probe/ -> snapshots/snap_<iter>/
  3. rewrite live_tune.json with the FULL pool (LIVETUNE replaces target_pool
     wholesale -- single_agent_env._load_live_tune), the four self entries
     pointing at latest + a delta-uniform shift register of older snapshots

The opponent loader caches by PATH (single_agent_env._ensure_policy_opponent),
so a monotonic new path per snapshot is REQUIRED -- overwriting a fixed path
would never reload. That is exactly what snap_<iter> gives.

This is measurement/plumbing, NOT training. Run it in the background next to
the trainer:
    python student/tools/snapshot_sidecar.py --tag 0721_anchor2
"""
from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _p in (ROOT, SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _stage_pool(idx: int):
    """The authoritative pool from my_curriculum for stage `idx`, so the sidecar
    never drifts from the stage definition -- we only swap the four self entries."""
    import importlib
    stages = importlib.import_module("student.my_curriculum").get_stages()
    st = [s for s in stages if s.index == idx][0]
    return [dict(e) for e in st.env_overrides["target_pool"]], st


def _current_iter(state_path: Path, idx: int) -> int | None:
    try:
        s = json.loads(state_path.read_text(encoding="utf-8"))
        return int(s["stages"][str(idx)].get("iterations_trained") or 0)
    except Exception:
        return None


def _atomic_write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default="0721_anchor2")
    ap.add_argument("--name", default="AeroFlyer")
    ap.add_argument("--stage", type=int, default=32, help="curriculum stage index")
    ap.add_argument("--poll-seconds", type=float, default=30.0)
    ap.add_argument("--keep", type=int, default=6, help="snapshots to retain")
    ap.add_argument("--lag-steps", default="0,5,20,60",
                    help="자가 슬롯이 집을 history 뒤로-칸수 (한 칸=probe 간격). "
                         "0 은 최신. 기본 0,5,20,60 = 대략 지금/-100/-400/-1200 iter")
    # [MOD-LTPATH] 2026-08-19 — 학습이 **실제로 읽는** live_tune 경로를 지정한다.
    # 기본은 종전대로 <run_dir>/live_tune.json.
    # 왜 필요한가: 커리큘럼 stage 34 의 live_tune_file 이 태그와 무관하게
    # 0817_timefix 로 하드코딩돼 있다. 새 태그(0819_hz20)로 학습을 띄우면
    # sidecar 는 0819_hz20/live_tune.json 에 쓰는데 트레이너는 0817_timefix 를
    # 읽어, **상대 풀이 갱신되지 않는다**(실측: 6.2시간 동안 고정 4슬롯).
    # patrol 은 sidecar 쪽 파일을 보므로 "갱신 1.4분 전"이라고 정상 보고한다 —
    # 감시로도 안 잡히는 조합이었다.
    ap.add_argument("--live-tune-file", default=None,
                    help="트레이너가 읽는 live_tune.json 절대경로 "
                         "(미지정 시 <run_dir>/live_tune.json)")
    args = ap.parse_args()

    lag_steps = [int(x) for x in str(args.lag_steps).split(",") if x.strip() != ""]
    pool_template, _st = _stage_pool(args.stage)
    run_dir = (ROOT / "artifacts" / "curriculum" / args.name / args.tag)
    stage_dir = run_dir / f"stage_{args.stage}_{_st.name}"
    probe_bundle = stage_dir / "killfloor_probe"
    probe_signal = stage_dir / "killfloor_probe.json"
    snap_dir = stage_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    live_tune = (Path(args.live_tune_file) if args.live_tune_file
                 else run_dir / "live_tune.json")   # [MOD-LTPATH]
    print(f"[LTPATH] 상대 풀을 여기에 쓴다: {live_tune}")
    state_path = run_dir / "curriculum_state.json"

    # seed snap_0000 = parent, so the self block is a valid (past-self) bundle
    # before the first probe exists. The launcher also does this; here as a
    # safety net if the sidecar starts first.
    seed = snap_dir / "snap_0000"
    if not seed.exists():
        print("WARNING: snap_0000 missing -- seed it from the parent bundle "
              "before launch (loader crashes on a missing path)")

    # indices of the four self entries (bundle path contains '/snapshots/')
    self_idx = [i for i, e in enumerate(pool_template)
                if "/snapshots/" in str(e.get("bundle", "")).replace("\\", "/")]
    # Any number of self entries. It was pinned at 4 because stage 32 had four;
    # an all-aspect pool needs one per opening (offensive / defensive / head-on
    # / beam), and the hard check turned that into a startup crash.
    if not self_idx:
        print("ERROR: no self entries found (bundle path must contain "
              "'/snapshots/')")
        return 2
    print(f"watching {probe_signal}")
    print(f"self entries at pool indices {self_idx}")

    last_seen = 0.0
    # [2026-08-18] 디스크에 이미 있는 스냅샷으로 이력을 채운다.
    # 이걸 안 하면 sidecar 를 재기동할 때마다 history 가 ["snap_0000"] 하나로
    # 시작해, 넓힌 lag_steps(-1200 iter 까지)가 60 스냅샷(=1,200 iter, 약 5시간)
    # 뒤에나 효과를 낸다. GC 를 꺼서 snap_0000 부터 전부 남아 있으므로 그냥 읽는다.
    _existing = []
    for _d in snap_dir.glob("snap_*"):
        _m = re.match(r"snap_(\d+)$", _d.name)
        if _d.is_dir() and _m and (_d / "policy_weights.pkl.gz").exists():
            _existing.append((int(_m.group(1)), _d.name))
    history: list[str] = [n for _, n in sorted(_existing)] or ["snap_0000"]
    print(f"이력 복원: {len(history)}개 "
          f"({history[0]} ~ {history[-1]})")
    while True:
        if not probe_signal.exists():
            time.sleep(args.poll_seconds)
            continue
        m = probe_signal.stat().st_mtime
        if m <= last_seen:
            time.sleep(args.poll_seconds)
            continue
        it = _current_iter(state_path, args.stage)
        if it is None:
            time.sleep(args.poll_seconds)
            continue

        # copy the just-flushed probe bundle to a monotonic path
        dst = snap_dir / f"snap_{it:04d}"
        if not dst.exists() and probe_bundle.exists():
            tmp = snap_dir / f".snap_{it:04d}.partial"
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            shutil.copytree(probe_bundle, tmp)
            os.replace(tmp, dst)
            history.append(f"snap_{it:04d}")
            print(f"[{time.strftime('%H:%M:%S')}] snapshot -> {dst.name}")

        # build the full pool: fixed teacher/frozen entries verbatim, the self
        # entries = latest + delta-uniform older (shift register tail), one
        # pick per self entry however many there are
        # [2026-08-18 사용자 지적] "셀프플레이가 너무 금방 갱신돼서 학습이 빡세다."
        # 맞다. 예전에는 history[-1],[-2],[-3],[-4] 로 **연속 4개**를 집었다.
        # 스냅샷이 20 iter 마다 쌓이므로 상대 넷이 전부 -20~-80 iter = "거의 지금의 나"
        # 였다. 정책이 움직이는 표적을 쫓게 되고, 과거에 이겼던 상대를 잊는다
        # (순환: A->B->C->A). AlphaStar/OpenAI Five 가 리그를 쓰는 이유가 이것이다.
        #
        # GC 를 꺼둔 덕에 snap_0000 부터 전부 디스크에 있다(현재 319개). 저장 간격은
        # 그대로 두고 **고르는 간격만** 기하급수로 벌린다. 기본 --lag-steps 0,5,20,60:
        #     history 한 칸 = 20 iter 이므로 대략 지금 / -100 / -400 / -1200 iter.
        # 최신 하나는 남겨 정직함을 유지하고, 나머지로 견고함과 망각 방지를 산다.
        # 역사가 짧을 때는 자동으로 가장 오래된 것(초기엔 snap_0000)으로 물린다.
        picks = [history[max(0, len(history) - 1 - k)] for k in lag_steps]
        pool = [dict(e) for e in pool_template]
        for slot, idx in enumerate(self_idx):
            # [2026-08-28] 절대경로 금지: 작업루트 기준 상대경로로 기록 (폴더를 옮겨도 깨지지 않게)
            pool[idx]["bundle"] = os.path.relpath(snap_dir / picks[slot], ROOT).replace("\\", "/")
        # [2026-08-17] target_pool 만 쓰고 통째로 덮어쓰면, 손으로 넣은
        # reward 핫튜닝이 다음 스냅샷(20 iter)에 지워진다. 기존 키는 보존한다.
        _payload = {}
        try:
            with open(live_tune, encoding="utf-8") as _f:
                _payload = json.load(_f)
            if not isinstance(_payload, dict):
                _payload = {}
        except Exception:
            _payload = {}
        _payload["target_pool"] = pool
        _atomic_write_json(live_tune, _payload)
        print(f"[{time.strftime('%H:%M:%S')}] live_tune updated: "
              f"picks={picks} (lag_steps={lag_steps}, history={len(history)})")

        # GC old snapshots (keep the newest --keep, never snap_0000)
        #
        # [2026-08-16] NEVER delete a snapshot that live_tune.json currently
        # points at. Measured failure: two sidecars were running at once (a
        # nohup launch that looked like it had failed, plus a second one). Each
        # kept its own `history`, so A wrote snap_0057 into live_tune and B --
        # whose keep-window did not contain it -- deleted it. Five env runners
        # then died on FileNotFoundError reading snap_0057/metadata.json, and
        # because the trainer runs with restart_failed_sub_environments=False
        # RLlib took five actors out of service before Ray restarted them.
        #
        # `picks` alone is not enough: it only covers THIS process's view. We
        # re-read the file we just wrote, so any writer's references are
        # protected. Belt and braces, because the cost of a wrong delete is a
        # dead training run and the cost of keeping a stale directory is 2 MB.
        protected = {"snap_0000", *picks}
        try:
            with open(live_tune, encoding="utf-8") as _f:
                for _e in json.load(_f).get("target_pool", []):
                    protected.add(os.path.basename(str(_e.get("bundle", ""))))
        except Exception:
            # unreadable live_tune -> protect everything, delete nothing
            protected = None
        if protected is not None:
            snaps = sorted([p for p in snap_dir.glob("snap_*") if p.is_dir()])
            for p in snaps[:-args.keep]:
                if p.name not in protected:
                    shutil.rmtree(p, ignore_errors=True)

        last_seen = m
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
