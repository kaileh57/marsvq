"""Pick one forward, ground-facing NavCam frame per stop and label it with the real next stop.

Run: python3 -I marsvq/path/select_real.py META_DIR SOL_FROM SOL_TO OUT_JSON

Rules, all automatic:
- Full 1280x960 NavCam-left frame with a CAHVORE model.
- Mast elevation between -45 and -15 deg (looking at the ground ahead, not the sky) and mast
  azimuth within 30 deg of the rover's forward axis.
- The stop has a next stop at least 10 m away at the same site (next_stop.py).
- The projected chord endpoint lands inside the 1200x900 browse frame.
- Per stop, the frame whose mast azimuth is closest to straight ahead.
"""

import glob
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from next_stop import label, stops  # noqa: E402


def load(meta_dir, lo, hi):
    recs = []
    for p in sorted(glob.glob(os.path.join(meta_dir, "sol_*.json"))):
        sol = int(os.path.basename(p)[4:8])
        if lo <= sol <= hi:
            recs += json.load(open(p))
    return recs


def candidate(r):
    e = r.get("extended") or {}
    cam = r.get("camera") or {}
    if cam.get("instrument") != "NAVCAM_LEFT" or cam.get("camera_model_type") != "CAHVORE":
        return False
    if e.get("dimension") != "(1280,960)" or r.get("sample_type") != "Full":
        return False
    try:
        el, az = float(e["mastEl"]), float(e["mastAz"])
    except (KeyError, ValueError):
        return False
    az = (az + 180) % 360 - 180
    return -45 <= el <= -15 and abs(az) <= 30


def main():
    meta_dir, lo, hi, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    recs = load(meta_dir, lo, hi)
    table = stops(recs)
    best = {}
    for r in recs:
        if not candidate(r):
            continue
        lab = label(r, table)
        if lab is None or not lab["end_in_frame"]:
            continue
        lab["url"] = r["image_files"]["large"]
        lab["cahvore"] = r["camera"]["camera_model_component_list"]
        key = (lab["site"], lab["drive"])
        az = abs((lab["mast_az_deg"] + 180) % 360 - 180)
        if key not in best or az < abs((best[key]["mast_az_deg"] + 180) % 360 - 180):
            best[key] = lab
    labs = [best[k] for k in sorted(best)]
    with open(out, "w") as f:
        json.dump(labs, f, indent=1)
        f.write("\n")
    b = [e["cam_bearing_deg"] for e in labs]
    print("%d stops in sols %d-%d, %d sites" % (len(labs), lo, hi, len({e["site"] for e in labs})))
    if len(b) > 1:
        print("cam_bearing deg: mean %.1f  sd %.1f  min %.1f  p25 %.1f  median %.1f  p75 %.1f  max %.1f" % (
            statistics.mean(b), statistics.stdev(b), min(b), *statistics.quantiles(b, n=4), max(b)))
        print("constant-at-mean MAE %.1f deg" % statistics.mean(abs(x - statistics.mean(b)) for x in b))


if __name__ == "__main__":
    main()
