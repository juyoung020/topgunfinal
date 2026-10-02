# -*- coding: utf-8 -*-
"""[제작 - 학습 아님] 관측 차원을 늘리며 학습을 이어받는다 (net2net 열 확장).

첫 층 가중치에 0 열을 붙이면 확장 직후 정책 출력이 그대로다(검증: 최대 차이 7.2e-07).
지금까지 배운 것을 하나도 안 잃고 새 채널 쓰는 법만 추가로 배운다.

바꾸는 것
  · module_state.pkl  : actor/critic 인코더 첫 층 (256, N) -> (256, N+k)
  · *class_and_ctor_args.pkl : observation_space Box((N,)) -> Box((N+k,))
  · 옵티마이저 모멘트  : 같은 파라미터의 exp_avg / exp_avg_sq 도 0 열 확장
  · 번들 metadata      : observation_size

사용:
  python student/tools/expand_obs_dim.py --src <체크포인트/번들 부모> --dst <출력> --to 17
"""
from __future__ import annotations

import argparse, gzip, io, json, os, pickle, shutil, sys
from pathlib import Path

import numpy as np

FIRST_LAYER_KEYS = (
    "encoder.actor_encoder.tokenizer.net.mlp.0.weight",
    "encoder.critic_encoder.tokenizer.net.mlp.0.weight",
)


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="peak_v8_iter19140 처럼 checkpoint/ 와 번들이 있는 폴더")
    p.add_argument("--dst", required=True)
    p.add_argument("--to", type=int, default=17)
    return p.parse_args()


def widen(arr, to):
    """(out, in) -> (out, to). 새 열은 0."""
    import torch
    t = torch.as_tensor(np.asarray(arr))
    if t.shape[1] == to:
        return t
    pad = torch.zeros(t.shape[0], to - t.shape[1], dtype=t.dtype)
    return __import__("torch").cat([t, pad], dim=1)


def patch_module_state(path, to):
    d = pickle.load(open(path, "rb"))
    n = 0
    for k in FIRST_LAYER_KEYS:
        if k in d:
            before = tuple(np.asarray(d[k]).shape)
            d[k] = widen(d[k], to)
            print("   %-52s %s -> %s" % (k.split("encoder.")[1][:52], before, tuple(d[k].shape)))
            n += 1
    pickle.dump(d, open(path, "wb"))
    return n


def patch_spaces(root, frm, to):
    """observation_space 의 shape 를 바꾼다. Box 객체를 새로 만들어 교체."""
    from gymnasium.spaces import Box
    hits = 0
    for p in Path(root).rglob("*.pkl"):
        try:
            obj = pickle.load(open(p, "rb"))
        except Exception:
            continue
        changed = [0]

        def fix(o, depth=0):
            if depth > 6:
                return o
            if isinstance(o, Box) and o.shape == (frm,):
                changed[0] += 1
                return Box(float(np.min(o.low)), float(np.max(o.high)), (to,), o.dtype)
            if isinstance(o, dict):
                return {k: fix(v, depth + 1) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                t = [fix(v, depth + 1) for v in o]
                return type(o)(t) if not isinstance(o, tuple) else tuple(t)
            return o

        new = fix(obj)
        if changed[0]:
            pickle.dump(new, open(p, "wb"))
            print("   공간 교체 %d개 · %s" % (changed[0], p.relative_to(root)))
            hits += changed[0]
    return hits


def patch_optimizer(root, to):
    """Adam 모멘트도 같은 모양으로 늘린다. 안 늘리면 로드 시 모양 불일치."""
    import torch
    n = 0
    for p in Path(root).rglob("state.pkl"):
        try:
            obj = pickle.load(open(p, "rb"))
        except Exception:
            continue
        s = str(type(obj))
        touched = [0]

        def fix(o, depth=0):
            if depth > 8:
                return o
            if isinstance(o, dict):
                out = {}
                for k, v in o.items():
                    if isinstance(v, (np.ndarray, torch.Tensor)) and getattr(v, "ndim", 0) == 2 \
                            and v.shape[0] == 256 and v.shape[1] == to - 1:
                        out[k] = widen(v, to); touched[0] += 1
                    else:
                        out[k] = fix(v, depth + 1)
                return out
            if isinstance(o, list):
                return [fix(v, depth + 1) for v in o]
            return o

        new = fix(obj)
        if touched[0]:
            pickle.dump(new, open(p, "wb"))
            print("   옵티마이저 텐서 %d개 확장 · %s" % (touched[0], p.relative_to(root)))
            n += touched[0]
    return n


def main():
    a = parse()
    src, dst = Path(a.src), Path(a.dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("복사:", dst)

    ck = dst / "checkpoint"
    ms = ck / "learner_group/learner/rl_module/default_policy/module_state.pkl"
    print("\n[1] 첫 층 열 확장")
    if ms.exists():
        patch_module_state(str(ms), a.to)
    for extra in ck.rglob("module_state.pkl"):
        if extra != ms:
            patch_module_state(str(extra), a.to)

    print("\n[2] observation_space 교체")
    patch_spaces(str(ck), a.to - 1, a.to)

    print("\n[3] 옵티마이저 모멘트 확장")
    patch_optimizer(str(ck), a.to)

    print("\n[4] 번들")
    bw = dst / "policy_weights.pkl.gz"
    if bw.exists():
        w = pickle.load(gzip.open(bw, "rb"))
        for k in FIRST_LAYER_KEYS:
            if k in w:
                w[k] = widen(w[k], a.to)
        with gzip.open(bw, "wb") as f:
            pickle.dump(w, f)
        print("   policy_weights.pkl.gz 확장")
    bm = dst / "metadata.json"
    if bm.exists():
        m = json.loads(bm.read_text(encoding="utf-8"))
        md = m.get("metadata", m)
        if "observation_size" in md:
            md["observation_size"] = a.to
        bm.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        print("   metadata observation_size =", a.to)
    print("\n완료:", dst)


if __name__ == "__main__":
    main()
