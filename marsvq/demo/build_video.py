"""Render docs/demo.mp4 from data/pairs/demo_pairs.json.

Run: marsvq/sim/.venv/bin/python marsvq/demo/build_video.py

For each pair: the NavCam source, then the Grok Imagine edit, each held SHOT_S seconds with hard
cuts. Both get the same path.json drawn as one 3 px #39e639 line. The edit is resized to the
1200x900 source size so the path pixels line up, which is the same mapping index.html uses.
One caption line sits below the image. No audio.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/demo.mp4"
SHOT_S = 2.5
W, H, BAND = 1200, 900, 60
GREEN = "#39e639"
FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)


def frame(img_path, points, caption):
    im = Image.open(ROOT / img_path).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    ImageDraw.Draw(im).line([tuple(p) for p in points], fill=GREEN, width=3)
    out = Image.new("RGB", (W, H + BAND), "#0e0e0e")
    out.paste(im, (0, 0))
    ImageDraw.Draw(out).text((16, H + BAND // 2), caption, fill="#d0d0d0", font=FONT, anchor="lm")
    return out


def main():
    pairs = json.loads((ROOT / "data/pairs/demo_pairs.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        lines = []
        for k, p in enumerate(pairs):
            where = f"Perseverance NavCam, sol {p['sol']}, drive {p['drive']}"
            shots = [(p["source"], f"{where}. Source (NASA/JPL-Caltech)"),
                     (p["edit"], f"{where}. Grok Imagine edit, edge recall {p['recall']:.2f}")]
            for j, (img, cap) in enumerate(shots):
                f = tmp / f"{k:02d}_{j}.png"
                frame(img, p["points"], cap).save(f)
                lines += [f"file '{f}'", f"duration {SHOT_S}"]
        (tmp / "list.txt").write_text("\n".join(lines) + "\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                        "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-an",
                        "-movflags", "+faststart", str(OUT)], check=True)
    print(OUT, len(pairs), "pairs")


if __name__ == "__main__":
    main()
