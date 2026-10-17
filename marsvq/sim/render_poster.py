"""Render data/sim/terrain.png: headless Chrome screenshot of view.html?poster=1,
with a numpy/PIL oblique render as fallback if Chrome is missing or returns a blank frame.

Usage (from the repo root): marsvq/sim/.venv/bin/python marsvq/sim/render_poster.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "data" / "sim"
POSTER = SIM / "terrain.png"
VIEW = Path(__file__).resolve().parent / "view.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1920, 1080


def is_blank(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w = a.shape[:2]
    a = a[h // 4: 3 * h // 4, w // 4: 3 * w // 4]  # ignore the HUD caption
    return a.std() < 12 or a.mean() < 8


def chrome_shot(extra):
    exe = CHROME if Path(CHROME).exists() else shutil.which("google-chrome") or shutil.which("chromium")
    if not exe:
        return False
    with tempfile.TemporaryDirectory() as prof:
        cmd = [exe, "--headless=new", "--hide-scrollbars", f"--window-size={W},{H}",
               "--virtual-time-budget=10000", f"--user-data-dir={prof}",
               "--allow-file-access-from-files", *extra,
               f"--screenshot={POSTER}", VIEW.as_uri() + "?poster=1"]
        try:
            subprocess.run(cmd, check=True, timeout=120, capture_output=True)
        except (subprocess.SubprocessError, OSError) as e:
            print("chrome failed:", e, file=sys.stderr)
            return False
    return POSTER.exists() and not is_blank(POSTER)


def numpy_fallback():
    """Painter's-algorithm oblique render of the textured heightfield plus the path."""
    meta = json.loads((SIM / "heightfield.json").read_text())
    q = np.asarray(Image.open(SIM / "heightfield.png"), dtype=np.float64) / 65535
    z = q * meta["relief_m"]
    tex = np.asarray(Image.open(SIM / "texture.png").convert("RGB"))
    path = np.array(json.loads((SIM / "path.json").read_text())["dense"])
    n, post = z.shape[0], meta["post_m"]
    exag, tilt = 1.5, 0.5  # vertical exaggeration, view elevation (rad)
    scale = W * 0.55 / (n * post)

    def project(x, y, h):  # local ENU meters -> screen px, camera looking north from the south
        sx = W / 2 + x * scale
        sy = H * 0.55 - (y * np.sin(tilt) + h * exag * np.cos(tilt)) * scale
        return sx, sy

    img = Image.new("RGB", (W, H), (26, 15, 12))
    d = ImageDraw.Draw(img)
    c = np.arange(n)
    for r in range(n):  # north (far) to south (near)
        x = (c - (n - 1) / 2) * post
        y = np.full(n, ((n - 1) / 2 - r) * post)
        sx, sy = project(x, y, z[r])
        base = project(x, y, np.zeros(n) - 5)[1]
        for i in range(0, n - 1):
            d.line([(sx[i], sy[i]), (sx[i], base[i])], fill=tuple(int(v) for v in tex[r, i]), width=2)
    glow = Image.new("RGB", (W, H), 0)
    g = ImageDraw.Draw(glow)
    pts = [project(p[0], p[1], p[2] + 1) for p in path]
    g.line(pts, fill=(20, 200, 255), width=14)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img = Image.fromarray(np.clip(np.asarray(img, np.int32) + np.asarray(glow, np.int32), 0, 255).astype(np.uint8))
    ImageDraw.Draw(img).line(pts, fill=(230, 255, 250), width=3)
    img.save(POSTER)


def main():
    for extra in (["--use-angle=swiftshader", "--enable-unsafe-swiftshader"], ["--disable-gpu"], []):
        if chrome_shot(extra):
            print("poster: headless Chrome WebGL", extra, "->", POSTER)
            return
    numpy_fallback()
    print("poster: numpy fallback ->", POSTER)


if __name__ == "__main__":
    main()
