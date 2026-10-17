"""Render the held-out demo: predicted path and real next-stop path on real test frames.

Run: ~/Projects/mlenv/.venv/bin/python marsvq/demo/build_heldout.py

Reads data/real/results.json (train_eval.py) and data/real/test_labels.json. Every third test
frame in sol order is shown, so the frames are not picked by how well the model did.

On each frame the green line is the mars+edits model's prediction and the white line is the real
chord to the next stop. The model predicts direction only, so the green line is drawn to the same
length and end height as the white one.

Writes data/real/demo/<stem>.jpg (lines drawn, no text), data/real/demo/table.png,
marsvq/demo/index.html and docs/demo.mp4.
"""

import json
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "marsvq", "path"))
from build_paths import cahvore_3d_to_2d, parse_cahvore, to_jpeg  # noqa: E402

SRC = os.path.join(ROOT, "data/raw/real/m2020_navcam_select")
OUT = os.path.join(ROOT, "data/real/demo")
VIDEO = os.path.join(ROOT, "docs/demo.mp4")
HTML = os.path.join(ROOT, "marsvq/demo/index.html")
MODEL = "mars+edits"
W, H, BAND = 1200, 900, 60
GREEN, WHITE = "#39e639", "#ffffff"
SHOT_S, TABLE_S = 2.5, 8.0
FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
NAMES = {"constant": "Constant (training mean)", "mars": "Mars only", "mars+edits": "Mars + Imagine edits"}


def chord(e, cam_bearing_deg):
    m = parse_cahvore(e["cahvore"])
    x, y, z = e["next_stop_rover_xyz_m"]
    k = min(1.0, 20.0 / math.hypot(x, y))
    length, zend = k * math.hypot(x, y), k * z
    b = math.radians(cam_bearing_deg + e["cam_az_deg"])
    pts = []
    for i in range(33):
        t = (i / 32) ** 2
        px = cahvore_3d_to_2d((t * length * math.cos(b), t * length * math.sin(b), t * zend), m)
        if px is not None:
            pts.append(to_jpeg(px))
    return pts


def table_rows(res):
    rows = [("", "Train images", "MAE", "Median", "Within 10°")]
    for k, r in res["runs"].items():
        rows.append((NAMES[k], str(r["n_train"]), "%.1f°" % r["mae_deg"], "%.1f°" % r["median_ae_deg"],
                     "%d%%" % round(100 * r["within_10deg"])))
    return rows


def verdict(res):
    """The edit comparison in words: a CI that spans zero is no detectable effect, not a sign."""
    b = res["bootstrap_paired"]["mars+edits minus mars"]
    lo, hi = b["ci95"]
    if lo < 0 < hi:
        return "No detectable effect of the edits in either direction."
    return "The edits made the error %s." % ("larger" if lo > 0 else "smaller")


def comparison(res, deg):
    b = res["bootstrap_paired"]["mars+edits minus mars"]
    return "Edits minus Mars only: %+.1f%s MAE, 95%% CI [%+.1f%s, %+.1f%s], bootstrap by sol" % (
        b["mae_diff_deg"], deg, b["ci95"][0], deg, b["ci95"][1], deg)


def table_image(res):
    im = Image.new("RGB", (W, H + BAND), "#0e0e0e")
    d = ImageDraw.Draw(im)
    t = res["test"]
    d.text((80, 150), "Held-out: sols %s, %d real stops, sites %s" % (
        t["sols"], t["n_stops"], ", ".join(map(str, t["sites"]))), fill="#d0d0d0", font=FONT)
    d.text((80, 190), "Error in the direction of the real next stop", fill="#d0d0d0", font=FONT)
    xs = [80, 470, 680, 820, 990]
    for j, row in enumerate(table_rows(res)):
        for x, cell in zip(xs, row):
            d.text((x, 280 + 60 * j), cell, fill="#ffffff" if j else "#8a8a8a", font=FONT)
    d.text((80, 560), comparison(res, "°"), fill="#d0d0d0", font=FONT)
    d.text((80, 600), verdict(res), fill="#ffffff", font=FONT)
    d.text((80, 660), "Both models use one ridge penalty, picked on Mars only.", fill="#8a8a8a", font=FONT)
    return im


def main():
    res = json.load(open(os.path.join(ROOT, "data/real/results.json")))
    labels = {e["stem"]: e for e in json.load(open(os.path.join(ROOT, "data/real/test_labels.json")))}
    preds = sorted(res["test_predictions"], key=lambda p: (p["sol"], p["drive"]))[::3]
    os.makedirs(OUT, exist_ok=True)
    shown = []
    for p in preds:
        e = labels[p["stem"]]
        im = Image.open(os.path.join(SRC, p["stem"] + ".jpg")).convert("RGB")
        d = ImageDraw.Draw(im)
        d.line(chord(e, e["cam_bearing_deg"]), fill=WHITE, width=3)
        d.line(chord(e, p[MODEL]), fill=GREEN, width=3)
        im.save(os.path.join(OUT, p["stem"] + ".jpg"), quality=90)
        err = abs(p[MODEL] - p["true_deg"])
        shown.append({"img": "data/real/demo/%s.jpg" % p["stem"],
                      "caption": "Sol %d, drive %d. Green: predicted. White: real next stop. Error %.0f°" % (
                          p["sol"], p["drive"], err)})
    table_image(res).save(os.path.join(OUT, "table.png"))

    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for k, s in enumerate(shown):
            fr = Image.new("RGB", (W, H + BAND), "#0e0e0e")
            fr.paste(Image.open(os.path.join(ROOT, s["img"])), (0, 0))
            ImageDraw.Draw(fr).text((16, H + BAND // 2), s["caption"], fill="#d0d0d0", font=FONT, anchor="lm")
            f = os.path.join(tmp, "%02d.png" % k)
            fr.save(f)
            lines += ["file '%s'" % f, "duration %s" % SHOT_S]
        lines += ["file '%s'" % os.path.join(OUT, "table.png"), "duration %s" % TABLE_S,
                  "file '%s'" % os.path.join(OUT, "table.png")]
        open(os.path.join(tmp, "list.txt"), "w").write("\n".join(lines) + "\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
                        "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-an",
                        "-movflags", "+faststart", VIDEO], check=True)

    rows = table_rows(res)
    table_html = "".join("<tr>%s</tr>" % "".join(("<th>%s</th>" if i == 0 else "<td>%s</td>") % c for c in r)
                         for i, r in enumerate(rows))
    note = "Held-out sols %s, %d real stops in %d sols. %s. %s Both models use one ridge penalty, picked on Mars only." % (
        res["test"]["sols"], res["test"]["n_stops"], res["test"]["n_sols"], comparison(res, "&deg;"), verdict(res))
    html = PAGE.replace("@@FRAMES@@", json.dumps(shown)).replace("@@TABLE@@", table_html).replace("@@NOTE@@", note)
    open(HTML, "w").write(html)
    print("%d frames, %s, %s" % (len(shown), VIDEO, HTML))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>marsvq held-out predictions</title>
<style>
  html, body { margin: 0; background: #0e0e0e; color: #d0d0d0; font-family: ui-monospace, Menlo, monospace; }
  #wrap { max-width: 1200px; margin: 0 auto; }
  img { width: 100%; display: block; }
  #cap, #note { font-size: 13px; padding: 8px 12px; }
  table { border-collapse: collapse; margin: 4px 12px 12px; font-size: 13px; }
  th, td { padding: 3px 14px 3px 0; text-align: left; }
  th { color: #8a8a8a; font-weight: normal; }
  #credit { font-size: 11px; color: #8a8a8a; padding: 0 12px 12px; }
</style>
</head>
<body>
<div id="wrap">
<img id="img" alt="">
<div id="cap"></div>
<table>@@TABLE@@</table>
<div id="note">@@NOTE@@</div>
<div id="credit">Arrow keys step through frames. NavCam frames: NASA/JPL-Caltech.</div>
</div>
<script>
// Written by marsvq/demo/build_heldout.py. Paths are relative to the repo root.
const FRAMES = @@FRAMES@@;
let i = 0;
function show() {
  document.getElementById("img").src = "../../" + FRAMES[i].img;
  document.getElementById("cap").textContent = (i + 1) + "/" + FRAMES.length + "  " + FRAMES[i].caption;
}
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") i = (i + 1) % FRAMES.length;
  else if (e.key === "ArrowLeft") i = (i - 1 + FRAMES.length) % FRAMES.length;
  else return;
  show();
});
show();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
