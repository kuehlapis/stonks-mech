"""Local match runner for mechfight/1 (phase 2: full rules). Usage:

  python sim/run.py --matches 10 --seed 1 --jobs 8 --bot "python -u python/example_bot.py" [--bot CMD ...] [--out summary.json]

`--jobs N` plays N matches at once in separate processes (each match runs 16 bot processes, so keep
N * 16 bots within what the machine can answer in 50 ms; check `late_pct`).

Bots fill slots in the order given. `--count K` after a --bot gives it K slots (default 1); the last --bot
fills any slots left, so `--bot NEW --bot OLD` is 1 NEW against 15 OLD, and
`--bot A --count 4 --bot B --count 4 --bot C` is 4 A, 4 B and 8 C.
"""
import argparse
import concurrent.futures
import gzip
import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "python"))
from engine import Match  # noqa: E402

ARENA = os.path.join(REPO, "arena")


def load_world():
    try:
        from world import World
        return World(ARENA), "python/world.py"
    except Exception as e:  # shortcut: flat stub until world.py loads; geometry-free numbers are optimistic
        print(f"world.py failed ({e!r}); using a flat world", file=sys.stderr)
        return FlatWorld(), "flat stub"


class FlatWorld:
    canopy = None  # no trees
    def __init__(self):
        with open(os.path.join(ARENA, "v2", "world.json"), encoding="utf-8") as f:
            b = json.load(f)["bounds"]
        self.bounds = (b["minX"], b["minY"], b["maxX"], b["maxY"])

    def ground(self, x, y): return 0.0
    def top(self, x, y, z): return 0.0
    def solid(self, x, y, z): return z < 0
    def los(self, a, b): return a[2] >= 0 and b[2] >= 0
    def blocked(self, x, y, z, radius, height, step=1.2): return False


def recorded_hello():
    with gzip.open(os.path.join(REPO, "check", "stream.jsonl.gz"), "rt") as f:
        return json.loads(f.readline())


def argv_of(cmd):
    a = shlex.split(cmd)
    if a and a[0] in ("python", "python3"):
        a[0] = sys.executable
    return a


class Bot:
    def __init__(self, cmd, log_path):
        self.cmd, self.log_path = cmd, log_path
        self.log = open(log_path, "wb")
        self.p = subprocess.Popen(argv_of(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, cwd=REPO)
        self.q = queue.Queue()
        self.dead = False
        self.bad = self.late = self.answered = 0
        self.lat = []
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            self.q.put((time.perf_counter(), line))
        self.q.put((time.perf_counter(), None))

    def send(self, msg):
        if self.dead:
            return
        try:
            self.p.stdin.write((json.dumps(msg, separators=(",", ":")) + "\n").encode())
            self.p.stdin.flush()
        except OSError:
            self.dead = True

    def recv(self, deadline, want):
        """First message matching want(msg) before deadline, else None. Stale or bad lines are dropped."""
        while True:
            try:
                ts, line = self.q.get(timeout=max(0.0, deadline - time.perf_counter()))
            except queue.Empty:
                return None, None
            if line is None:
                self.dead = True
                return None, None
            if len(line) > 65536:
                self.bad += 1
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                self.bad += 1
                continue
            if isinstance(msg, dict) and want(msg):
                return msg, ts

    def close(self):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        try:
            self.p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.p.kill()
        self.log.close()
        with open(self.log_path, "rb") as f:
            self.exceptions = f.read().count(b"Traceback")


def play(cmds, cfg, world, seed, log_dir):
    hello = recorded_hello()
    eng = 0.0
    match = Match(cfg, world, seed, len(cmds))
    bots = [Bot(c, os.path.join(log_dir, f"m{seed}-slot{i}.log")) for i, c in enumerate(cmds)]
    for i, b in enumerate(bots):
        b.send({"type": "hello", "protocol": "mechfight/1", "slot": i, "seed": match.rng.getrandbits(32),
                "map": {"dir": ARENA.replace("\\", "/"), "files": hello["map"]["files"]}, "config": cfg})
    deadline = time.perf_counter() + cfg["bot"]["hello_budget_ms"] / 1000
    for b in bots:
        msg, _ = b.recv(deadline, lambda m: m.get("type") == "ready")
        if msg is None:
            b.dead = True  # never ready: idles all match
    budget = cfg["bot"]["tick_budget_ms"] / 1000
    t0 = time.perf_counter()
    decisions = 0
    while not match.over:
        sent = {}
        for m in match.alive():
            b = bots[m.id]
            e0 = time.perf_counter()
            obs = match.observe(m)
            eng += time.perf_counter() - e0
            if not b.dead:
                b.send(obs)
                sent[m.id] = time.perf_counter()
        match.prune_sounds()
        deadline = time.perf_counter() + budget
        tick = match.tick
        for m in match.alive():
            b, a = bots[m.id], None
            if m.id in sent:
                a, ts = b.recv(deadline, lambda msg: msg.get("tick") == tick and "type" not in msg)
                if a is None:
                    b.late += 1
                else:
                    b.answered += 1
                    b.lat.append(ts - sent[m.id])
            match.apply_action(m, a)
        e0 = time.perf_counter()
        for _ in range(cfg["match"]["decide_every"]):
            match.step()
            if match.over:
                break
        eng += time.perf_counter() - e0
        decisions += 1
    wall = time.perf_counter() - t0
    places = match.places()
    for m in match.mechs:
        bots[m.id].send({"type": "end", "place": places[m.id], "kills": m.kills})
    for b in bots:
        b.close()
    rows = []
    for m in match.mechs:
        b = bots[m.id]
        rows.append({"slot": m.id, "cmd": b.cmd, "place": places[m.id], "kills": m.kills, "cause": m.death_cause,
                     "ticks_alive": m.ticks_alive, "ticks_out": m.ticks_out, "dmg_taken": m.dmg_taken,
                     "dmg_rear": m.dmg_rear, "shots_mid": m.shots_mid, "hits_mid": m.hits_mid,
                     "hp_at_3": (match.hp_at_3 or {}).get(m.id), "hp_at_415": (match.hp_at_415 or {}).get(m.id),
                     "death": None if m.death_tick is None else {
                         "t": round(m.death_tick * match.dt, 2), "cause": m.death_cause, "by_slot": m.killed_by,
                         "by_cmd": None if m.killed_by is None else bots[m.killed_by].cmd if m.killed_by < len(bots) else "npc",
                         "hp_before": m.hp_before_death, "pos": m.death_pos},
                     "cubes_final": m.cubes_final if m.cubes_final is not None else m.cubes,
                     "weapons_final": m.weapons_final if m.weapons_final is not None else m.held_kinds(),
                     "kinds_taken": m.kinds_taken, "upgrades": m.upgrades,
                     "dmg_dealt_by": {k: round(v, 1) for k, v in m.dmg_dealt_by.items()},
                     "dmg_taken_by": {k: round(v, 1) for k, v in m.dmg_taken_by.items()},
                     "drops_captured": m.drops_captured, "npc_kills": m.npc_kills, "crates_broken": m.crates_broken,
                     "late": b.late, "answered": b.answered,
                     "bad": b.bad, "exceptions": b.exceptions,
                     "lat_max_ms": round(max(b.lat) * 1000, 1) if b.lat else None})
    return {"seed": seed, "t_end": round(match.t, 2), "wall_s": round(wall, 2), "decisions": decisions,
            "ms_per_decision": round(wall / max(1, decisions) * 1000, 2),
            "engine_ms_per_decision": round(eng / max(1, decisions) * 1000, 2), "mechs": rows}


def summarize(matches, n_mechs):
    by = {}
    for mt in matches:
        for r in mt["mechs"]:
            r["seed"] = mt["seed"]
            by.setdefault(r["cmd"], []).append(r)
    out = {}
    for cmd, rs in by.items():
        n = len(rs)
        ta = sum(r["ticks_alive"] for r in rs)
        dmg = sum(r["dmg_taken"] for r in rs)
        shots = sum(r["shots_mid"] for r in rs)
        h3 = [r["hp_at_3"] for r in rs if r["hp_at_3"] is not None]
        h415 = [r["hp_at_415"] for r in rs if r["hp_at_415"] is not None]
        ans = sum(r["answered"] + r["late"] for r in rs)
        out[cmd] = {
            "mech_matches": n,
            "mean_score": round(sum(n_mechs - r["place"] for r in rs) / n, 2),
            "mean_place": round(sum(r["place"] for r in rs) / n, 2),
            "win_rate": round(sum(r["place"] == 1 for r in rs) / n, 3),
            "zone_deaths_pct": round(100 * sum(r["cause"] == "zone" for r in rs) / n, 1),
            "ticks_outside_zone_pct": round(100 * sum(r["ticks_out"] for r in rs) / max(1, ta), 2),
            "rear_hit_damage_share_pct": round(100 * sum(r["dmg_rear"] for r in rs) / dmg, 1) if dmg else None,
            "gun_hit_rate_50_150_pct": round(100 * sum(r["hits_mid"] for r in rs) / shots, 1) if shots else None,
            "gun_shots_50_150": shots,
            "hp_at_le3_alive_pct": round(100 * sum(h3) / len(h3), 1) if h3 else None,
            "hp_at_le3_samples": len(h3),
            "hp_at_415s_survivors_pct": round(100 * sum(h415) / len(h415), 1) if h415 else None,
            "hp_at_415s_samples": len(h415),
            "deaths": [dict(r["death"], match_seed=r["seed"], slot=r["slot"], place=r["place"]) for r in rs if r["death"]],
            "late_pct": round(100 * sum(r["late"] for r in rs) / max(1, ans), 3),
            "bad_lines": sum(r["bad"] for r in rs),
            "exceptions": sum(r["exceptions"] for r in rs),
            "kills_per_match": round(sum(r["kills"] for r in rs) / n, 2),
            "mean_cubes_at_death_or_end": round(sum(r["cubes_final"] for r in rs) / n, 2),
            "weapons_held_at_death_or_end_pct": {k: round(100 * sum(k in r["weapons_final"] for r in rs) / n, 1)
                                                 for k in ("gun", "mortar", "laser", "lightning")},
            "pickups_taken_per_match": round(sum(len(r["kinds_taken"]) for r in rs) / n, 2),
            "dmg_dealt_per_match_by_weapon": _mean_dict([r["dmg_dealt_by"] for r in rs], n),
            "dmg_taken_per_match_by_weapon": _mean_dict([r["dmg_taken_by"] for r in rs], n),
            "deaths_by_cause": _count(r["cause"] for r in rs if r["cause"]),
            "drops_captured": sum(r["drops_captured"] for r in rs),
            "npc_kills_per_match": round(sum(r["npc_kills"] for r in rs) / n, 2),
            "crates_broken_per_match": round(sum(r["crates_broken"] for r in rs) / n, 2),
            "upgrades_taken": _count(u for r in rs for u in r["upgrades"]),
        }
    return out


def _mean_dict(ds, n):
    out = {}
    for d in ds:
        for k, v in d.items():
            out[k] = out.get(k, 0.0) + v
    return {k: round(v / n, 1) for k, v in sorted(out.items())}


def _count(it):
    out = {}
    for k in it:
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


_WORLD = None


def _job(cmds, cfg, seed, log_dir):
    """Worker entry: one match. The world loads once per worker process."""
    global _WORLD
    if _WORLD is None:
        _WORLD = load_world()[0]
    return play(cmds, cfg, _WORLD, seed, log_dir)


class BotArg(argparse.Action):
    def __call__(self, parser, ns, value, option=None):
        ns.bots = (ns.bots or []) + [[value, None]]


class CountArg(argparse.Action):
    def __call__(self, parser, ns, value, option=None):
        if not ns.bots or value < 1:
            parser.error("--count needs a preceding --bot and a value >= 1")
        ns.bots[-1][1] = value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bot", action=BotArg, required=True, dest="bots", help="bot command line (repeatable)")
    ap.add_argument("--count", action=CountArg, dest="bots", type=int, help="slots for the preceding --bot")
    ap.add_argument("--matches", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mechs", type=int, default=None, help="mechs per match (default: config match.mechs = 16)")
    ap.add_argument("--out", help="write the JSON summary here")
    ap.add_argument("--jobs", type=int, default=1, help="matches played in parallel processes (default 1)")
    args = ap.parse_args()
    cfg = recorded_hello()["config"]
    n = args.mechs or cfg["match"]["mechs"]
    cmds = [c for c, k in args.bots for _ in range(k or 1)]
    if len(cmds) > n:
        ap.error(f"{len(cmds)} bots for {n} slots")
    cmds += [args.bots[-1][0]] * (n - len(cmds))
    log_dir = tempfile.mkdtemp(prefix="mechsim-")
    seeds = [args.seed * 1000 + k for k in range(args.matches)]
    matches = []

    def report(mt):
        matches.append(mt)
        order = sorted(mt["mechs"], key=lambda r: r["place"])
        print(f"match {len(matches)}/{args.matches} seed {mt['seed']}: ended t={mt['t_end']} s, wall {mt['wall_s']} s, "
              f"{mt['ms_per_decision']} ms/decision (engine {mt['engine_ms_per_decision']})")
        print("  " + " ".join(f"{r['place']}:s{r['slot']}{'/' + r['cause'][:2] if r['cause'] else ''}" for r in order))
        sys.stdout.flush()

    if args.jobs <= 1:
        world, world_name = load_world()
        for sd in seeds:
            report(play(cmds, cfg, world, sd, log_dir))
    else:
        world_name = "python/world.py"
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futs = [ex.submit(_job, cmds, cfg, sd, log_dir) for sd in seeds]
            for f in concurrent.futures.as_completed(futs):
                report(f.result())
    matches.sort(key=lambda mt: mt["seed"])
    eng = [mt["engine_ms_per_decision"] for mt in matches]
    summary = {"world": world_name, "matches": args.matches, "seed": args.seed, "mechs": n, "bot_logs": log_dir,
               "jobs": args.jobs, "engine_ms_per_decision_mean": round(sum(eng) / len(eng), 2),
               "engine_ms_per_decision_max": max(eng),
               "per_bot": summarize(matches, n), "per_match": matches}
    print(json.dumps({k: v for k, v in summary.items() if k != "per_match"}, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(summary, f, indent=1)


if __name__ == "__main__":
    main()
