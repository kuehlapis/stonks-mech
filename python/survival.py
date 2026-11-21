"""Survival: zone timing (Z1), hold point (Z2), hold facing (Z4), cover search (F3 step 1), final center (EG2).
Rule ids refer to notes/ideas/game-plan.md. Contract: notes/interfaces.md "M1 modules"."""
import math

# Tuning constants from the game plan (not rule values; those come from cfg / obs.self.stats).
MARGIN_EXTRA = 12.0      # margin = stats.radius + 12 (§1)
SNAP_STEP, SNAP_MAX = 2.0, 30   # Z2 snap off buildings
PATH_FACTOR = 1.3        # eta = straight distance x 1.3 until nav gives path lengths (§1)
BOOST_HP_FRAC = 0.2      # Z1: boost if dps x eta > 0.2 x hp
EDGE_FACE = 30.0         # Z4: face outward while the live edge is more than 30 m away
SWEEP = math.radians(60)  # Z4 outward sweep half-width
SWEEP_PERIOD = 4.0       # s per full sweep (our choice; turn_rate 4 rad/s covers 120 deg in 0.5 s)
RINGS = (15.0, 30.0)     # F3 candidate rings
LOS_CAP = 32             # F3 max los calls per search
CACHE_S, MOVE_M = 1.0, 10.0  # F3 cache life, threat move that invalidates it


def _stats(obs, cfg):
    return obs["self"].get("stats") or cfg["mech"]


class Survival:
    def __init__(self, cfg, world):
        self.cfg, self.world = cfg, world
        self.final_radius = cfg["zone"]["phases"][-1]["radius"]
        self._saved = None   # (shrink_start, center, radius) of the circle as it stood before the shrink
        self._cover = None   # (t, threat positions, result)
        self._hold = None    # (next-circle key, stable hold point) to keep Nav's goal from oscillating
        self.los_calls = 0   # los calls made by the last find_cover search (tests read it)

    def live_circle(self, obs):
        """(center, radius) of the circle now, interpolated only from values saved before shrink_start (Z1)."""
        z, t = obs["zone"], obs["t"]
        # Mid-shrink with nothing saved (first obs late): obs.zone.center may already be moving; best guess we have.
        if t < z["shrink_start"] or not (self._saved and self._saved[0] == z["shrink_start"]):
            self._saved = (z["shrink_start"], list(z["center"]), z["radius"])
        _, c0, r0 = self._saved
        span = z["shrink_end"] - z["shrink_start"]
        s = 0.0 if t <= z["shrink_start"] else 1.0 if span <= 0 or t >= z["shrink_end"] else (t - z["shrink_start"]) / span
        nc = z["next_center"]
        return [c0[0] + (nc[0] - c0[0]) * s, c0[1] + (nc[1] - c0[1]) * s], r0 + (z["next_radius"] - r0) * s

    def hold_point(self, obs):
        z, st = obs["zone"], _stats(obs, self.cfg)
        nc, pos = z["next_center"], obs["self"]["pos"]
        dx, dy = pos[0] - nc[0], pos[1] - nc[1]
        d = math.hypot(dx, dy)
        limit = max(0.0, z["next_radius"] - st["radius"] - MARGIN_EXTRA)
        if d <= limit:
            self._hold = None
            return [pos[0], pos[1]]
        key = (tuple(nc[:2]), z["next_radius"], st["radius"])
        if self._hold and self._hold[0] == key:
            return list(self._hold[1])
        k = min(d, limit)
        if d < 1e-9 or k <= 0:
            return [nc[0], nc[1]]
        ux, uy = dx / d, dy / d
        w = self.world
        if w is None:
            p = [nc[0] + ux * k, nc[1] + uy * k]
            self._hold = (key, p)
            return p
        for _ in range(SNAP_MAX):
            x, y = nc[0] + ux * k, nc[1] + uy * k
            if not w.blocked(x, y, w.ground(x, y), st["radius"], st["height"], st["step_up"]):
                p = [x, y]
                self._hold = (key, p)
                return p
            k -= SNAP_STEP
            if k <= 0:
                break
        p = [nc[0], nc[1]]
        self._hold = (key, p)
        return p

    def zone_goal(self, obs):
        z, me, st = obs["zone"], obs["self"], _stats(obs, self.cfg)
        pos, nc = me["pos"], z["next_center"]
        if not me.get("in_zone", True):
            c, r = self.live_circle(obs)
            eta = max(0.0, math.hypot(pos[0] - c[0], pos[1] - c[1]) - r) * PATH_FACTOR / st["walk_speed"]
            return [nc[0], nc[1]], z["dps"] * eta > BOOST_HP_FRAC * me["hp"]
        hp = self.hold_point(obs)
        # Inside the clamped next circle (or already at the hold point): nothing to do for the zone.
        if math.hypot(pos[0] - nc[0], pos[1] - nc[1]) <= max(0.0, z["next_radius"] - st["radius"] - MARGIN_EXTRA) \
                or math.hypot(pos[0] - hp[0], pos[1] - hp[1]) <= 2.0:
            return None
        # Not in the plan: boost if walking would miss the deadline (shrink_start, or shrink_end once shrinking).
        deadline = z["shrink_start"] if obs["t"] < z["shrink_start"] else z["shrink_end"]
        eta = math.hypot(pos[0] - hp[0], pos[1] - hp[1]) * PATH_FACTOR / st["walk_speed"]
        return hp, eta > deadline - obs["t"]

    def hold_facing(self, obs):
        pos, nc = obs["self"]["pos"], obs["zone"]["next_center"]
        dx, dy = pos[0] - nc[0], pos[1] - nc[1]
        if math.hypot(dx, dy) < 1e-6:
            return obs["self"]["aim"][0]
        out = math.atan2(dy, dx)
        c, r = self.live_circle(obs)
        if math.hypot(pos[0] - c[0], pos[1] - c[1]) <= r - EDGE_FACE:
            y = out + SWEEP * math.sin(2 * math.pi * obs["t"] / SWEEP_PERIOD)
        else:
            y = out + math.pi
        return math.atan2(math.sin(y), math.cos(y))

    def find_cover(self, obs, threats):
        w = self.world
        tps = [list(th["pos"]) for th in threats if th.get("pos")]
        if w is None or not tps:
            return None
        t = obs["t"]
        c = self._cover
        if c and t - c[0] < CACHE_S and len(c[1]) == len(tps) and all(
                math.hypot(a[0] - b[0], a[1] - b[1]) <= MOVE_M for a, b in zip(c[1], tps)):
            return c[2]
        st = _stats(obs, self.cfg)
        eye = st["eye_height"]
        pos = obs["self"]["pos"]
        cc, cr = self.live_circle(obs)
        # Within a ring, try directions away from the first (strongest) threat first.
        ax, ay = pos[0] - tps[0][0], pos[1] - tps[0][1]
        cands = sorted(((ring, a) for ring in RINGS for a in range(8)),
                       key=lambda ra: (ra[0], -math.cos(ra[1] * math.pi / 4 - math.atan2(ay, ax))))
        checks = [((p[0], p[1], p[2] + eye), h) for p in tps for h in (st["height"] / 2, st["height"])]
        calls, best = 0, None
        for ring, a in cands:
            x, y = pos[0] + ring * math.cos(a * math.pi / 4), pos[1] + ring * math.sin(a * math.pi / 4)
            if math.hypot(x - cc[0], y - cc[1]) > cr:
                continue
            gz = w.ground(x, y)
            if w.blocked(x, y, gz, st["radius"], st["height"], st["step_up"]):
                continue
            if calls + len(checks) > LOS_CAP:
                break  # not enough budget left to verify this point
            ok = True
            for e, h in checks:
                calls += 1
                if w.los(e, (x, y, gz + h)):
                    ok = False
                    break
            if ok:
                best = [x, y, gz]
                break
        self.los_calls = calls
        self._cover = (t, tps, best)
        return best

    def final_center(self, obs):
        z = obs["zone"]
        return list(z["next_center"][:2]) if z["next_radius"] <= self.final_radius else None
