"""Tree sight blocking for the simulator (protocol.md §8, §11): trunks stop sight, dense crowns stop sight,
light foliage does not. Trees never stop shots.

Model (assumption: protocol.md names the numbers but not the formula):
- crown = ellipsoid centred at (crownX, crownY, z + (crownBase + height) / 2) with horizontal semi-axis crownR and
  vertical semi-axis (height - crownBase) / 2; heights in world.json are relative to the tree's ground `z`
  (crownBase is below z for many trees, so it cannot be absolute).
- a sight line through crowns keeps transmittance exp(-canopyDensity * metres of crown crossed); it is blocked when
  that falls below canopyBlockT (0.35 / 0.25 -> about 4 m of crown).
- trunk = vertical cylinder of trunkR at (x, y) from z up to z + crownBase (assumption: inside the crown the
  crown rule applies).
"""
import json
import math
import os

CELL = 16.0


class Canopy:
    def __init__(self, world_json_path=None, data=None):
        if data is None:
            with open(world_json_path, encoding="utf-8") as f:
                data = json.load(f)
        rules = data.get("rules", {})
        dens = float(rules.get("canopyDensity", 0.35))
        blk = float(rules.get("canopyBlockT", 0.25))
        self.max_len = math.log(1.0 / blk) / dens if dens > 0 and 0 < blk < 1 else float("inf")
        b = data["bounds"]
        self.x0, self.y0 = float(b["minX"]), float(b["minY"])
        self.nx = int(math.ceil((float(b["maxX"]) - self.x0) / CELL)) + 1
        self.ny = int(math.ceil((float(b["maxY"]) - self.y0) / CELL)) + 1
        tr = data.get("trees") or {}
        fields = tr.get("fields") or []
        raw = tr.get("data") or []
        k = len(fields)
        col = {f: i for i, f in enumerate(fields)}
        self.trees = []
        cells = {}
        for o in range(0, len(raw) - k + 1, k if k else 1):
            r = raw[o:o + k]
            x, y, z = r[col["x"]], r[col["y"]], r[col["z"]]
            h, cr, cb, trr = r[col["height"]], r[col["crownR"]], r[col["crownBase"]], r[col["trunkR"]]
            cx = r[col["crownX"]] if "crownX" in col else x
            cy = r[col["crownY"]] if "crownY" in col else y
            hz = max(0.05, (h - cb) / 2)
            t = (x, y, z, z + max(cb, 0.0), trr, cx, cy, z + (cb + h) / 2, cr, hz, min(z, z + cb), z + h)
            idx = len(self.trees)
            self.trees.append(t)
            lo_x, hi_x = min(x - trr, cx - cr), max(x + trr, cx + cr)
            lo_y, hi_y = min(y - trr, cy - cr), max(y + trr, cy + cr)
            for j in range(self._cj(lo_y), self._cj(hi_y) + 1):
                for i in range(self._ci(lo_x), self._ci(hi_x) + 1):
                    cells.setdefault(j * self.nx + i, []).append(idx)
        self.cells = cells

    def _ci(self, x):
        return min(self.nx - 1, max(0, int((x - self.x0) // CELL)))

    def _cj(self, y):
        return min(self.ny - 1, max(0, int((y - self.y0) // CELL)))

    def candidates(self, ax, ay, bx, by):
        """Tree indices whose cells the 2D segment passes (supercover-ish DDA over a coarse grid)."""
        out = set()
        cells = self.cells
        nx = self.nx
        gx, gy = (ax - self.x0) / CELL, (ay - self.y0) / CELL
        hx, hy = (bx - self.x0) / CELL, (by - self.y0) / CELL
        i, j = int(math.floor(gx)), int(math.floor(gy))
        ie, je = int(math.floor(hx)), int(math.floor(hy))
        dx, dy = hx - gx, hy - gy
        si = 1 if dx > 0 else -1
        sj = 1 if dy > 0 else -1
        inf = float("inf")
        tdx = abs(1.0 / dx) if dx else inf
        tdy = abs(1.0 / dy) if dy else inf
        tmx = ((i + 1 - gx) if dx > 0 else (gx - i)) * tdx if dx else inf
        tmy = ((j + 1 - gy) if dy > 0 else (gy - j)) * tdy if dy else inf
        for _ in range(abs(ie - i) + abs(je - j) + 1):
            c = cells.get(j * nx + i)
            if c:
                out.update(c)
            if tmx < tmy:
                i += si
                tmx += tdx
            else:
                j += sj
                tmy += tdy
        return out

    def blocks(self, a, b):
        """True if trees block sight from a to b."""
        ax, ay, az = a
        dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
        L2 = dx * dx + dy * dy
        if L2 < 1e-9:
            return False
        seg_len = math.sqrt(L2 + dz * dz)
        zlo, zhi = min(az, b[2]), max(az, b[2])
        crown = 0.0
        trees = self.trees
        for ti in self.candidates(ax, ay, b[0], b[1]):
            x, y, z, ztop, trr, cx, cy, cz, cr, hz, tlo, thi = trees[ti]
            if zhi < tlo or zlo > thi:
                continue
            # trunk: closest approach of the 2D segment to the trunk axis
            if trr > 0:
                s = ((x - ax) * dx + (y - ay) * dy) / L2
                s = 0.0 if s < 0 else 1.0 if s > 1 else s
                px, py = ax + dx * s - x, ay + dy * s - y
                if px * px + py * py <= trr * trr and z <= az + dz * s <= ztop:
                    return True
            # crown: chord through the ellipsoid
            fx, fy, fz = (ax - cx) / cr, (ay - cy) / cr, (az - cz) / hz
            ux, uy, uz = dx / cr, dy / cr, dz / hz
            qa = ux * ux + uy * uy + uz * uz
            qb = 2 * (fx * ux + fy * uy + fz * uz)
            qc = fx * fx + fy * fy + fz * fz - 1
            disc = qb * qb - 4 * qa * qc
            if disc <= 0:
                continue
            sq = math.sqrt(disc)
            t0, t1 = max(0.0, (-qb - sq) / (2 * qa)), min(1.0, (-qb + sq) / (2 * qa))
            if t1 > t0:
                crown += (t1 - t0) * seg_len
                if crown > self.max_len:
                    return True
        return False


def load(arena_dir):
    try:
        return Canopy(os.path.join(arena_dir, "v2", "world.json"))
    except Exception:
        return None
