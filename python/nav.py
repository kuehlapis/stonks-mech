"""Navigation: grid A* around buildings plus the N1 stuck rule (notes/interfaces.md, game-plan §3 N1)."""
import heapq
import math
import time

CELL = 4.0           # grid cell (m); full map grid builds in about 0.5 s
ARRIVE = 2.0         # arrived within this horizontal distance (m)
STUCK_WINDOW = 2.0   # N1: progress window (s)
STUCK_PROGRESS = 3.0 # N1: minimum progress in the window (m)
JET_ENERGY = 40.0    # N1: jet only with at least this much energy
SIDE_WALK = 10.0     # N1: walk this far along the wall (m)
REPLAN_MOVE = 4.0    # replan when the goal moves this far (m)
REPLAN_EVERY = 0.5   # at most one new search per this many seconds
SEARCH_MS = 2.0      # A* time slice per step (ms); the search continues next step
LOOKAHEAD = 8        # path nodes considered for the steering point
SNAP = 10            # cells searched for the nearest free cell
DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


class Nav:
    def __init__(self, cfg, world):
        m = (cfg or {}).get("mech", {})
        self._m = m
        self._step_speed = float((cfg or {}).get("sound", {}).get("step_speed", 5))
        # jet reach: a full tank at max rise speed, 10% margin (towers are 67+ m, the highest roof 49.5 m)
        self._reach = 0.9 * float(m.get("energy", 100)) / float(m.get("jet_drain", 15)) * float(m.get("max_rise_speed", 10))
        self.world = world
        self._goal = None        # goal the current plan is for
        self._target = None      # goal, or the free point next to it when it is out of jet reach
        self._path = []          # [(x, y)] ending at the target
        self._suffix = []        # remaining path length after each node
        self._i = 0
        self._search = None
        self._plan_t = -1e9
        self._stage = 0          # 0 walk, 1 jump+jet, 2 walk along the wall
        self._win = None         # (t, remaining) at the start of the stuck window
        self._side = 1           # +1 left, -1 right
        self._side_from = None
        self._stage_t = 0.0
        if world is not None:
            try:
                self._build(world)
            except Exception:
                self.world = None

    # ---- grid -------------------------------------------------------------
    def _build(self, w):
        x0, y0, x1, y1 = w.bounds
        self._x0, self._y0 = x0, y0
        self._nx, self._ny = int((x1 - x0) // CELL), int((y1 - y0) // CELL)
        r = float(self._m.get("radius", 2.5))
        h = float(self._m.get("height", 9))
        step = float(self._m.get("step_up", 1.2))
        edge = r + 0.5
        free = bytearray(self._nx * self._ny)
        g = [0.0] * (self._nx * self._ny)
        for j in range(self._ny):
            y = y0 + (j + 0.5) * CELL
            for i in range(self._nx):
                x = x0 + (i + 0.5) * CELL
                k = j * self._nx + i
                z = g[k] = w.ground(x, y)
                # the map edge is a wall (blocked() ignores it)
                if x - x0 > edge and x1 - x > edge and y - y0 > edge and y1 - y > edge and not w.blocked(x, y, z, r, h, step):
                    free[k] = 1
        self._free, self._g = free, g
        self._climb = math.tan(math.radians(float(self._m.get("max_slope_deg", 50)))) * CELL

    def _cell(self, x, y):
        return int((x - self._x0) // CELL), int((y - self._y0) // CELL)

    def _ok(self, i, j):
        return 0 <= i < self._nx and 0 <= j < self._ny and self._free[j * self._nx + i]

    def _center(self, i, j):
        return (self._x0 + (i + 0.5) * CELL, self._y0 + (j + 0.5) * CELL)

    def _snap(self, x, y):
        """Nearest free cell to (x, y), or None."""
        ci, cj = self._cell(x, y)
        if self._ok(ci, cj):
            return ci, cj
        best = None
        for rr in range(1, SNAP + 1):
            for i in range(ci - rr, ci + rr + 1):
                for j in (cj - rr, cj + rr) if abs(i - ci) < rr else range(cj - rr, cj + rr + 1):
                    if self._ok(i, j):
                        cx, cy = self._center(i, j)
                        d = (cx - x) ** 2 + (cy - y) ** 2
                        if best is None or d < best[0]:
                            best = (d, i, j)
            if best:
                return best[1], best[2]
        return None

    def _clear(self, a, b):
        """Straight walk a→b stays on free cells (samples every 1 m)."""
        n = int(math.hypot(b[0] - a[0], b[1] - a[1])) + 1
        for s in range(1, n + 1):
            f = s / n
            if not self._ok(*self._cell(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)):
                return False
        return True

    def _astar(self, start, goal):
        """Generator: yields None while working (time-sliced), then the cell path or []."""
        nx, free, g, climb = self._nx, self._free, self._g, self._climb
        si, sj = start
        gi, gj = goal
        s, e = sj * nx + si, gj * nx + gi
        cost = {s: 0.0}
        came = {s: -1}
        heap = [(0.0, s)]
        n = 0
        deadline = time.perf_counter() + SEARCH_MS / 1000
        while heap:
            n += 1
            if n % 64 == 0 and time.perf_counter() > deadline:
                yield None
                deadline = time.perf_counter() + SEARCH_MS / 1000
            _, k = heapq.heappop(heap)
            if k == e:
                out = []
                while k != -1:
                    out.append((k % nx, k // nx))
                    k = came[k]
                yield out[::-1]
                return
            i, j = k % nx, k // nx
            ck = cost[k]
            for di, dj, dc in DIRS:
                a, b = i + di, j + dj
                if not self._ok(a, b) or (di and dj and not (free[j * nx + a] and free[b * nx + i])):
                    continue
                q = b * nx + a
                if g[q] - g[k] > climb * dc:  # too steep to walk up
                    continue
                c = ck + dc
                if c < cost.get(q, 1e18):
                    cost[q] = c
                    came[q] = k
                    dx, dy = abs(a - gi), abs(b - gj)
                    heapq.heappush(heap, (c + max(dx, dy) + 0.4142 * min(dx, dy), q))
        yield []

    # ---- planning ---------------------------------------------------------
    def _plan(self, pos, goal, t):
        self._goal, self._plan_t = goal, t
        self._target, self._search = goal, None
        if self.world is None:
            self._set_path([goal])
            return
        gc = self._snap(goal[0], goal[1])
        if gc and self.world.top(goal[0], goal[1], 1e4) - self.world.ground(goal[0], goal[1]) > self._reach:
            self._target = self._center(*gc)  # out of jet reach (dorm towers, chimneys): stop beside it
        sc = self._snap(pos[0], pos[1])
        if gc and sc:
            self._search = self._astar(sc, gc)
        self._set_path([self._target])  # walk straight while the search runs (a few steps)

    def _set_path(self, pts):
        self._path, self._i = pts, 0
        suf = [0.0] * len(pts)
        for k in range(len(pts) - 2, -1, -1):
            suf[k] = suf[k + 1] + math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
        self._suffix = suf

    def _advance_search(self):
        if self._search is None:
            return
        r = next(self._search, [])
        if r is None:
            return
        self._search, self._win = None, None  # path length differs from the straight distance
        self._set_path([self._center(i, j) for i, j in r[1:]] + [self._target])

    def _remaining(self, p):
        q = self._path[self._i]
        return math.hypot(q[0] - p[0], q[1] - p[1]) + self._suffix[self._i]

    def _carrot(self, p):
        path = self._path
        hi = min(len(path), self._i + LOOKAHEAD)
        self._i = min(range(self._i, hi), key=lambda k: (path[k][0] - p[0]) ** 2 + (path[k][1] - p[1]) ** 2)
        if self.world is None:
            return path[self._i]
        for k in range(min(len(path), self._i + LOOKAHEAD) - 1, self._i, -1):
            if self._clear(p, path[k]):
                return path[k]
        return path[min(self._i + 1, len(path) - 1)]

    # ---- step -------------------------------------------------------------
    def step(self, obs, goal, boost=False, quiet=False):
        me = obs["self"]
        p = me["pos"]
        t = float(obs["t"])
        goal = [float(goal[0]), float(goal[1])]
        try:
            return self._step(me, p, t, goal, boost, quiet)
        except Exception:
            return self._out(goal[0] - p[0], goal[1] - p[1], me, boost, quiet)

    def _out(self, dx, dy, me, boost, quiet, jump=False):
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return {"move": [0.0, 0.0], "boost": False, "jump": False}
        s = 1.0
        if quiet:
            walk = float(me.get("stats", {}).get("walk_speed", self._m.get("walk_speed", 11.7)))
            s = min(1.0, 0.9 * self._step_speed / walk)
            boost = False
        return {"move": [dx / d * s, dy / d * s], "boost": bool(boost), "jump": jump}

    def _step(self, me, p, t, goal, boost, quiet):
        if self._goal is None or math.hypot(goal[0] - self._goal[0], goal[1] - self._goal[1]) > REPLAN_MOVE:
            if self._goal is None or t - self._plan_t >= REPLAN_EVERY or self._search is None:
                self._plan(p, goal, t)
                self._win, self._stage, self._side = None, 0, 1
        self._advance_search()
        tgt = self._target
        if math.hypot(tgt[0] - p[0], tgt[1] - p[1]) < ARRIVE:
            self._win, self._stage = None, 0
            return {"move": [0.0, 0.0], "boost": False, "jump": False}

        rem = self._remaining(p)
        if self._win is None:
            self._win = (t, rem)

        if self._stage == 1:  # N1 (1): jump and jet toward the goal
            rising = me.get("vel", [0, 0, 0])[2] > 0.5 and me.get("energy", 0) > 5
            if t - self._stage_t < STUCK_WINDOW or rising:
                grounded = me.get("grounded", True)
                return self._out(goal[0] - p[0], goal[1] - p[1], me, not grounded, False, jump=grounded)
            self._stage = 0
            if self._win[1] - rem < STUCK_PROGRESS:
                self._wall_walk(p, t)
            else:
                self._win = (t, rem)
        if self._stage == 2:  # N1 (2): walk along the wall, left first, then right
            sx, sy = self._side_from
            if math.hypot(p[0] - sx, p[1] - sy) < SIDE_WALK and t - self._stage_t < 2.5 * STUCK_WINDOW:
                return self._out(-self._side_dir[1] * self._side, self._side_dir[0] * self._side, me, False, quiet)
            self._stage, self._side = 0, -self._side
            self._plan(p, goal, t)
            rem = self._remaining(p)
            self._win = (t, rem)

        if t - self._win[0] >= STUCK_WINDOW:
            if self._win[1] - rem < STUCK_PROGRESS:
                if me.get("energy", 0) >= JET_ENERGY:
                    self._stage, self._stage_t = 1, t
                    return self._out(goal[0] - p[0], goal[1] - p[1], me, False, False, jump=bool(me.get("grounded", True)))
                self._wall_walk(p, t)
                return self._step(me, p, t, goal, boost, quiet)
            self._win = (t, rem)

        c = self._carrot(p)
        return self._out(c[0] - p[0], c[1] - p[1], me, boost, quiet)

    def _wall_walk(self, p, t):
        g = self._goal
        d = math.hypot(g[0] - p[0], g[1] - p[1]) or 1.0
        self._side_dir = ((g[0] - p[0]) / d, (g[1] - p[1]) / d)
        self._side_from = (p[0], p[1])
        self._stage, self._stage_t = 2, t
