"""Build a heightfield, texture and scripted rover path from a real Mars DEM.

Usage (from the repo root):
    marsvq/sim/.venv/bin/python marsvq/sim/build_terrain.py [DEM.tif] [--fetch]

DEM resolution order: explicit path, else DEFAULT_DEM (the MSR Neretva N strip),
else the first DTM GeoTIFF/IMG under data/raw/hirise/,
else (with --fetch) a 400 m window read remotely from the USGS Mars 2020 TRN
Jezero delta HiRISE DTM and saved into data/raw/hirise/.

Outputs in data/sim/: heightfield.png (16-bit), heightfield.json, texture.png,
path.json, terrain_data.js (inline data so view.html works from file://).
"""
import base64
import heapq
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
import rasterio.windows
from PIL import Image
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "hirise"
OUT = ROOT / "data" / "sim"

REMOTE_TILE = "DTM_MOLAtopography_DeltaGeoid_Jezero_DL_Edited_affine_1m_Eqc_latTs0_lon0.tif"
REMOTE_URL = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/HiRISE/" + REMOTE_TILE
REMOTE_WINDOW = (5469, 6405, 400, 400)  # col, row, w, h: delta front, ~73 m relief (scout.py)
LOCAL_CROP = "jezero_DL_crop_c5469_r6405_400m.tif"
# Pinned so rebuilds stay stable while other agents add files to data/raw/hirise/.
DEFAULT_DEM = RAW / "msr_soc003_strip1_neretva_n" / "1_DTM_MSR_HiRISE_Neretva_N_1m_MOLATopography_DeltaGeoid_eqc_c0.tif"

CROP_M = 400.0       # crop edge in meters
MAX_GRID = 512       # decimate so the grid is at most this many posts per side
MAX_SLOPE_DEG = 15.0


def fetch_remote():
    """Windowed read of the remote COG-like tiled GeoTIFF; save only the crop."""
    RAW.mkdir(parents=True, exist_ok=True)
    dst = RAW / LOCAL_CROP
    c, r, w, h = REMOTE_WINDOW
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + REMOTE_URL) as src:
            win = Window(c, r, w, h)
            a = src.read(1, window=win)
            prof = src.profile.copy()
            prof.update(width=w, height=h, transform=src.window_transform(win),
                        tiled=False, compress="lzw")
            prof.pop("blockxsize", None)
            prof.pop("blockysize", None)
    with rasterio.open(dst, "w", **prof) as out:
        out.write(a, 1)
    note = f"""
## HiRISE DTM crop for the sim terrain (added {date.today().isoformat()} by the sim agent)

- File: `data/raw/hirise/{LOCAL_CROP}` ({w}x{h} posts at 1 m, float32 meters, nodata -32768)
- Source: {REMOTE_URL}
- Index: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/HiRISE/index.html
- Window: col {c}, row {r}, {w}x{h} px, read remotely with rasterio `/vsicurl/` (only the crop was downloaded)
- Product: "High-Resolution Imaging Science Experiment Digital Terrain Model Jezero_DL; PSP_002387_1985, PSP_003798_1985",
  Fergason, Galuszka, Hare, Mayer, Redding, Smith (USGS Astrogeology, Mars 2020 Terrain Relative Navigation), 2020-07-24,
  https://doi.org/10.5066/P9REJ9JN. Elevations relative to the MOLA areoid. Public domain (USGS); use constraints: none.
"""
    sources = ROOT / "data" / "raw" / "SOURCES.md"
    with open(sources, "a") as f:
        f.write(note)
    return dst


def find_dem(argv):
    paths = [a for a in argv if not a.startswith("--")]
    if paths:
        return Path(paths[0])
    if DEFAULT_DEM.exists():
        return DEFAULT_DEM
    if RAW.exists():
        hits = [p for p in sorted(RAW.rglob("*")) if p.suffix.lower() in (".tif", ".tiff", ".img")
                and "fom" not in p.name.lower() and "confidence" not in p.name.lower()]
        hits.sort(key=lambda p: ("dtm" not in p.name.lower() and "dem" not in p.name.lower(), str(p)))
        if hits:
            return hits[0]
    if "--fetch" in argv:
        return fetch_remote()
    sys.exit("no DEM in data/raw/hirise/; pass a path or --fetch")


def detrend(a):
    """Residual after removing the best-fit plane (the regional tilt)."""
    yy, xx = np.mgrid[: a.shape[0], : a.shape[1]]
    A = np.column_stack([xx.ravel(), yy.ravel(), np.ones(a.size)])
    coef, *_ = np.linalg.lstsq(A, a.ravel(), rcond=None)
    return a - (A @ coef).reshape(a.shape)


def candidate_windows(src, size_px, grid=12):
    """Nodata-free square windows of size_px, ranked by detrended relief.

    Raw relief favours steep crater walls (a tilted sheet). Instead, keep windows where
    most of the ground is drivable and rank them by relief left after removing the tilt.
    """
    if src.width <= size_px and src.height <= size_px:
        return [Window(0, 0, src.width, src.height)]
    size_px = min(size_px, src.width, src.height)
    found = []
    for fy in np.linspace(0, 1, grid):
        for fx in np.linspace(0, 1, grid):
            c, r = int(fx * (src.width - size_px)), int(fy * (src.height - size_px))
            win = Window(c, r, size_px, size_px)
            a = src.read(1, window=win, out_shape=(80, 80)).astype(np.float64)
            if src.nodata is not None and (a == src.nodata).any():
                continue
            if not np.isfinite(a).all() or (a < -1e4).any():
                continue
            post = size_px * abs(src.res[0]) / a.shape[0]
            drivable = (slope_deg(a, post) < MAX_SLOPE_DEG).mean()
            if drivable < 0.75:
                continue
            r = detrend(a)
            found.append((np.percentile(r, 98) - np.percentile(r, 2), win))
    if not found:
        sys.exit("no nodata-free window found")
    found.sort(key=lambda t: -t[0])
    return [w for _, w in found]


def load_heights(src, win):
    res = abs(src.res[0])
    n = int(min(win.width, win.height))
    win = Window(win.col_off, win.row_off, n, n)
    out_n = min(n, MAX_GRID)
    z = src.read(1, window=win, out_shape=(out_n, out_n)).astype(np.float64)
    bad = ~np.isfinite(z) | (z < -1e4)
    if src.nodata is not None:
        bad |= z == src.nodata
    if bad.any():
        z[bad] = np.median(z[~bad])
    dem = Path(src.name)
    meta = {"dem": str(dem.relative_to(ROOT)) if ROOT in dem.parents else src.name,
            "crs": src.crs.to_string() if src.crs else None,
            "window_px": [int(win.col_off), int(win.row_off), n, n],
            "window_bounds": list(rasterio.windows.bounds(win, src.transform)),
            "src_grid": [src.height, src.width], "src_res_m": list(map(abs, src.res)),
            "post_m": res * n / out_n, "nodata_filled": int(bad.sum())}
    return z, meta


def slope_deg(z, post):
    gy, gx = np.gradient(z, post)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def texture(z, post):
    """Hillshade times a Mars colour ramp. Row 0 is north."""
    gy, gx = np.gradient(z, post)
    az, alt = np.radians(315), np.radians(35)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    shade = np.clip(shade, 0, 1)
    r = detrend(z)
    lo_p, hi_p = np.percentile(r, [1, 99])
    t = np.clip((r - lo_p) / max(hi_p - lo_p, 1e-6), 0, 1)
    lo, hi = np.array([92, 44, 26]), np.array([214, 140, 92])
    base = lo + (hi - lo) * t[..., None]
    rgb = base * (0.35 + 0.85 * shade[..., None])
    return np.clip(rgb, 0, 255).astype(np.uint8)


def plan_path(z, post, n_coarse=80):
    """A* over a coarse grid from SW to NE, cost grows with slope, blocked above MAX_SLOPE_DEG."""
    k = max(1, z.shape[0] // n_coarse)
    zc = z[: z.shape[0] // k * k, : z.shape[1] // k * k]
    zc = zc.reshape(zc.shape[0] // k, k, zc.shape[1] // k, k).mean(axis=(1, 3))
    pc = post * k
    s = slope_deg(zc, pc)
    H, W = s.shape

    def nearest_flat(fy, fx):
        ys, xs = np.nonzero(s < MAX_SLOPE_DEG * 0.6)
        d = (ys - fy * H) ** 2 + (xs - fx * W) ** 2
        i = int(np.argmin(d))
        return int(ys[i]), int(xs[i])

    start, goal = nearest_flat(0.92, 0.08), nearest_flat(0.08, 0.92)  # row 0 is north
    cost = 1 + (s / MAX_SLOPE_DEG) ** 2 * 4
    cost[s > MAX_SLOPE_DEG] = np.inf
    nbrs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    g = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    while pq:
        _, cur = heapq.heappop(pq)
        if cur == goal:
            break
        for dy, dx in nbrs:
            ny, nx = cur[0] + dy, cur[1] + dx
            if not (0 <= ny < H and 0 <= nx < W) or not np.isfinite(cost[ny, nx]):
                continue
            step = np.hypot(dy, dx) * 0.5 * (cost[cur] + cost[ny, nx])
            ng = g[cur] + step
            if ng < g.get((ny, nx), np.inf):
                g[(ny, nx)] = ng
                prev[(ny, nx)] = cur
                h = np.hypot(goal[0] - ny, goal[1] - nx)
                heapq.heappush(pq, (ng + h, (ny, nx)))
    if goal not in prev:
        return None
    cells = [goal]
    while cells[-1] != start:
        cells.append(prev[cells[-1]])
    cells.reverse()
    # Keep ~12 waypoints, then smooth with Catmull-Rom.
    idx = np.unique(np.linspace(0, len(cells) - 1, 12).round().astype(int))
    way = np.array([[(cells[i][1] + 0.5) * k, (cells[i][0] + 0.5) * k] for i in idx], float)  # (col, row) in fine px
    dense = catmull_rom(way, 24)
    return way, dense


def catmull_rom(p, per_seg):
    p = np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, per_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-2])
    return np.array(out)


def bilinear(z, cr):
    c = np.clip(cr[:, 0], 0, z.shape[1] - 1.001)
    r = np.clip(cr[:, 1], 0, z.shape[0] - 1.001)
    c0, r0 = c.astype(int), r.astype(int)
    fc, fr = c - c0, r - r0
    return (z[r0, c0] * (1 - fc) * (1 - fr) + z[r0, c0 + 1] * fc * (1 - fr)
            + z[r0 + 1, c0] * (1 - fc) * fr + z[r0 + 1, c0 + 1] * fc * fr)


def to_local(cr, z, post, zmin):
    """Fine-grid (col, row) to local ENU meters, origin at tile center, z above tile minimum."""
    n = z.shape[0]
    x = (cr[:, 0] - (n - 1) / 2) * post
    y = ((n - 1) / 2 - cr[:, 1]) * post
    h = bilinear(z, cr) - zmin
    return np.column_stack([x, y, h])


def png_b64(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    dem = find_dem(sys.argv[1:])
    with rasterio.open(dem) as src:
        for win in candidate_windows(src, int(round(CROP_M / abs(src.res[0])))):
            z, meta = load_heights(src, win)
            post = meta["post_m"]
            planned = plan_path(z, post)
            if planned:
                break
            print("no slope-safe path in window", meta["window_px"], "- trying next", file=sys.stderr)
        else:
            sys.exit("A* found no slope-safe path in any window")
    zmin, zmax = float(z.min()), float(z.max())
    OUT.mkdir(parents=True, exist_ok=True)

    q = np.round((z - zmin) / max(zmax - zmin, 1e-6) * 65535).astype(np.uint16)
    Image.fromarray(q).save(OUT / "heightfield.png")
    tex = texture(z, post)
    Image.fromarray(tex).save(OUT / "texture.png")

    way, dense = planned
    way_m, dense_m = to_local(way, z, post, zmin), to_local(dense, z, post, zmin)
    s = slope_deg(z, post)
    path_len = float(np.linalg.norm(np.diff(dense_m, axis=0), axis=1).sum())
    max_path_slope = float(bilinear(s, dense).max())

    n = z.shape[0]
    meta.update({"grid": [n, n], "size_m": post * (n - 1), "z_min_m": zmin, "z_max_m": zmax,
                 "relief_m": zmax - zmin, "heightfield_png": "uint16, 0..65535 -> z_min..z_max, row 0 = north",
                 "path_len_m": path_len, "path_max_slope_1m_deg": max_path_slope, "planner": "A* on ~5 m cells, slope limit applied at that scale",
                 "slope_limit_deg": MAX_SLOPE_DEG})
    (OUT / "heightfield.json").write_text(json.dumps(meta, indent=2))
    (OUT / "path.json").write_text(json.dumps({
        "frame": "local ENU meters, origin at tile center (x east, y north), z above tile min",
        "waypoints": way_m.round(3).tolist(), "dense": dense_m.round(3).tolist()}, indent=1))

    m = re.search(r"HiRISE_(.+?)_1m", Path(meta["dem"]).name) or re.search(r"Jezero_([A-Z_]+?)_", Path(meta["dem"]).name)
    site = m.group(1).replace("_", " ") if m else Path(meta["dem"]).stem
    site = {"Neretva N": "Neretva Vallis (north)", "DL": "delta"}.get(site, site)
    js = {"n": n, "site": site, "post": post, "zmin": zmin, "zmax": zmax, "source": meta["dem"],
          "heights": base64.b64encode(q.astype("<u2").tobytes()).decode(),
          "texture": "data:image/png;base64," + png_b64(tex),
          "waypoints": way_m.round(3).tolist(), "path": dense_m.round(3).tolist()}
    (OUT / "terrain_data.js").write_text("window.TERRAIN = " + json.dumps(js) + ";\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
