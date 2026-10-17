"""Project a ground-plane driving path into each sol-104 NavCam JPEG.

Uses the CAHVORE model from the raw-image API record for each frame. That
model is in the rover navigation frame (x forward, y right, z down, ground at
z = 0) and in 1280x960 pixel space. The browse JPEGs are 1200x900, so pixels
are scaled by 0.9375.

Output per frame: data/pairs/<stem>/path.json, a list of [u, v] in JPEG pixels
with (0, 0) at the top-left corner of the image (pixel centers at +0.5).
Also writes data/pairs/index.json.

Run: python3 -I marsvq/path/build_paths.py
"""

import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = "data/raw/real/m2020_sol0104_ncam"
META = os.path.join(SRC_DIR, "raw_image_api_metadata.json")
OUT_DIR = "data/pairs"

MODEL_W, MODEL_H = 1280, 960  # CAHVORE pixel space ("dimension" in the record)
JPEG_W, JPEG_H = 1200, 900
SCALE = JPEG_W / MODEL_W  # 0.9375 on both axes

N_POINTS = 33
HORIZON_M = 20.0
CURVATURE = 1.0 / 80.0  # 1/m; ~2.5 m lateral offset at 20 m
TURN = "left"  # heading decreases with s (z-down frame: +y is the rover's right)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(k, a):
    return (k * a[0], k * a[1], k * a[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def norm(a):
    return math.sqrt(dot(a, a))


def parse_cahvore(s):
    parts = s.split(";")
    vecs = [tuple(float(x) for x in p.strip("()").split(",")) for p in parts[:7]]
    mtype, mparm = float(parts[7]), float(parts[8])
    c, a, h, v, o, r, e = vecs
    linearity = {1: 1.0, 2: 0.0}.get(int(mtype), mparm)  # 1 perspective, 2 fisheye, 3 general
    return dict(c=c, a=a, h=h, v=v, o=o, r=r, e=e, linearity=linearity)


def cahvore_3d_to_2d(p, m):
    """JPL CAHVORE projection (cmod_cahvore_3d_to_2d). Returns (u, v) in model
    pixels, or None if the point is behind the camera."""
    c, a, h, v, o, r, e, lin = (m[k] for k in ("c", "a", "h", "v", "o", "r", "e", "linearity"))
    p_c = sub(p, c)
    zeta = dot(p_c, o)
    lam3 = sub(p_c, scale(zeta, o))
    lam = norm(lam3)
    if zeta <= 0 or dot(p_c, a) <= 0:
        return None

    # Solve for the ray angle theta; E moves the entrance pupil along O.
    theta = math.atan2(lam, zeta)
    for _ in range(100):
        ct, st = math.cos(theta), math.sin(theta)
        t2 = theta * theta
        t3 = t2 * theta
        t4 = t3 * theta
        upsilon = (zeta * ct + lam * st
                   - (1 - ct) * (e[0] + e[1] * t2 + e[2] * t4)
                   - (theta - st) * (2 * e[1] * theta + 4 * e[2] * t3))
        dtheta = (zeta * st - lam * ct
                  - (theta - st) * (e[0] + e[1] * t2 + e[2] * t4)) / upsilon
        theta -= dtheta
        if abs(dtheta) < 1e-11:
            break
    if theta * abs(lin) > math.pi / 2:
        return None

    if theta < 1e-8:
        pp_c = p_c
    else:
        lt = lin * theta
        if lin < -1e-15:
            chi = math.sin(lt) / lin
        elif lin > 1e-15:
            chi = math.tan(lt) / lin
        else:
            chi = theta
        chi2 = chi * chi
        zetap = lam / chi
        mu = r[0] + r[1] * chi2 + r[2] * chi2 * chi2
        pp_c = add(scale(zetap, o), scale(1 + mu, lam3))

    alpha = dot(pp_c, a)
    if alpha <= 0:
        return None
    return dot(pp_c, h) / alpha, dot(pp_c, v) / alpha


def to_jpeg(uv):
    # Model pixel centers are integers; JPEG output puts pixel centers at +0.5.
    return (uv[0] + 0.5) * SCALE, (uv[1] + 0.5) * SCALE


def ground_path(c, heading):
    """33 ground points (z = 0) from the camera footprint along a constant-
    curvature arc, arc length s_i = 20 * (i/32)^2 (spec 4.1)."""
    x0, y0 = c[0], c[1]
    k = CURVATURE if TURN == "right" else -CURVATURE
    pts = []
    for i in range(N_POINTS):
        s = HORIZON_M * (i / (N_POINTS - 1)) ** 2
        x = x0 + (math.sin(heading + k * s) - math.sin(heading)) / k
        y = y0 - (math.cos(heading + k * s) - math.cos(heading)) / k
        pts.append((s, (x, y, 0.0)))
    return pts


def main():
    os.chdir(ROOT)
    with open(META) as f:
        records = json.load(f)

    index = []
    for rec in sorted(records, key=lambda r: r["imageid"]):
        stem = rec["imageid"] + "01_1200"
        jpeg = os.path.join(SRC_DIR, stem + ".jpg")
        if not os.path.exists(jpeg):
            raise SystemExit("missing " + jpeg)
        assert rec["camera"]["camera_model_type"] == "CAHVORE"
        assert rec["extended"]["dimension"] == "(%d,%d)" % (MODEL_W, MODEL_H)
        m = parse_cahvore(rec["camera"]["camera_model_component_list"])
        c, a = m["c"], m["a"]

        # Heading = boresight azimuth projected onto the ground plane.
        heading = math.atan2(a[1], a[0])

        uv = []
        dropped_behind = dropped_horizon = 0
        for _, p in ground_path(c, heading):
            if p[2] <= c[2]:  # at or above the camera's level plane (z down)
                dropped_horizon += 1
                continue
            px = cahvore_3d_to_2d(p, m)
            if px is None:
                dropped_behind += 1
                continue
            u, v = to_jpeg(px)
            uv.append([round(u, 2), round(v, 2)])

        n_in = sum(1 for u, v in uv if 0 <= u <= JPEG_W and 0 <= v <= JPEG_H)
        horizon = to_jpeg(cahvore_3d_to_2d(
            add(c, (1000 * math.cos(heading), 1000 * math.sin(heading), 0.0)), m))

        out = os.path.join(OUT_DIR, stem)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "path.json"), "w") as f:
            json.dump(uv, f)
            f.write("\n")

        index.append({
            "stem": stem,
            "jpeg": jpeg,
            "path": os.path.join(out, "path.json"),
            "image_size": [JPEG_W, JPEG_H],
            "camera_model": "CAHVORE (raw-image API), scaled 1280x960 -> 1200x900",
            "mast_az_deg": float(rec["extended"]["mastAz"]),
            "mast_el_deg": float(rec["extended"]["mastEl"]),
            "heading_deg_rover": round(math.degrees(heading) % 360, 3),
            "turn": TURN,
            "curvature_1_per_m": CURVATURE,
            "start_rover_xy_m": [round(c[0], 4), round(c[1], 4)],
            "camera_height_m": round(-c[2], 4),
            "n_points": len(uv),
            "n_in_frame": n_in,
            "n_dropped_behind_camera": dropped_behind,
            "n_dropped_above_horizon": dropped_horizon,
            "horizon_v_at_heading": round(horizon[1], 1),
        })
        print("%s  head %6.1f  n %2d  in-frame %2d  first %s  last %s  horizon v %.0f" % (
            stem[:30], math.degrees(heading) % 360, len(uv), n_in, uv[0], uv[-1], horizon[1]))

    with open(os.path.join(OUT_DIR, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
