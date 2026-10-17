"""Mark which drive frames to keep. Adds "kept" and "drop_reason" to each entry of an index
written by build_paths.py.

Run: marsvq/sim/.venv/bin/python marsvq/path/select_drive.py data/pairs/drive_index.json

Two drop rules:
- Mast elevation above 0: the camera looks over the horizon and the near path is below the frame.
- The near path lies on the rover body: median HSV saturation of the path pixels in the bottom
  50 rows is below 0.3. Ground there measures 0.37 to 0.51, and the deck rail is grayer. This
  threshold was set by looking at the 11 ground-facing frames, so it records a visual check.
  It is not a tested classifier.
"""

import json
import sys

import numpy as np
from PIL import Image

W, H = 1200, 900
BOTTOM_ROWS = 50
MIN_SAT = 0.3


def path_pixels(uv):
    pts = []
    for (u0, v0), (u1, v1) in zip(uv[:-1], uv[1:]):
        n = int(max(abs(u1 - u0), abs(v1 - v0))) + 1
        for t in np.linspace(0, 1, n, endpoint=False):
            u, v = u0 + (u1 - u0) * t, v0 + (v1 - v0) * t
            if 0 <= u < W and 0 <= v < H:
                pts.append((int(u), int(v)))
    return np.array(pts)


def main():
    index_path = sys.argv[1]
    index = json.load(open(index_path))
    for e in index:
        e.pop("kept", None)
        e.pop("drop_reason", None)
        e.pop("near_path_median_saturation", None)
        if e["mast_el_deg"] > 0:
            e["kept"], e["drop_reason"] = False, "mast pointed above the horizon; near path below the frame"
            continue
        hsv = np.asarray(Image.open(e["jpeg"]).convert("HSV"), float)
        px = path_pixels(json.load(open(e["path"])))
        near = px[px[:, 1] >= H - BOTTOM_ROWS]
        sat = float(np.median(hsv[near[:, 1], near[:, 0], 1]) / 255)
        e["near_path_median_saturation"] = round(sat, 3)
        if sat < MIN_SAT:
            e["kept"], e["drop_reason"] = False, "near path lies on the rover deck rail"
        else:
            e["kept"], e["drop_reason"] = True, None
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)
        f.write("\n")
    for e in index:
        print(e["stem"][:30], "kept" if e["kept"] else "drop: " + e["drop_reason"])


if __name__ == "__main__":
    main()
