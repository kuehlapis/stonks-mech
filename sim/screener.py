"""No-code-change 16-seed paired strategy screener.

One screener arm replays 16 seeds (seed 11, seed*100000+k), paired against
sim/versions/s_base2 with --rotate. It acquires the shared match-batch lock
so it cannot overlap a 56+ match calibration batch.
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import inproc
from batchlock import BatchLock


def candidate_path(name):
    p = os.path.join(REPO, "sim", "versions", name, "bot.py")
    return p if os.path.isfile(p) else None


def validate_candidate(name):
    p = candidate_path(name)
    if not p:
        raise ValueError("candidate is not an existing variant: %s" % name)
    low = name.lower()
    if "cover" in low or "ambush" in low:
        idea = os.path.join(REPO, "notes", "ideas", name + "-spec.md")
        review = os.path.join(REPO, "notes", "reviews", name + "-critic.md")
        if not (os.path.isfile(idea) and os.path.isfile(review)):
            raise ValueError(
                "cover/ambush candidate %s blocked: need Builder spec %s and Critic spec %s"
                % (name, idea, review)
            )
    return p


def row_for_label(result, label):
    for row in result["rows"]:
        if row["label"] == label:
            return row
    return None


def run_arm(label, bot_path, seed, count, jobs):
    squad = os.path.join(REPO, "sim", "bots", "squad.py")
    specs = [(label, bot_path)] + [("squad", squad)] * 15
    jobs_arg = []
    for k in range(count):
        slots = specs[k % len(specs):] + specs[:k % len(specs)]
        jobs_arg.append((slots, seed * 100000 + k, None, "engine", None))
    if jobs > 1 and len(jobs_arg) > 1:
        with Pool(min(jobs, len(jobs_arg))) as pool:
            packed = pool.map(inproc._job, jobs_arg, chunksize=1)
    else:
        packed = [inproc._job(j) for j in jobs_arg]
    results = [r for r, _ in packed if r]
    return results


def pair_metrics(candidate_results, baseline_results, candidate_label):
    paired = []
    direct = {}
    assisted = {}
    for cresult, bresult in zip(candidate_results, baseline_results):
        seed = cresult["seed"]
        crow = row_for_label(cresult, candidate_label)
        brow = row_for_label(bresult, "s_base2")
        if crow and brow:
            paired.append({
                "seed": seed,
                "candidate_score": 16 - crow["place"],
                "baseline_score": 16 - brow["place"],
                "score_delta": (16 - crow["place"]) - (16 - brow["place"]),
                "candidate_kills": crow["kills"],
                "baseline_kills": brow["kills"],
                "kill_delta": crow["kills"] - brow["kills"],
            })
        # Direct: this arm delivered the final mech hit. Assisted: contributed
        # damage to a mech but a different killer (or environment) finished it.
        labels_by_slot = {row["slot"]: row["label"] for row in cresult["rows"]}
        candidate_slots = [i for i, lab in labels_by_slot.items() if lab == candidate_label]
        for victim in cresult["rows"]:
            if victim["label"] != "squad":
                continue
            killer_slot = victim.get("killed_by")
            # killed_by is a label in inproc rows.
            damage_by_slot = victim.get("dmg_by_slot") or {}
            contributed = any(
                float(damage_by_slot.get(str(slot), damage_by_slot.get(slot, 0.0)) or 0.0) > 0.0
                for slot in candidate_slots
            )
            if killer_slot == candidate_label:
                direct[victim["cause"] or "unknown"] = direct.get(victim["cause"] or "unknown", 0) + 1
            elif contributed:
                assisted[victim["cause"] or "unknown"] = assisted.get(victim["cause"] or "unknown", 0) + 1
    cs = inproc.summarize(candidate_results, 16)
    bs = inproc.summarize(baseline_results, 16)
    cd = paired_delta(paired, "score_delta")
    kd = paired_delta(paired, "kill_delta")
    return {
        "seeds": len(paired),
        "candidate": cs.get(candidate_label, {}),
        "baseline": bs.get("s_base2", {}),
        "paired_score_delta": cd,
        "paired_kill_delta": kd,
        "direct_squad_deaths": direct,
        "assisted_squad_deaths": assisted,
    }


def paired_delta(rows, key):
    vals = [r[key] for r in rows]
    if not vals:
        return {"mean": None, "se": None}
    mean = sum(vals) / len(vals)
    if len(vals) == 1:
        se = 0.0
    else:
        sd = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        se = sd / len(vals) ** 0.5
    return {"mean": round(mean, 2), "se": round(se, 2)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", action="append", required=True,
                    help="existing variant name under sim/versions/ (repeatable)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--workers", type=int, default=1, help="candidate arms to run in parallel")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seeds", type=int, default=16, help="paired seed count (hard maximum 16)")
    a = ap.parse_args()
    if a.seed != 11:
        raise SystemExit("--seed must be 11")
    if not 1 <= a.seeds <= 16:
        raise SystemExit("--seeds must be between 1 and 16")

    candidates = []
    for name in a.candidate:
        candidates.append((name, validate_candidate(name)))
    # Capture the 16-seed cohort exactly once and never extend it.
    names = [n for n, _ in candidates]
    lock = BatchLock("16-seed paired strategy screener", timeout=1800)
    lock.acquire()
    started = time.time()
    try:
        arms = []

        def one(item):
            name, path = item
            arm_jobs = 1 if a.workers > 1 else a.jobs
            cand = run_arm(name, path, a.seed, a.seeds, arm_jobs)
            base = run_arm("s_base2", os.path.join(REPO, "sim", "versions", "s_base2", "bot.py"),
                           a.seed, a.seeds, arm_jobs)
            return name, pair_metrics(cand, base, name)

        if a.workers > 1 and len(candidates) > 1:
            with Pool(min(a.workers, len(candidates))) as pool:
                arms = pool.map(one, candidates)
        else:
            arms = [one(item) for item in candidates]
    finally:
        lock.release()

    report = {
        "seed": a.seed,
        "paired_seeds": a.seeds,
        "stopped_after_seeds": a.seeds,
        "rotate": True,
        "wall_s": round(time.time() - started, 2),
        "candidates": {name: metrics for name, metrics in arms},
    }
    text = json.dumps(report, indent=2)
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    main()
