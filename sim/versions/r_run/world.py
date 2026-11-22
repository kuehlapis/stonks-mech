"""Static map model: terrain height, prisms, line of sight, walkability (notes/interfaces.md)."""
import json
import math
import os
import sys
from array import array

CELL = 8.0  # spatial grid cell (m)
BAND = 1.0  # y-band (m) for point-in-polygon ray casting


class World:
    def __init__(self, map_dir):
        with open(os.path.join(map_dir, "v2", "world.json"), encoding="utf-8") as f:
            w = json.load(f)
        b = w["bounds"]
        self.bounds = (float(b["minX"]), float(b["minY"]), float(b["maxX"]), float(b["maxY"]))

        t = w["terrain"]
        self._tx0, self._ty0, self._ts = float(t["minX"]), float(t["minY"]), float(t["step"])
        self._tnx, self._tny = int(t["nx"]), int(t["ny"])
        scale = float(t.get("scale", 0.01))
        h = array("h")
        with open(os.path.join(map_dir, "v2", t.get("file", "terrain.i16")), "rb") as f:
            h.frombytes(f.read())
        if len(h) != self._tnx * self._tny:
            raise ValueError("terrain size %d != %d x %d" % (len(h), self._tnx, self._tny))
        if sys.byteorder == "big":
            h.byteswap()
        self._h = array("d", (v * scale for v in h))

        # Grid over bounds. Each cell: list of (prism index, edges of that prism whose bbox touches the cell).
        self._gx0, self._gy0 = self.bounds[0], self.bounds[1]
        self._gnx = int(math.ceil((self.bounds[2] - self._gx0) / CELL)) or 1
        self._gny = int(math.ceil((self.bounds[3] - self._gy0) / CELL)) or 1
        cells = [dict() for _ in range(self._gnx * self._gny)]
        self._p = []  # (base, top, minx, miny, maxx, maxy, bands)
        for pi, p in enumerate(w["prisms"]):
            edges = []
            for r in [p["ring"]] + list(p.get("holes") or []):
                n = len(r) // 2
                for k in range(n):
                    x1, y1 = r[2 * k], r[2 * k + 1]
                    x2, y2 = r[(2 * k + 2) % (2 * n)], r[(2 * k + 3) % (2 * n)]
                    if (x1, y1) != (x2, y2):
                        edges.append((x1, y1, x2, y2))
            if not edges:
                continue
            xs = [e[0] for e in edges]
            ys = [e[1] for e in edges]
            bands = {}
            for e in edges:
                for k in range(self._band(min(e[1], e[3])), self._band(max(e[1], e[3])) + 1):
                    bands.setdefault(k, []).append(e)
            idx = len(self._p)
            self._p.append((float(p["base"]), float(p["top"]), min(xs), min(ys), max(xs), max(ys), bands))
            i0, j0, i1, j1 = self._cellrange(min(xs), min(ys), max(xs), max(ys))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    cells[j * self._gnx + i][idx] = []
            for e in edges:
                i0, j0, i1, j1 = self._cellrange(min(e[0], e[2]), min(e[1], e[3]), max(e[0], e[2]), max(e[1], e[3]))
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        cells[j * self._gnx + i][idx].append(e)
        self._cells = [list(c.items()) for c in cells]

        # Max terrain per grid cell, so los samples the ground only where the segment gets close to it.
        tnx, ts = self._tnx, self._ts
        hh = self._h
        cols = []
        for i in range(self._gnx):
            a = self._gx0 + i * CELL
            cols.append((max(0, int(math.floor((a - self._tx0) / ts))), min(tnx - 1, int(math.ceil((a + CELL - self._tx0) / ts)))))
        rowmax = []
        for j in range(self._tny):
            o = j * tnx
            rowmax.append([max(hh[o + c0:o + c1 + 1]) if c1 >= c0 else -1e9 for c0, c1 in cols])
        self._cmax = array("d", [0.0]) * (self._gnx * self._gny)
        for j in range(self._gny):
            a = self._gy0 + j * CELL
            r0 = max(0, int(math.floor((a - self._ty0) / ts)))
            r1 = min(self._tny - 1, int(math.ceil((a + CELL - self._ty0) / ts)))
            rows = rowmax[r0:r1 + 1] or [rowmax[0 if r1 < 0 else -1]]
            for i in range(self._gnx):
                self._cmax[j * self._gnx + i] = max(r[i] for r in rows)

    def _band(self, y):
        return int(math.floor((y - self.bounds[1]) / BAND))

    def _cellrange(self, x0, y0, x1, y1):
        """Clamped cell index range covering the box."""
        m = self._gnx - 1
        n = self._gny - 1
        return (min(m, max(0, int((x0 - self._gx0) // CELL))), min(n, max(0, int((y0 - self._gy0) // CELL))),
                min(m, max(0, int((x1 - self._gx0) // CELL))), min(n, max(0, int((y1 - self._gy0) // CELL))))

    def _cell(self, x, y):
        i = int((x - self._gx0) // CELL)
        j = int((y - self._gy0) // CELL)
        if 0 <= i < self._gnx and 0 <= j < self._gny:
            return self._cells[j * self._gnx + i]
        return ()

    def _inside(self, p, x, y):
        """(x, y) inside ring minus holes: ray cast to +x over the edges in y's band."""
        if not (p[2] <= x <= p[4] and p[3] <= y <= p[5]):
            return False
        c = False
        for x1, y1, x2, y2 in p[6].get(self._band(y), ()):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
        return c

    def ground(self, x, y):
        fx = min(max((x - self._tx0) / self._ts, 0.0), self._tnx - 1.0)
        fy = min(max((y - self._ty0) / self._ts, 0.0), self._tny - 1.0)
        i = min(int(fx), self._tnx - 2)
        j = min(int(fy), self._tny - 2)
        tx = fx - i
        ty = fy - j
        h = self._h
        o = j * self._tnx + i
        a = h[o] + (h[o + 1] - h[o]) * tx
        b = h[o + self._tnx] + (h[o + self._tnx + 1] - h[o + self._tnx]) * tx
        return a + (b - a) * ty

    def top(self, x, y, z):
        best = self.ground(x, y)
        lim = z + 0.01
        for pi, _ in self._cell(x, y):
            p = self._p[pi]
            if best < p[1] <= lim and self._inside(p, x, y):
                best = p[1]
        return best

    def solid(self, x, y, z):
        if z < self.ground(x, y):
            return True
        for pi, _ in self._cell(x, y):
            p = self._p[pi]
            if p[0] <= z < p[1] and self._inside(p, x, y):
                return True
        return False

    def los(self, a, b):
        ax, ay, az = a[0], a[1], a[2]
        dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
        seg = {}  # prism index -> clipped 2D sub-segment inside the prism's z-slab, or None
        length = math.sqrt(dx * dx + dy * dy)
        for k, t0, t1 in self._walk(ax, ay, b[0], b[1]):
            zlo = az + dz * (t0 if dz > 0 else t1)
            if zlo < self._cmax[k]:
                # shortcut: samples the ground every terrain step, a sub-metre bump between samples can be missed
                n = max(1, int(math.ceil((t1 - t0) * length / self._ts)))
                for s in range(n + 1):
                    t = t0 + (t1 - t0) * s / n
                    if az + dz * t < self.ground(ax + dx * t, ay + dy * t):
                        return False
            for pi, edges in self._cells[k]:
                if pi in seg:
                    sg = seg[pi]
                else:
                    sg = seg[pi] = self._clip(self._p[pi], ax, ay, az, dx, dy, dz)
                if sg is None:
                    continue
                px, py, qx, qy = sg
                ux, uy = qx - px, qy - py
                for x1, y1, x2, y2 in edges:
                    d1 = ux * (y1 - py) - uy * (x1 - px)
                    d2 = ux * (y2 - py) - uy * (x2 - px)
                    if (d1 > 0) != (d2 > 0) and d1 != 0 and d2 != 0:
                        ex, ey = x2 - x1, y2 - y1
                        d3 = ex * (py - y1) - ey * (px - x1)
                        d4 = ex * (qy - y1) - ey * (qx - x1)
                        if (d3 > 0) != (d4 > 0) and d3 != 0 and d4 != 0:
                            return False
        # No wall crossed: a clipped piece is wholly inside or wholly outside its prism.
        for pi, sg in seg.items():
            if sg is not None and self._inside(self._p[pi], (sg[0] + sg[2]) * 0.5, (sg[1] + sg[3]) * 0.5):
                return False
        return True

    @staticmethod
    def _clip(p, ax, ay, az, dx, dy, dz):
        if dz == 0:
            if not (p[0] <= az < p[1]):
                return None
            s0, s1 = 0.0, 1.0
        else:
            s0, s1 = (p[0] - az) / dz, (p[1] - az) / dz
            if s0 > s1:
                s0, s1 = s1, s0
            s0, s1 = max(s0, 0.0), min(s1, 1.0)
            if s1 - s0 <= 1e-9:  # touching a roof or underside only
                return None
        px, py, qx, qy = ax + dx * s0, ay + dy * s0, ax + dx * s1, ay + dy * s1
        if max(px, qx) < p[2] or min(px, qx) > p[4] or max(py, qy) < p[3] or min(py, qy) > p[5]:
            return None
        return (px, py, qx, qy)

    def _walk(self, ax, ay, bx, by):
        """Grid cells along a→b (2D DDA): yields (cell index, t_enter, t_exit), skipping cells off the grid."""
        gx, gy = (ax - self._gx0) / CELL, (ay - self._gy0) / CELL
        hx, hy = (bx - self._gx0) / CELL, (by - self._gy0) / CELL
        i, j = int(math.floor(gx)), int(math.floor(gy))
        n = abs(int(math.floor(hx)) - i) + abs(int(math.floor(hy)) - j) + 1
        dx, dy = hx - gx, hy - gy
        inf = float("inf")
        si = 1 if dx > 0 else -1
        sj = 1 if dy > 0 else -1
        tdx = abs(1.0 / dx) if dx else inf
        tdy = abs(1.0 / dy) if dy else inf
        tmx = ((i + 1 - gx) if dx > 0 else (gx - i)) * tdx if dx else inf
        tmy = ((j + 1 - gy) if dy > 0 else (gy - j)) * tdy if dy else inf
        t = 0.0
        gnx, gny = self._gnx, self._gny
        for _ in range(n):
            tn = min(tmx, tmy, 1.0)
            if 0 <= i < gnx and 0 <= j < gny:
                yield j * gnx + i, t, tn
            if tmx < tmy:
                i += si
                t = tmx
                tmx += tdx
            else:
                j += sj
                t = tmy
                tmy += tdy

    def blocked(self, x, y, z, radius, height, step=1.2):
        # step: pass config.mech step_up; the 1.2 default is protocol.md §7's default (not in the interface yet).
        r2 = radius * radius
        lo, hi = z + step, z + height
        seen = set()
        i0, j0, i1, j1 = self._cellrange(x - radius, y - radius, x + radius, y + radius)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                for pi, edges in self._cells[j * self._gnx + i]:
                    p = self._p[pi]
                    if p[1] <= lo or p[0] >= hi:
                        continue
                    if pi not in seen:
                        seen.add(pi)
                        if self._inside(p, x, y):
                            return True
                    for x1, y1, x2, y2 in edges:
                        ex, ey = x2 - x1, y2 - y1
                        t = ((x - x1) * ex + (y - y1) * ey) / (ex * ex + ey * ey)
                        t = 0.0 if t < 0 else 1.0 if t > 1 else t
                        cx, cy = x1 + ex * t - x, y1 + ey * t - y
                        if cx * cx + cy * cy < r2:
                            return True
        return False
