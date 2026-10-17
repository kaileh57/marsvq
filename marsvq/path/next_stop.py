"""Real path labels: where the rover went next, projected into the frame it took at this stop.

For each frame, the next stop is the first later (site, drive) at least MIN_MOVE_M away. The literal
next drive counter is useless as a label for forward-looking frames: every mast-down frame in sols
101 to 110 is followed by a 5 m straight bump (bearing 0 +- 2 deg) before the real drive segment.
Skipping stops closer than 10 m labels the frame with where the drive actually went. Its site-frame
position (extended.xyz, x north, y east, z down, metres) minus this stop's position is rotated into
this stop's rover frame with the inverse of this stop's attitude quaternion (w, x, y, z, rover to
site). The chord from the rover origin to that point, clipped to 20 m, is sampled at 33 points and
projected through the frame's CAHVORE model with the code in build_paths.py.

Labels per frame:
- bearing_deg: direction of the next stop in the rover frame, degrees, + is right.
- cam_bearing_deg: the same direction relative to the camera boresight azimuth. This is what the
  image can show, because the mast may not point straight ahead.
- end_uv: the projected chord endpoint in 1200x900 JPEG pixels.

Run: python3 -I marsvq/path/next_stop.py meta.json [meta.json ...] --out labels.json
Every metadata file is a list of raw-image API records. Records from all files are pooled, so the
next stop can come from any camera, not only from the frames being labelled.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_paths import cahvore_3d_to_2d, parse_cahvore, to_jpeg, JPEG_W, JPEG_H  # noqa: E402

N_POINTS = 33
CLIP_M = 20.0
MIN_MOVE_M = 10.0  # skip stops closer than this (see the docstring)


def vec(s):
    return tuple(float(x) for x in s.strip("()").split(","))


def quat_rotate_inv(q, v):
    """Rotate site-frame v into the rover frame: R(q)^T v, q = (w, x, y, z)."""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
         [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
         [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]]
    return tuple(sum(r[j][i] * v[j] for j in range(3)) for i in range(3))


def yaw_deg(q):
    w, x, y, z = q
    return math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def stops(records):
    """(site, drive) -> (xyz, attitude), from every record that has both."""
    out = {}
    for r in records:
        e = r.get("extended") or {}
        if not e.get("xyz") or not r.get("attitude"):
            continue
        try:
            key = (int(r["site"]), int(r["drive"]))
        except (KeyError, TypeError, ValueError):
            continue
        out.setdefault(key, (vec(e["xyz"]), vec(r["attitude"])))
    return out


def next_stop(key, table, min_move=None):
    min_move = MIN_MOVE_M if min_move is None else min_move
    xyz = table[key][0]
    for k in sorted(k for k in table if k > key):
        if k[0] != key[0]:
            return None  # a new site resets the frame origin; don't chain across it
        d = [a - b for a, b in zip(table[k][0], xyz)]
        if math.hypot(d[0], d[1]) >= min_move:
            return k
    return None


def label(rec, table, min_move=None):
    key = (int(rec["site"]), int(rec["drive"]))
    nk = next_stop(key, table, min_move)
    if nk is None:
        return None
    xyz, att = table[key]
    d_site = tuple(a - b for a, b in zip(table[nk][0], xyz))
    d = quat_rotate_inv(att, d_site)
    dist = math.hypot(d[0], d[1])
    k = min(1.0, CLIP_M / dist)
    end = tuple(k * c for c in d)
    m = parse_cahvore(rec["camera"]["camera_model_component_list"])
    cam_az = math.degrees(math.atan2(m["a"][1], m["a"][0]))
    bearing = math.degrees(math.atan2(d[1], d[0]))
    uv = []
    for i in range(N_POINTS):
        t = (i / (N_POINTS - 1)) ** 2
        p = tuple(t * c for c in end)
        if p[2] <= m["c"][2]:
            continue
        px = cahvore_3d_to_2d(p, m)
        if px is not None:
            u, v = to_jpeg(px)
            uv.append([round(u, 2), round(v, 2)])
    end_px = cahvore_3d_to_2d(end, m)
    end_uv = [round(c, 2) for c in to_jpeg(end_px)] if end_px else None
    in_frame = end_uv is not None and 0 <= end_uv[0] < JPEG_W and 0 <= end_uv[1] < JPEG_H
    return {
        "imageid": rec["imageid"],
        "stem": rec["imageid"] + "01_1200",
        "sol": int(rec["sol"]), "site": key[0], "drive": key[1],
        "next_site": nk[0], "next_drive": nk[1],
        "mast_az_deg": float(rec["extended"]["mastAz"]),
        "mast_el_deg": float(rec["extended"]["mastEl"]),
        "rover_yaw_deg": round(yaw_deg(att), 2),
        "next_stop_rover_xyz_m": [round(c, 3) for c in d],
        "next_stop_dist_m": round(dist, 2),
        "bearing_deg": round(bearing, 2),
        "cam_az_deg": round(cam_az, 2),
        "cam_bearing_deg": round((bearing - cam_az + 180) % 360 - 180, 2),
        "end_uv": end_uv,
        "end_in_frame": in_frame,
        "path_uv": uv,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta", nargs="+")
    ap.add_argument("--stops", nargs="*", default=[], help="extra metadata used only for stop positions")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-move", type=float, default=MIN_MOVE_M)
    args = ap.parse_args()
    recs = [r for p in args.meta for r in json.load(open(p))]
    pool = recs + [r for p in args.stops for r in json.load(open(p))]
    table = stops(pool)
    out = []
    for r in sorted(recs, key=lambda r: r["imageid"]):
        lab = label(r, table, args.min_move)
        if lab:
            out.append(lab)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    for e in out:
        print("sol %3d drive %4d -> %4d  dist %5.1f m  yaw %7.1f  bearing %6.1f  cam %6.1f  end %s %s" % (
            e["sol"], e["drive"], e["next_drive"], e["next_stop_dist_m"], e["rover_yaw_deg"],
            e["bearing_deg"], e["cam_bearing_deg"], e["end_uv"], "in" if e["end_in_frame"] else "OUT"))


if __name__ == "__main__":
    main()
