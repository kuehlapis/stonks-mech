"""In-process match runner: bots run as Python objects in this process (no subprocesses), matches run in
parallel worker processes. Fast batches for A/B tests, and a per-decision trace of one slot for debugging.

  python sim/inproc.py --bot ours=python/bot.py --count 1 --bot ex=python/example_bot.py \
      --matches 64 --jobs 12 --seed 1 [--trace SLOT --trace-out t.jsonl] [--out summary.json]

A bot spec is LABEL=PATH to a file that calls mf.run(BotClass). Each bot file's directory gets its own module
namespace, so two versions of our bot (e.g. a snapshot in sim/versions/v1/) can play in the same match.
Late answers: an act() slower than the tick budget is treated as missing (coast), like the server.
"""
import argparse
import contextlib
import gzip
import importlib.util
import json
import math
import os
import sys
import time
import traceback
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PY = os.path.join(REPO, "python")
ARENA = os.path.join(REPO, "arena")
_CONT = ("move", "aim", "boost")


def recorded_hello():
    with gzip.open(os.path.join(REPO, "check", "stream.jsonl.gz"), "rt") as f:
        return json.loads(f.readline())


class BotEnv:
    """Module namespace for one bot directory: its .py files are swapped into sys.modules while active."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.names = {f[:-3] for f in os.listdir(self.dir) if f.endswith(".py")}
        if not os.path.exists(os.path.join(self.dir, "mechfight.py")):
            self.names.add("mechfight")  # shared from python/
        self.mods = {}
        self.cls = None

    @contextlib.contextmanager
    def active(self):
        saved = {n: sys.modules.pop(n) for n in list(sys.modules) if n in self.names}
        sys.modules.update(self.mods)
        sys.path.insert(0, self.dir)
        if self.dir != PY:
            sys.path.insert(1, PY)
        try:
            yield
        finally:
            for n in list(sys.modules):
                if n in self.names:
                    self.mods[n] = sys.modules.pop(n)
            sys.path.remove(self.dir)
            if self.dir != PY:
                sys.path.remove(PY)
            sys.modules.update(saved)

    def load(self):
        with self.active():
            import mechfight as mf
            got = []
            real = mf.run
            mf.run = got.append
            try:
                spec = importlib.util.spec_from_file_location("__bot_" + str(abs(hash(self.path))), self.path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            finally:
                mf.run = real
            self.cls = got[-1]
            self.mf = mf
        return self

    def make(self, hello):
        with self.active():
            self.mf.draw.caps = hello["config"].get("debug", {})
            return self.cls(hello)


_WORLD = None
_ENVS = {}


def _world():
    global _WORLD
    if _WORLD is None:
        sys.path.insert(0, PY)
        from world import World
        _WORLD = World(ARENA)
    return _WORLD


def _env(path):
    if path not in _ENVS:
        _ENVS[path] = BotEnv(path).load()
    return _ENVS[path]


def play(specs, seed, trace_slot=None, timing=True, engine="engine", trace_label=None):
    """specs: list of (label, path) per slot. Returns a result dict (and the trace list if asked)."""
    Match = importlib.import_module(engine).Match
    hello0 = recorded_hello()
    cfg = hello0["config"]
    world = _world()
    match = Match(cfg, world, seed, len(specs))
    budget = cfg["bot"]["tick_budget_ms"] / 1000
    bots, envs, last, errs, lat, late = [], [], [], [0] * len(specs), [[] for _ in specs], [0] * len(specs)
    for i, (label, path) in enumerate(specs):
        env = _env(path)
        hello = {"type": "hello", "protocol": "mechfight/1", "slot": i, "seed": match.rng.getrandbits(32),
                 "map": {"dir": ARENA.replace("\\", "/"), "files": hello0["map"]["files"]}, "config": cfg}
        try:
            b = env.make(hello)
        except Exception:
            traceback.print_exc()
            b = None
        bots.append(b)
        envs.append(env)
        last.append({})
    trace = []
    if trace_label is not None:
        trace_slot = next((i for i, (lab, _) in enumerate(specs) if lab == trace_label), None)
    while not match.over:
        acts = []
        for m in match.alive():
            obs = match.observe(m)
            b, env = bots[m.id], envs[m.id]
            a = None
            if b is not None:
                env.mf.draw.clear()
                t0 = time.perf_counter()
                try:
                    a = dict(b.act(obs) or {})
                    last[m.id] = {k: a[k] for k in _CONT if k in a}
                except Exception:
                    errs[m.id] += 1
                    if errs[m.id] <= 3:
                        traceback.print_exc()
                    a = dict(last[m.id])
                dt = time.perf_counter() - t0
                lat[m.id].append(dt)
                a["tick"] = obs["tick"]
                dbg = env.mf.draw.take()
                if m.id == trace_slot:
                    trace.append({"t": obs["t"], "pos": obs["self"]["pos"], "hp": obs["self"]["hp"],
                                  "energy": obs["self"]["energy"], "alive": obs["alive"],
                                  "label": (dbg or {}).get("label"), "act": {k: v for k, v in a.items() if k != "debug"},
                                  "mechs": [(x["id"], x.get("kind"), [round(v) for v in x["pos"]], x.get("hp"), x.get("weapons"))
                                            for x in obs.get("mechs", [])],
                                  "events": obs.get("events", []), "zone": obs["zone"],
                                  "weapons": [w and w.get("kind") for w in obs["self"].get("weapons") or []],
                                  "cubes": obs["self"].get("cubes")})
                if timing and dt > budget:
                    late[m.id] += 1
                    a = None
                else:
                    a = json.loads(json.dumps(a))
            acts.append((m, a))
        match.prune_sounds()
        for m, a in acts:
            match.apply_action(m, a)
        for _ in range(cfg["match"]["decide_every"]):
            match.step()
            if match.over:
                break
    places = match.places()
    rows = []
    for m in match.mechs:
        L = sorted(lat[m.id]) or [0.0]
        rows.append({"slot": m.id, "label": specs[m.id][0], "place": places[m.id], "kills": m.kills,
                     "cause": m.death_cause, "death_t": None if m.death_tick is None else round(m.death_tick * match.dt, 2),
                     "killed_by": specs[m.killed_by][0] if isinstance(m.killed_by, int) and 0 <= m.killed_by < len(specs) else m.killed_by,
                     "hp_before": m.hp_before_death, "dmg_taken": round(m.dmg_taken), "dmg_rear": round(m.dmg_rear),
                     "ticks_alive": m.ticks_alive, "ticks_out": m.ticks_out,
                     "cubes": getattr(m, "cubes", 0), "errors": errs[m.id], "late": late[m.id],
                     "ms_mean": round(1000 * sum(L) / len(L), 2), "ms_p99": round(1000 * L[int(0.99 * (len(L) - 1))], 2),
                     "ms_max": round(1000 * L[-1], 2),
                     "hp415": (match.hp_at_415 or {}).get(m.id)})
    return {"seed": seed, "t_end": round(match.t, 2), "rows": rows}, trace


def _job(arg):
    specs, seed, trace_slot, engine, trace_label = arg
    try:
        return play(specs, seed, trace_slot, engine=engine, trace_label=trace_label)
    except Exception:
        traceback.print_exc()
        return None, []


def summarize(results, n):
    by = {}
    for r in results:
        for row in r["rows"]:
            by.setdefault(row["label"], []).append(row)
    out = {}
    for lab, rs in by.items():
        k = len(rs)
        places = [r["place"] for r in rs]
        causes = {}
        for r in rs:
            if r["cause"]:
                causes[r["cause"]] = causes.get(r["cause"], 0) + 1
        dts = sorted(r["death_t"] for r in rs if r["death_t"] is not None)
        mean = sum(n - p for p in places) / k
        sd = math.sqrt(sum((n - p - mean) ** 2 for p in places) / max(1, k - 1))
        dmg = sum(r["dmg_taken"] for r in rs)
        out[lab] = {"n": k, "score": round(mean, 2), "se": round(sd / math.sqrt(k), 2),
                    "win%": round(100 * sum(p == 1 for p in places) / k, 1),
                    "top3%": round(100 * sum(p <= 3 for p in places) / k, 1),
                    "early_death%": round(100 * sum(1 for d in dts if d < 120) / k, 1),
                    "causes": causes, "kills": round(sum(r["kills"] for r in rs) / k, 2),
                    "rear%": round(100 * sum(r["dmg_rear"] for r in rs) / dmg, 1) if dmg else None,
                    "out%": round(100 * sum(r["ticks_out"] for r in rs) / max(1, sum(r["ticks_alive"] for r in rs)), 2),
                    "errors": sum(r["errors"] for r in rs), "late": sum(r["late"] for r in rs),
                    "ms_mean": round(sum(r["ms_mean"] for r in rs) / k, 2), "ms_max": max(r["ms_max"] for r in rs),
                    "death_t_median": dts[len(dts) // 2] if dts else None}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bot", action="append", required=True, help="LABEL=PATH (repeatable)")
    ap.add_argument("--count", action="append", type=int, default=[], help="slots for the bot at the same position")
    ap.add_argument("--matches", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--mechs", type=int, default=16)
    ap.add_argument("--rotate", action="store_true", help="rotate slot assignment per match (removes slot bias)")
    ap.add_argument("--trace", type=int, default=None, help="slot to trace (first match only, unless --trace-all)")
    ap.add_argument("--trace-out", default=None)
    ap.add_argument("--trace-label", default=None, help="trace the first slot with this label in every match")
    ap.add_argument("--out", default=None)
    ap.add_argument("--start", type=int, default=0, help="first match index (to replay one match of a batch)")
    ap.add_argument("--engine", default="engine", help="engine module in sim/ (engine_p1 = frozen phase 1)")
    a = ap.parse_args()
    specs = []
    for i, b in enumerate(a.bot):
        lab, _, path = b.partition("=")
        k = a.count[i] if i < len(a.count) else None
        specs.append((lab, os.path.join(REPO, path) if not os.path.isabs(path) else path, k))
    slots = []
    for lab, path, k in specs:
        slots += [(lab, path)] * (k or 1)
    slots = slots[:a.mechs]
    while len(slots) < a.mechs:
        slots.append(specs[-1][:2])
    jobs = []
    for k in range(a.start, a.start + a.matches):
        s = slots[k % len(slots):] + slots[:k % len(slots)] if a.rotate else slots
        jobs.append((s, a.seed * 100000 + k, a.trace if k == a.start else None, a.engine, a.trace_label))
    t0 = time.time()
    if a.jobs > 1 and len(jobs) > 1:
        with Pool(min(a.jobs, len(jobs))) as pool:
            res = pool.map(_job, jobs, chunksize=1)
    else:
        res = [_job(j) for j in jobs]
    results = [r for r, _ in res if r]
    if a.trace_label is not None and a.trace_out:
        with open(a.trace_out, "w") as f:
            for k, (r, tr) in enumerate(res):
                for row in tr:
                    row["match"] = k + a.start
                    f.write(json.dumps(row) + "\n")
    elif a.trace is not None and a.trace_out and res and res[0][1]:
        with open(a.trace_out, "w") as f:
            for row in res[0][1]:
                f.write(json.dumps(row) + "\n")
    summ = summarize(results, a.mechs)
    print(f"{len(results)}/{len(jobs)} matches in {time.time() - t0:.0f} s")
    for lab, s in sorted(summ.items(), key=lambda kv: -kv[1]["score"]):
        print(f"  {lab:>10}: " + " ".join(f"{k}={v}" for k, v in s.items()))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"summary": summ, "matches": results}, f, indent=1)


if __name__ == "__main__":
    main()
