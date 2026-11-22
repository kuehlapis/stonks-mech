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
LOS_CAP = 40             # F3 max los calls per search
WALL_SEARCH = 60.0       # m, radius of the wall-cell cover search
COVER_DZ = 2.5           # m, cover cells must be about our own height
URGENT_LOOK, URGENT_EDGE = 8.0, 10.0   # zone travel is urgent if the edge passes within 10 m of us in 8 s
URGENT_FACTOR, URGENT_SLACK = 1.5, 8.0  # ... or eta x 1.5 + 8 s reaches the deadline
HOLD_DEPTH = 0.85        # hold within this fraction of the clamped next radius (room for the next circle)
WALL_DETOUR = 60.0       # m of extra walking accepted to hold at a better (beside a wall, hidden) spot
HOLD_ROOF = 0.0          # m: if > 0, hold on roofs at least this high above the street (hunters must climb)
HOLD_EXPO_W = 1.0        # hold score = exposure x this + path metres / 100
HOLD_CANDS = 60          # wall cells considered for the hold point
HOLD_SEARCH_M = 300.0    # m, path search limit for the hold point
HOLD_FAR_M = 120.0       # m outside the clamped circle: walk the straight line first, search later
HOLD_NODES = 4000        # grid nodes, path search limit for the hold point
HOLD_SEARCH = False      # wall-side hold point search off: it took 50-62 ms worst case (> 50 ms budget)
FUNNEL = True  # R1: with >= FUNNEL_MIN hunters, take the wall cell the fewest of them can see
FUNNEL_MIN = 3
FUNNEL_K = 8             # nearest wall cells scored
FUNNEL_N = 5             # nearest hunters checked per cell (K x N <= LOS_CAP)
ZONE_LEAN = False        # R4: wait on the side of the next circle away from the visible hunters
CACHE_S, MOVE_M = 1.0, 10.0  # F3 cache life, threat move that invalidates it


def _stats(obs, cfg):
    return obs["self"].get("stats") or cfg["mech"]


class Survival:
    def __init__(self, cfg, world):
        self.cfg, self.world = cfg, world
        self.final_radius = cfg["zone"]["phases"][-1]["radius"]
        self._saved = None   # (shrink_start, center, radius) of the circle as it stood before the shrink
        self._cover = None   # (t, threat positions, result)
        self._hold = None    # (circle key, hold point)
        self._hold_fail = None  # (circle key, retry time) after a failed search
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
        """Where to wait for this circle: the nearest cell by walking path inside the clamped next circle,
        preferring one beside a building wall (half the directions covered). Cached per circle."""
        z, st = obs["zone"], _stats(obs, self.cfg)
        nc, pos = z["next_center"], obs["self"]["pos"]
        R = max(0.0, z["next_radius"] - st["radius"] - MARGIN_EXTRA)
        if R <= 0:
            return [nc[0], nc[1]]
        key = (round(nc[0], 1), round(nc[1], 1), z["next_radius"])
        h = self._hold
        if h and h[0] == key and math.hypot(h[1][0] - nc[0], h[1][1] - nc[1]) <= R:
            return h[1]
        nav = getattr(self, "nav", None)
        far = math.hypot(pos[0] - nc[0], pos[1] - nc[1]) - R > HOLD_FAR_M
        failed = self._hold_fail and self._hold_fail[0] == key and obs["t"] < self._hold_fail[1]
        if HOLD_SEARCH and nav is not None and not far and not failed:
            inner = R * HOLD_DEPTH
            first, cands = [], []

            def accept(x, y, wall, c, expo):
                if math.hypot(x - nc[0], y - nc[1]) > inner:
                    return False
                if HOLD_ROOF > 0:
                    sz = nav.surface(x, y)
                    if sz is not None and self.world is not None and sz - self.world.ground(x, y) >= HOLD_ROOF:
                        if not first:
                            first.append(([x, y], c))
                        cands.append((c / 100.0 - (sz - self.world.ground(x, y)) / 50.0, [x, y]))
                        return len(cands) >= HOLD_CANDS
                    if not first or c < first[0][1] + WALL_DETOUR * 3:
                        return False
                if not first:
                    first.append(([x, y], c))
                if wall and expo is not None:
                    cands.append((expo * HOLD_EXPO_W + c / 100.0, [x, y]))
                return c > first[0][1] + WALL_DETOUR or len(cands) >= HOLD_CANDS

            nav.search(pos[0], pos[1], accept, max_cost=HOLD_SEARCH_M, max_nodes=HOLD_NODES)
            if cands:
                p = min(cands)[1]
            elif first:
                p = first[0][0]
            else:
                p = None
            if p is not None:
                self._hold = (key, p)
                return p
            self._hold_fail = (key, obs["t"] + 3.0)
        return self._hold_line(obs, z, st, nc, pos)  # map-free (or search failed): nearest point on the line

    def _hold_line(self, obs, z, st, nc, pos):
        nc, pos = z["next_center"], obs["self"]["pos"]
        dx, dy = pos[0] - nc[0], pos[1] - nc[1]
        d = math.hypot(dx, dy)
        k = min(d, max(0.0, z["next_radius"] - st["radius"] - MARGIN_EXTRA))
        if d < 1e-9 or k <= 0:
            return [nc[0], nc[1]]
        ux, uy = dx / d, dy / d
        if ZONE_LEAN:
            hs = [m["pos"] for m in obs.get("mechs") or () if m.get("kind") == "mech" and m.get("pos")]
            if hs:
                ax = nc[0] - sum(h[0] for h in hs) / len(hs)
                ay = nc[1] - sum(h[1] for h in hs) / len(hs)
                a = math.hypot(ax, ay)
                if a > 1e-6:
                    vx, vy = ux + ax / a, uy + ay / a  # halfway between our side and the far side
                    v = math.hypot(vx, vy)
                    if v > 1e-6:
                        ux, uy = vx / v, vy / v
        w = self.world
        if w is None:
            return [nc[0] + ux * k, nc[1] + uy * k]
        for _ in range(SNAP_MAX):
            x, y = nc[0] + ux * k, nc[1] + uy * k
            if not w.blocked(x, y, w.ground(x, y), st["radius"], st["height"], st["step_up"]):
                return [x, y]
            k -= SNAP_STEP
            if k <= 0:
                break
        return [nc[0], nc[1]]

    def zone_goal(self, obs):
        z, me, st = obs["zone"], obs["self"], _stats(obs, self.cfg)
        pos, nc = me["pos"], z["next_center"]
        if not me.get("in_zone", True):
            c, r = self.live_circle(obs)
            eta = max(0.0, math.hypot(pos[0] - c[0], pos[1] - c[1]) - r) * PATH_FACTOR / st["walk_speed"]
            return self.hold_point(obs), z["dps"] * eta > BOOST_HP_FRAC * me["hp"]
        hp = self.hold_point(obs)
        # Inside the clamped next circle (or already at the hold point): nothing to do for the zone.
        if math.hypot(pos[0] - nc[0], pos[1] - nc[1]) <= max(0.0, z["next_radius"] - st["radius"] - MARGIN_EXTRA) \
                or math.hypot(pos[0] - hp[0], pos[1] - hp[1]) <= 2.0:
            return None
        # Not in the plan: boost if walking would miss the deadline (shrink_start, or shrink_end once shrinking).
        deadline = z["shrink_start"] if obs["t"] < z["shrink_start"] else z["shrink_end"]
        eta = math.hypot(pos[0] - hp[0], pos[1] - hp[1]) * PATH_FACTOR / st["walk_speed"]
        return hp, eta > deadline - obs["t"]

    def circle_at(self, obs, t):
        """(center, radius) of the circle at a future time t, from the saved pre-shrink circle."""
        z = obs["zone"]
        self.live_circle(obs)  # refreshes the saved circle
        _, c0, r0 = self._saved
        span = z["shrink_end"] - z["shrink_start"]
        s = 0.0 if t <= z["shrink_start"] else 1.0 if span <= 0 or t >= z["shrink_end"] else (t - z["shrink_start"]) / span
        nc = z["next_center"]
        return [c0[0] + (nc[0] - c0[0]) * s, c0[1] + (nc[1] - c0[1]) * s], r0 + (z["next_radius"] - r0) * s

    def zone_urgent(self, obs, goal=None):
        """True when zone travel must outrank fighting: outside now, the live edge reaches us within
        URGENT_LOOK s, or walking to the goal would miss the deadline (with slack)."""
        z, me, st = obs["zone"], obs["self"], _stats(obs, self.cfg)
        if not me.get("in_zone", True):
            return True
        pos, t = me["pos"], obs["t"]
        c, r = self.circle_at(obs, t + URGENT_LOOK)
        if math.hypot(pos[0] - c[0], pos[1] - c[1]) > r - URGENT_EDGE:
            return True
        if goal is None:
            return False
        deadline = z["shrink_start"] if t < z["shrink_start"] else z["shrink_end"]
        eta = math.hypot(pos[0] - goal[0], pos[1] - goal[1]) * PATH_FACTOR / st["walk_speed"]
        return eta * URGENT_FACTOR + URGENT_SLACK >= deadline - t

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

    def _hidden(self, p, checks):
        """True if no threat eye in `checks` sees p's center or top. Counts los calls."""
        w = self.world
        for e, h in checks:
            self.los_calls += 1
            if w.los(e, (p[0], p[1], p[2] + h)):
                return False
        return True

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
        checks = [((p[0], p[1], p[2] + eye), h) for p in tps for h in (st["height"] / 2, st["height"])]
        self.los_calls = 0
        # 1. Keep the last cover point while it is still hidden and inside (no thrashing between points).
        prev = c[2] if c else None
        if prev and math.hypot(prev[0] - cc[0], prev[1] - cc[1]) <= cr - 5 \
                and math.hypot(prev[0] - pos[0], prev[1] - pos[1]) <= WALL_SEARCH and self._hidden(prev, checks):
            self._cover = (t, tps, prev)
            return prev
        nav = getattr(self, "nav", None)
        best = self._funnel(obs, tps, st, eye, pos, cc, cr, nav) if FUNNEL and nav is not None else None
        if best is not None:
            self._cover = (t, tps, best)
            return best
        # 2. Wall cells whose building lies between the cell and the main threat (its shadow side).
        if nav is not None:
            tx, ty = tps[0][0], tps[0][1]
            cands = []
            for x, y, gz, nx, ny in nav.wall_cells(pos[0], pos[1], WALL_SEARCH):
                if math.hypot(x - cc[0], y - cc[1]) > cr - 5 or abs(gz - pos[2]) > COVER_DZ:
                    continue  # no climbing onto roofs for cover: exposed and slow
                dx, dy = tx - x, ty - y
                dt = math.hypot(dx, dy) or 1.0
                if nx * dx + ny * dy < 0.3 * dt:
                    continue
                d = math.hypot(x - pos[0], y - pos[1])
                cands.append((d + max(0.0, 60.0 - dt), x, y, gz))
            cands.sort()
            for _, x, y, gz in cands:
                if self.los_calls + len(checks) > LOS_CAP:
                    break
                if self._hidden((x, y, gz), checks):
                    best = [x, y, gz]
                    break
        if best is None:
            best = self._ring_cover(obs, tps, st, eye, pos, cc, cr, checks)
        self._cover = (t, tps, best)
        return best

    def _funnel(self, obs, tps, st, eye, pos, cc, cr, nav):
        """R1: among the FUNNEL_K nearest wall cells facing away from the hunters' centroid, the one the
        fewest of the FUNNEL_N nearest hunters can see (score = seen x 100 + m). None if > 2 see the best."""
        if len(tps) < FUNNEL_MIN:
            return None
        hs = sorted(tps, key=lambda p: math.hypot(p[0] - pos[0], p[1] - pos[1]))[:FUNNEL_N]
        mx, my = sum(p[0] for p in tps) / len(tps), sum(p[1] for p in tps) / len(tps)
        cands = []
        for x, y, gz, nx, ny in nav.wall_cells(pos[0], pos[1], WALL_SEARCH):
            if math.hypot(x - cc[0], y - cc[1]) > cr - 5 or abs(gz - pos[2]) > COVER_DZ:
                continue
            if nx * (mx - x) + ny * (my - y) <= 0:
                continue  # normal points into the building (as in find_cover): building between cell and hunters
            cands.append((math.hypot(x - pos[0], y - pos[1]), x, y, gz))
        cands.sort()
        best, h2 = None, st["height"] / 2
        for d, x, y, gz in cands[:FUNNEL_K]:
            if self.los_calls + len(hs) > LOS_CAP:
                break
            seen = 0
            for p in hs:
                self.los_calls += 1
                seen += bool(self.world.los((p[0], p[1], p[2] + eye), (x, y, gz + h2)))
            sc = seen * 100 + d
            if seen <= 2 and (best is None or sc < best[0]):
                best = (sc, [x, y, gz])
        return best[1] if best else None

    def _ring_cover(self, obs, tps, st, eye, pos, cc, cr, checks):
        w = self.world
        # Within a ring, try directions away from the first (strongest) threat first.
        ax, ay = pos[0] - tps[0][0], pos[1] - tps[0][1]
        cands = sorted(((ring, a) for ring in RINGS for a in range(8)),
                       key=lambda ra: (ra[0], -math.cos(ra[1] * math.pi / 4 - math.atan2(ay, ax))))
        for ring, a in cands:
            x, y = pos[0] + ring * math.cos(a * math.pi / 4), pos[1] + ring * math.sin(a * math.pi / 4)
            if math.hypot(x - cc[0], y - cc[1]) > cr:
                continue
            gz = w.ground(x, y)
            if w.blocked(x, y, gz, st["radius"], st["height"], st["step_up"]):
                continue
            if self.los_calls + len(checks) > LOS_CAP:
                break  # not enough budget left to verify this point
            if self._hidden((x, y, gz), checks):
                return [x, y, gz]
        return None

    def final_center(self, obs):
        z = obs["zone"]
        return list(z["next_center"][:2]) if z["next_radius"] <= self.final_radius else None
