"""Navigation on a 2.5D grid: each cell has a surface height (ground or roof). A* walks steps up to
step_up and terrain up to max_slope, drops down anything, and jets up walls within energy reach
(jump + jet). The step jumps and jets when the path climbs. Plus the N1 stuck rule (game-plan §3).
"""
import heapq
import math
import time

CELL = 4.0           # grid cell (m); full map grid builds in about 0.3 s
ARRIVE = 2.0         # arrived within this horizontal distance (m)
STUCK_WINDOW = 2.0   # N1: progress window (s)
STUCK_PROGRESS = 3.0 # N1: minimum progress in the window (m)
JET_ENERGY = 40.0    # N1: jet only with at least this much energy
SIDE_WALK = 10.0     # N1: walk this far along the wall (m)
REPLAN_MOVE = 4.0    # replan when the goal moves this far (m)
REPLAN_EVERY = 0.5   # at most one new search per this many seconds
SEARCH_MS = 4.0      # A* time slice per step (ms); the search continues next step
LOOKAHEAD = 8        # path nodes considered for the steering point
SNAP = 10            # cells searched for the nearest free cell
WALL_BUCKET = 32.0   # m, bucket size for wall-cell lookups
WALL_VIEW = 4.0      # a neighbour surface this much higher counts as a wall (blocks sight)
JET_PEN = 4.0        # extra cost (cells) of a jet edge: noise, energy, time
CLIMB_LOOK = 10.0    # m: start a climb when the higher path node is this close
DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


class Nav:
    def __init__(self, cfg, world):
        m = (cfg or {}).get("mech", {})
        self._m = m
        self._step_speed = float((cfg or {}).get("sound", {}).get("step_speed", 5))
        g = float(m.get("gravity", 22))
        self._jump_h = float(m.get("jump_speed", 11)) ** 2 / (2 * g) if g > 0 else 2.0
        self._rise = float(m.get("max_rise_speed", 10))
        self._drain = float(m.get("jet_drain", 15))
        self._step_up = float(m.get("step_up", 1.2))
        # jet reach with a full tank, 15% margin (towers are 67+ m, the highest roof 49.5 m)
        self._reach = self._jump_h + 0.85 * float(m.get("energy", 100)) / self._drain * self._rise
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
        self.climbing = False    # last step was a planned climb (jump/jet)
        self.walls = {}
        if world is not None:
            try:
                self._build(world)
            except Exception:
                self.world = None

    # ---- grid -------------------------------------------------------------
    def _build(self, w):
        x0, y0, x1, y1 = w.bounds
        self._x0, self._y0 = x0, y0
        nx = self._nx = int((x1 - x0) // CELL)
        ny = self._ny = int((y1 - y0) // CELL)
        r = float(self._m.get("radius", 2.5))
        h = float(self._m.get("height", 9))
        step = self._step_up
        edge = r + 0.5
        free = bytearray(nx * ny)
        roof = bytearray(nx * ny)
        s = [0.0] * (nx * ny)
        for j in range(ny):
            y = y0 + (j + 0.5) * CELL
            for i in range(nx):
                x = x0 + (i + 0.5) * CELL
                k = j * nx + i
                gz = w.ground(x, y)
                z = s[k] = max(gz, w.top(x, y, 1e4))
                roof[k] = z > gz + 0.5
                # the map edge is a wall (blocked() ignores it)
                if x - x0 > edge and x1 - x > edge and y - y0 > edge and y1 - y > edge and not w.blocked(x, y, z, r, h, step):
                    free[k] = 1
        self._free, self._s, self._roof = free, s, roof
        self._climb = math.tan(math.radians(float(self._m.get("max_slope_deg", 50)))) * CELL
        # Wall cells: free cells beside a building wall (an unwalkable or much higher neighbour), not the map
        # edge. n = unit vector toward the wall. Bucketed by WALL_BUCKET m for cover searches.
        walls = {}
        wall = bytearray(nx * ny)
        for j in range(1, ny - 1):
            for i in range(1, nx - 1):
                k = j * nx + i
                if not free[k]:
                    continue
                sx = sy = 0
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    q = (j + dj) * nx + i + di
                    if not free[q] or s[q] > s[k] + WALL_VIEW:
                        sx += di
                        sy += dj
                if sx or sy:
                    x, y = self._center(i, j)
                    if x - x0 <= 3 * CELL or x1 - x <= 3 * CELL or y - y0 <= 3 * CELL or y1 - y <= 3 * CELL:
                        continue
                    wall[k] = 1
                    L = math.hypot(sx, sy)
                    walls.setdefault((int(x // WALL_BUCKET), int(y // WALL_BUCKET)), []).append((x, y, s[k], sx / L, sy / L))
        self.walls, self._wall = walls, wall

    def surface(self, x, y):
        """Grid surface height at (x, y) (ground or roof), or None without a map."""
        if self.world is None:
            return None
        i, j = self._cell(x, y)
        if 0 <= i < self._nx and 0 <= j < self._ny:
            return self._s[j * self._nx + i]
        return None

    def _edge(self, k, q, dc, reach):
        """Cost of moving from cell k to neighbour q, or None if impossible."""
        dz = self._s[q] - self._s[k]
        if dz <= self._step_up:
            return dc
        if not self._roof[q] and not self._roof[k] and dz <= self._climb * dc:
            return dc  # walkable terrain slope
        if dz <= reach:
            return dc + JET_PEN + dz / CELL
        return None

    def wall_cells(self, x, y, r):
        """Wall cells (x, y, surface, nx, ny) within about r m of (x, y)."""
        out = []
        if self.world is None:
            return out
        b0, b1 = int((x - r) // WALL_BUCKET), int((x + r) // WALL_BUCKET)
        c0, c1 = int((y - r) // WALL_BUCKET), int((y + r) // WALL_BUCKET)
        r2 = r * r
        for bi in range(b0, b1 + 1):
            for bj in range(c0, c1 + 1):
                for w in self.walls.get((bi, bj), ()):
                    if (w[0] - x) ** 2 + (w[1] - y) ** 2 <= r2:
                        out.append(w)
        return out

    def search(self, x, y, accept, max_cost=200.0, max_nodes=8000):
        """Dijkstra over walkable cells from (x, y). Returns (point, path_m, is_wall) of the first cell where
        accept(cx, cy, is_wall, path_m) is true, else None. is_wall: the cell is beside a building wall."""
        if self.world is None:
            return None
        st = self._snap(x, y)
        if st is None:
            return None
        nx, free, wall, reach = self._nx, self._free, self._wall, self._reach
        k0 = st[1] * nx + st[0]
        cost = {k0: 0.0}
        heap = [(0.0, k0)]
        n = 0
        while heap and n < max_nodes:
            c, k = heapq.heappop(heap)
            if c > cost.get(k, 1e18) + 1e-9:
                continue
            n += 1
            i, j = k % nx, k // nx
            cx, cy = self._center(i, j)
            if accept(cx, cy, bool(wall[k]), c * CELL):
                return [cx, cy], c * CELL, bool(wall[k])
            if c * CELL > max_cost:
                break
            for di, dj, dc in DIRS:
                a, b = i + di, j + dj
                if not self._ok(a, b) or (di and dj and not (free[j * nx + a] and free[b * nx + i])):
                    continue
                q = b * nx + a
                e = self._edge(k, q, dc, reach)
                if e is None:
                    continue
                cq = c + e
                if cq < cost.get(q, 1e18):
                    cost[q] = cq
                    heapq.heappush(heap, (cq, q))
        return None

    def free_at(self, x, y):
        """True if (x, y) is a walkable grid cell (always True without a map)."""
        if self.world is None:
            return True
        return self._ok(*self._cell(x, y))

    def clear_line(self, a, b):
        """Straight walk a→b stays on walkable cells with no climb (always True without a map)."""
        return self.world is None or self._clear(a, b)

    def _cell(self, x, y):
        return int((x - self._x0) // CELL), int((y - self._y0) // CELL)

    def _ok(self, i, j):
        return 0 <= i < self._nx and 0 <= j < self._ny and self._free[j * self._nx + i]

    def _center(self, i, j):
        return (self._x0 + (i + 0.5) * CELL, self._y0 + (j + 0.5) * CELL)

    def _snap(self, x, y, z=None):
        """Nearest free cell to (x, y) (at or below height z + 2 when z is given), or None."""
        ci, cj = self._cell(x, y)
        if self._ok(ci, cj) and (z is None or self._s[cj * self._nx + ci] <= z + 2):
            return ci, cj
        best = None
        for rr in range(1, SNAP + 1):
            for i in range(ci - rr, ci + rr + 1):
                for j in (cj - rr, cj + rr) if abs(i - ci) < rr else range(cj - rr, cj + rr + 1):
                    if self._ok(i, j) and (z is None or self._s[j * self._nx + i] <= z + 2):
                        cx, cy = self._center(i, j)
                        d = (cx - x) ** 2 + (cy - y) ** 2
                        if best is None or d < best[0]:
                            best = (d, i, j)
            if best:
                return best[1], best[2]
        return None if z is None else self._snap(x, y)

    def _clear(self, a, b):
        """Straight walk a→b stays on free cells and never climbs more than a step (samples every 1 m)."""
        n = int(math.hypot(b[0] - a[0], b[1] - a[1])) + 1
        pi, pj = self._cell(a[0], a[1])
        prev = self._s[pj * self._nx + pi] if 0 <= pi < self._nx and 0 <= pj < self._ny else None
        for s in range(1, n + 1):
            f = s / n
            i, j = self._cell(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            if not self._ok(i, j):
                return False
            if (i, j) != (pi, pj):
                k = j * self._nx + i
                if prev is not None and self._s[k] - prev > self._step_up and (
                        self._roof[k] or self._s[k] - prev > self._climb):
                    return False
                prev, pi, pj = self._s[k], i, j
        return True

    def _astar(self, start, goal, reach):
        """Generator: yields None while working (time-sliced), then the cell path or []."""
        nx, free = self._nx, self._free
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
            ck, k = heapq.heappop(heap)
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
                ed = self._edge(k, q, dc, reach)
                if ed is None:
                    continue
                c = ck + ed
                if c < cost.get(q, 1e18):
                    cost[q] = c
                    came[q] = k
                    dx, dy = abs(a - gi), abs(b - gj)
                    heapq.heappush(heap, (c + max(dx, dy) + 0.4142 * min(dx, dy), q))
        yield []

    # ---- planning ---------------------------------------------------------
    def _plan(self, pos, goal, t, energy=None):
        self._goal, self._plan_t = goal, t
        self._target, self._search = goal, None
        if self.world is None:
            self._set_path([goal])
            return
        gc = self._snap(goal[0], goal[1])
        if gc and self.world.top(goal[0], goal[1], 1e4) - self.world.ground(goal[0], goal[1]) > self._reach:
            self._target = self._center(*gc)  # out of jet reach (dorm towers, chimneys): stop beside it
        sc = self._snap(pos[0], pos[1], pos[2] if len(pos) > 2 else None)
        if self._clear(pos, self._target) or not (gc and sc):
            self._set_path([self._target])  # open line (or no grid cell): walk straight, no search
            return
        self._search = self._astar(sc, gc, self._reach)
        old = self._path[self._i:] if self._path else []
        if old and math.hypot(old[-1][0] - self._target[0], old[-1][1] - self._target[1]) < 30:
            self._set_path(old)  # keep following the old route while the new search runs
        else:
            self._set_path([[pos[0], pos[1]]])  # stand still while the search runs (a few steps)

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

    def _climb_to(self, p):
        """(node, height) of the next path node higher than a step above p, within CLIMB_LOOK m, else None."""
        if self.world is None:
            return None
        z = p[2] if len(p) > 2 else 0.0
        for k in range(self._i, min(len(self._path), self._i + 3)):
            q = self._path[k]
            if math.hypot(q[0] - p[0], q[1] - p[1]) > CLIMB_LOOK:
                break
            h = self.surface(q[0], q[1])
            if h is not None and h > z + self._step_up + 0.3:
                return q, h
        return None

    # ---- step -------------------------------------------------------------
    def step(self, obs, goal, boost=False, quiet=False):
        me = obs["self"]
        p = me["pos"]
        t = float(obs["t"])
        goal = [float(goal[0]), float(goal[1])]
        self.climbing = False
        try:
            return self._step(me, p, t, goal, boost, quiet)
        except Exception:
            return self._out(goal[0] - p[0], goal[1] - p[1], me, boost, quiet)

    def _out(self, dx, dy, me, boost, quiet, jump=False):
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return {"move": [0.0, 0.0], "boost": bool(boost) and not me.get("grounded", True), "jump": jump}
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
                c = self._carrot(p)
                return self._out(c[0] - p[0], c[1] - p[1], me, not grounded, False, jump=grounded)
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

        # planned climb: jump, then jet until the feet clear the higher surface
        cl = self._climb_to(p)
        if cl is not None:
            q, h = cl
            z = p[2] if len(p) > 2 else 0.0
            grounded = me.get("grounded", True)
            need = max(0.0, h + 0.8 - z - (self._jump_h if grounded else 0.0))
            energy = me.get("energy", 0)
            if grounded and energy < need / self._rise * self._drain * 1.2 + 3 and me.get("in_zone", True):
                self._win = (t, rem)  # waiting for energy is not being stuck
                return {"move": [0.0, 0.0], "boost": False, "jump": False}
            self.climbing = True
            self._win = (t, rem) if not grounded else self._win
            return self._out(q[0] - p[0], q[1] - p[1], me, (not grounded) and z < h + 0.8, False, jump=grounded)

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
