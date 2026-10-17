"""Automatic filter for Imagine edits that add objects or change the ground under the path.

Run: ~/Projects/mlenv/.venv/bin/python marsvq/metrics/edit_filter.py LABELS_JSON SRC_DIR OUT_JSON

For every label whose data/pairs/<stem>/edit.jpg exists, the edit is resized to the source's
1200x900 and both are reduced to Canny edge maps (grayscale, Gaussian sigma 1.4, thresholds 50/100).
A "new edge" is an edit edge pixel with no source edge within 3 px.

Two regions come from the frame's own CAHVORE model, not from looking at the image:
- Sky: every pixel above the flat-ground horizon, the projection of points 2 km out at z = 0
  across the field of view, minus a 40 px margin for the crater rim.
- Corridor: the ground strip 1.4 m either side of the label chord (the rover is 2.7 m wide), from
  2 m out to the chord's end, projected into the image.
- Ground: every pixel below the horizon that is not in the corridor.

Three checks:
- sky_new: new-edge density in the sky. A planet, stars or a new skyline puts edges there.
  Fail above 0.002.
- corridor_excess: new-edge density in the corridor divided by new-edge density on the rest of
  the ground. The ice texture adds edges everywhere, so the absolute density says little. A crack
  or rock on the path adds edges in the corridor faster than elsewhere. Fail above 1.5.
- corridor_struct: coarse structural dissimilarity (1 - the SSIM structure term on images blurred
  at sigma 4, window sigma 8) in the corridor divided by the same on the rest of the ground. A
  smooth mound or ridge makes few edges but changes the shading. Fail above 1.15.

The thresholds were set on the 9 sol 101 to 110 edits that docs/REVIEW.md judged by eye, before
any new edit was scored. On those 9 the filter drops the three planet skies (510, 570, 910), the
crevasse on the path (710), the mound on the path (638) and the ridges across the path (488). It
keeps 350 and 810, and it also keeps 408, whose added rock beside the path it misses. n = 9, so
these thresholds are a calibrated guess, not a tested classifier.

An edit that fails any check is dropped from training.
"""

import json
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "path"))
from build_paths import cahvore_3d_to_2d, parse_cahvore, to_jpeg  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PAIRS = os.path.join(ROOT, "data", "pairs")
W, H = 1200, 900
SKY_MARGIN_PX = 40
HALF_WIDTH_M = 1.4
NEAR_M = 2.0
MAX_SKY_NEW = 0.002
MAX_CORRIDOR_EXCESS = 1.5
MAX_CORRIDOR_STRUCT = 1.15


def edges(gray):
    return cv2.Canny(cv2.GaussianBlur(gray, (0, 0), 1.4), 50, 100) > 0


def structure_dissimilarity(a, b):
    """1 - the SSIM structure term, on images blurred at sigma 4, local window sigma 8."""
    a = cv2.GaussianBlur(a, (0, 0), 4).astype(np.float64)
    b = cv2.GaussianBlur(b, (0, 0), 4).astype(np.float64)
    blur = lambda x: cv2.GaussianBlur(x, (0, 0), 8)  # noqa: E731
    mu_a, mu_b = blur(a), blur(b)
    va, vb = blur(a * a) - mu_a ** 2, blur(b * b) - mu_b ** 2
    cab = blur(a * b) - mu_a * mu_b
    return 1 - (2 * cab + 1e-3) / (va + vb + 1e-3)


def horizon_mask(m):
    """True above the flat-ground horizon (minus the margin)."""
    c = m["c"]
    head = math.atan2(m["a"][1], m["a"][0])
    pts = []
    for d in np.linspace(-70, 70, 141):
        az = head + math.radians(d)
        px = cahvore_3d_to_2d((c[0] + 2000 * math.cos(az), c[1] + 2000 * math.sin(az), 0.0), m)
        if px is not None:
            pts.append(to_jpeg(px))
    pts = sorted(p for p in pts if -200 < p[0] < W + 200)
    us = np.array([p[0] for p in pts])
    vs = np.array([p[1] for p in pts])
    row = np.interp(np.arange(W), us, vs) - SKY_MARGIN_PX
    return np.arange(H)[:, None] < row[None, :]


def corridor_mask(m, end):
    """Ground strip HALF_WIDTH_M either side of the chord from NEAR_M to its end."""
    ex, ey, ez = end
    L = math.hypot(ex, ey)
    ux, uy = ex / L, ey / L
    nx, ny = -uy, ux
    left, right = [], []
    for s in np.linspace(NEAR_M, L, 40):
        z = ez * s / L
        for side, out in ((1, left), (-1, right)):
            p = (ux * s + side * HALF_WIDTH_M * nx, uy * s + side * HALF_WIDTH_M * ny, z)
            px = cahvore_3d_to_2d(p, m)
            if px is not None:
                out.append(to_jpeg(px))
    poly = np.array(left + right[::-1], np.int32)
    mask = np.zeros((H, W), np.uint8)
    if len(poly) >= 3:
        cv2.fillPoly(mask, [poly], 1)
    return mask > 0


def score(e, src_dir):
    edit_path = os.path.join(PAIRS, e["stem"], "edit.jpg")
    src = cv2.imread(os.path.join(src_dir, e["stem"] + ".jpg"), cv2.IMREAD_GRAYSCALE)
    edit = cv2.resize(cv2.imread(edit_path, cv2.IMREAD_GRAYSCALE), (W, H), interpolation=cv2.INTER_AREA)
    es, ee = edges(src), edges(edit)
    near_src = cv2.dilate(es.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    new = ee & ~near_src
    m = parse_cahvore(e["cahvore"])
    sky = horizon_mask(m)
    cor = corridor_mask(m, e["next_stop_rover_xyz_m"] if e["next_stop_dist_m"] <= 20 else
                        [c * 20 / e["next_stop_dist_m"] for c in e["next_stop_rover_xyz_m"]])
    ground = ~sky & ~cor
    dens = lambda x, r: float(x[r].mean()) if r.any() else 0.0  # noqa: E731
    sky_new = dens(new, sky)
    cor_new, ground_new = dens(new, cor), dens(new, ground)
    excess = cor_new / ground_new if ground_new > 0 else float("inf")
    dis = structure_dissimilarity(src, edit)
    struct = float(dis[cor].mean() / dis[ground].mean())
    reasons = []
    if sky_new > MAX_SKY_NEW:
        reasons.append("new edges above the horizon")
    if excess > MAX_CORRIDOR_EXCESS:
        reasons.append("new edges in the corridor")
    if struct > MAX_CORRIDOR_STRUCT:
        reasons.append("corridor shading changed more than the rest of the ground")
    return {
        "stem": e["stem"], "sol": e["sol"], "site": e["site"], "drive": e["drive"],
        "sky_frac": round(float(sky.mean()), 3), "corridor_frac": round(float(cor.mean()), 3),
        "sky_new": round(sky_new, 4), "corridor_new": round(cor_new, 4), "ground_new": round(ground_new, 4),
        "corridor_excess": round(excess, 3), "corridor_struct": round(struct, 3),
        "src_corridor_edges": round(dens(es, cor), 4), "edit_corridor_edges": round(dens(ee, cor), 4),
        "keep": not reasons, "fail": reasons,
    }


def main():
    labels, src_dir, out = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
    rows = [score(e, src_dir) for e in labels if os.path.exists(os.path.join(PAIRS, e["stem"], "edit.jpg"))]
    with open(out, "w") as f:
        json.dump({"max_sky_new": MAX_SKY_NEW, "max_corridor_excess": MAX_CORRIDOR_EXCESS,
                   "max_corridor_struct": MAX_CORRIDOR_STRUCT, "edits": rows}, f, indent=1)
        f.write("\n")
    for r in rows:
        print("sol %3d drive %4d  sky_new %.4f  corridor_excess %5.2f  struct %5.2f  %s" % (
            r["sol"], r["drive"], r["sky_new"], r["corridor_excess"], r["corridor_struct"], "keep" if r["keep"] else "DROP: " + "; ".join(r["fail"])))
    print("kept %d of %d" % (sum(r["keep"] for r in rows), len(rows)))


if __name__ == "__main__":
    main()
