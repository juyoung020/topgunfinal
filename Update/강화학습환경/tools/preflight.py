# -*- coding: utf-8 -*-
"""기동 전 경로 일치 검사 (구조적 안전판). 태그 하나(FINAL_SP_TAG)에서 모든 경로가 파생되는지 확인한다.
사용: python tools/preflight.py [--tag final_sp2]   (launch.ps1 이 sidecar/trainer/round2/resume 앞에서 자동 호출)
검사: run dir · live_tune(reward 키, target_pool 경로 존재) · 스냅샷 snap_0000 · 커리큘럼 stage 35 의 경로가 태그와 일치
     · 풀 번들 전부 존재 · 절대경로 없음 · 대시보드 bat 의 logdir 이 이 태그의 리플레이를 포함 · 리플레이/대시보드 폴더 위치.
종료코드 0 = 통과, 1 = 실패(원인 출력).
"""
import argparse, io, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, "src"); sys.path.insert(0, ".")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=os.environ.get("FINAL_SP_TAG", "final_sp"))
    ap.add_argument("--first-run", action="store_true", help="새 태그 첫 기동: run dir 이 아직 없어도 통과")
    a = ap.parse_args(); tag = a.tag; os.environ["FINAL_SP_TAG"] = tag
    bad, notes = [], []
    run = f"artifacts/curriculum/AeroFlyer/{tag}"; lt = f"{run}/live_tune.json"; snaps = f"{run}/stage_35_selfplay_final/snapshots"
    import importlib
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    e = st.env_overrides
    if e["live_tune_file"] != lt: bad.append(f"커리큘럼 live_tune_file={e['live_tune_file']} ≠ {lt} (태그 불일치)")
    for p in e["target_pool"]:
        b = p["bundle"]
        if os.path.isabs(b): bad.append(f"절대경로 번들: {b}")
        if "/snapshots/" in b and not b.startswith(snaps): bad.append(f"self 슬롯이 다른 태그를 가리킴: {b}")
        if not os.path.isfile(os.path.join(b, "policy_weights.pkl.gz")):
            (notes if a.first_run and "/snapshots/" in b else bad).append(f"번들 없음: {b}")
    if os.path.isfile(lt):
        d = json.load(open(lt, encoding="utf-8"))
        if "reward" not in d: bad.append("live_tune 에 reward 없음")
        for p in d.get("target_pool", []):
            if os.path.isabs(p["bundle"]): bad.append(f"live_tune 절대경로: {p['bundle']}")
            if not os.path.isfile(os.path.join(p["bundle"], "policy_weights.pkl.gz")): bad.append(f"live_tune 번들 없음: {p['bundle']}")
        cr = d.get("reward", {})
        for k in ("win_reward", "crash_reward", "loss_reward"):
            if k in cr and cr[k] != st.reward_overrides.get(k): notes.append(f"live_tune {k}={cr[k]} ≠ 코드 {st.reward_overrides.get(k)} (핫튜닝 값이면 OK)")
    elif not a.first_run: bad.append(f"live_tune 없음: {lt}")
    if not os.path.isfile(f"{snaps}/snap_0000/policy_weights.pkl.gz") and not a.first_run: bad.append(f"snap_0000 없음: {snaps}")
    dash = io.open("launch_dashboard.bat", encoding="ascii").read()
    cmdlines = [l for l in dash.splitlines() if not l.lower().startswith("rem")]
    m = re.search(r"--logdir (\S+)", " ".join(cmdlines)); logdir = m.group(1).replace(chr(92), "/") if m else ""
    rep = f"artifacts/replays/AeroFlyer_{tag}"
    if not (rep.startswith(logdir.rstrip("/")) or logdir.rstrip("/") == rep): bad.append(f"대시보드 --logdir {logdir} 가 이 태그 리플레이 {rep} 를 안 봄")
    for f in ("launch_final_sidecar.bat", "launch_final_resume.bat", "launch_final_round2.bat"):
        t = io.open(f, encoding="utf-8").read()
        if "%FINAL_SP_TAG%" not in t: bad.append(f"{f} 가 태그 변수를 안 씀")
        if re.search(r"[A-Za-z]:\\", t.replace("%CONDA_ENV%", "")) and "anaconda3" not in t: bad.append(f"{f} 절대경로")
    ck = f"{run}/stage_35_selfplay_final/checkpoints"
    latest = sorted(os.listdir(ck))[-1] if os.path.isdir(ck) and os.listdir(ck) else "(없음)"
    print(f"[preflight] tag={tag} run={run} live_tune={'OK' if os.path.isfile(lt) else '없음'} snap_0000={'OK' if os.path.isfile(f'{snaps}/snap_0000/policy_weights.pkl.gz') else '없음'} pool={len(e['target_pool'])}항목 latest_ckpt={latest} replays={rep} dashboard_logdir={logdir}")
    for n in notes: print("  note:", n)
    for b in bad: print("  FAIL:", b)
    print("[preflight]", "PASS" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
