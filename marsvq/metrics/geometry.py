"""Edge-geometry overlap between Grok Imagine outputs and the source still.

Run: marsvq/sim/.venv/bin/python marsvq/metrics/geometry.py
Writes docs/results.json and docs/results.md. n=1 per condition; not a benchmark.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "data/imagine"
SRC = IMG / "src/PIA24765_crop.jpg"
EDIT = IMG / "pia24765_europa_edit.jpg"

# Fixed for every image; set once from the source still's edge density.
SIGMA = 1.4
LOW, HIGH = 30.0, 60.0  # Sobel L2 magnitude on 0-255 grayscale
DILATE = 3  # pixels (3 passes of a 3x3 max = 7x7 square)
TIMES = [0, 1, 2, 4, 5]


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den), int(s["nb_frames"])


def frames_at(path, times):
    w, h, fps, n = probe(path)
    idx = [min(round(t * fps), n - 1) for t in times]
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select={sel}",
         "-fps_mode", "vfr", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True).stdout
    assert len(raw) == len(idx) * w * h * 3, (path, len(raw))
    arr = np.frombuffer(raw, np.uint8).reshape(len(idx), h, w, 3)
    return (w, h), [Image.fromarray(a) for a in arr]


def gray(im, size):
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im.convert("L"), np.float64)


def conv_sep(x, k):
    r = len(k) // 2
    p = np.pad(x, r, mode="reflect")
    y = sum(k[i] * p[:, i:i + x.shape[1]] for i in range(len(k)))
    return sum(k[i] * y[i:i + x.shape[0], :] for i in range(len(k)))


def dilate(m, n=1):
    for _ in range(n):
        p = np.pad(m, 1)
        h, w = m.shape
        m = np.zeros_like(m)
        for dy in range(3):
            for dx in range(3):
                m |= p[dy:dy + h, dx:dx + w]
    return m


def canny(g):
    r = int(np.ceil(3 * SIGMA))
    x = np.arange(-r, r + 1)
    k = np.exp(-x**2 / (2 * SIGMA**2))
    g = conv_sep(g, k / k.sum())

    p = np.pad(g, 1, mode="reflect")
    h, w = g.shape
    s = lambda dy, dx: p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    gx = (s(-1, 1) + 2 * s(0, 1) + s(1, 1)) - (s(-1, -1) + 2 * s(0, -1) + s(1, -1))
    gy = (s(1, -1) + 2 * s(1, 0) + s(1, 1)) - (s(-1, -1) + 2 * s(-1, 0) + s(-1, 1))
    mag = np.hypot(gx, gy)

    # Non-maximum suppression with direction quantized to 0/45/90/135 deg.
    ang = (np.rad2deg(np.arctan2(gy, gx)) + 180) % 180
    q = ((ang + 22.5) // 45).astype(int) % 4
    mp = np.pad(mag, 1)
    m = lambda dy, dx: mp[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    nbrs = {0: ((0, 1), (0, -1)), 1: ((1, 1), (-1, -1)),
            2: ((1, 0), (-1, 0)), 3: ((1, -1), (-1, 1))}
    keep = np.zeros_like(mag, bool)
    for b, (a, c) in nbrs.items():
        keep |= (q == b) & (mag >= m(*a)) & (mag >= m(*c))
    nms = np.where(keep, mag, 0)
    nms[[0, -1], :] = 0
    nms[:, [0, -1]] = 0

    # Double threshold and hysteresis (8-connected).
    strong = nms >= HIGH
    weak = nms >= LOW
    while True:
        grown = weak & dilate(strong)
        if (grown == strong).all():
            return strong
        strong = grown


def score(ref_edges, test_edges):
    a, b = dilate(ref_edges, DILATE), dilate(test_edges, DILATE)
    iou = (a & b).sum() / (a | b).sum()
    recall = (ref_edges & b).sum() / ref_edges.sum()
    return float(iou), float(recall)


def main():
    rows, density, test_density = [], {}, []
    size = None
    for cond, video, ref_path in [
        ("A_drive", IMG / "pia24765_mars_drive.mp4", SRC),
        ("B_prompted_europa", IMG / "pia24765_europa_ice.mp4", SRC),
        ("C_edit_still", None, SRC),
        ("C_video_from_edit", IMG / "pia24765_europa_from_edit.mp4", EDIT),
    ]:
        if video is not None:
            size, frames = frames_at(video, TIMES)
            tests = list(zip(TIMES, frames))
        else:
            tests = [(None, Image.open(EDIT))]
        ref = canny(gray(Image.open(ref_path), size))
        density[ref_path.name] = float(dilate(ref, DILATE).mean())
        for t, im in tests:
            test = canny(gray(im, size))
            iou, rec = score(ref, test)
            test_density.append(float(dilate(test, DILATE).mean()))
            rows.append({"condition": cond, "t_sec": t, "iou": round(iou, 4),
                         "recall": round(rec, 4), "width": size[0], "height": size[1]})
            print(cond, t, f"iou={iou:.4f} recall={rec:.4f}", file=sys.stderr)

    (ROOT / "docs/results.json").write_text(json.dumps(rows, indent=1) + "\n")

    w, h = size
    ref_of = {"C_video_from_edit": "edited still"}
    lines = [
        "# Source-geometry overlap, PIA24765 crop",
        "",
        "n=1 per condition. This is not a benchmark.",
        "",
        "| condition | compared to | t_sec | IoU | recall | test density | chance IoU |",
        "|---|---|---|---|---|---|---|",
    ]
    for r, q in zip(rows, test_density):
        d = density[EDIT.name if r["condition"] == "C_video_from_edit" else SRC.name]
        t = "still" if r["t_sec"] is None else r["t_sec"]
        lines.append(f"| {r['condition']} | {ref_of.get(r['condition'], 'source still')} "
                     f"| {t} | {r['iou']:.3f} | {r['recall']:.3f} | {q:.3f} | {d * q / (d + q - d * q):.3f} |")
    lines += [
        "",
        f"Dilated-edge density of the reference: source still {density[SRC.name]:.3f}, "
        f"edited still {density[EDIT.name]:.3f} (fraction of pixels). "
        f"For independent maps at reference density p and test density q, chance IoU is pq/(p+q-pq) "
        f"and chance recall is q. "
        f"Frame 0 of the A video is not a pixel copy of the source: its gray values correlate with the "
        f"resized source at about 0.53 and the framing differs.",
        "",
        "## Method",
        "",
        f"For each video we took the frames nearest 0, 1, 2, 4 and 5 s (frames 0, 24, 48, 96, 120 at 24 fps), "
        f"resized the reference still to the {w}x{h} frame size with Lanczos (a small aspect stretch, "
        f"source 1.78, edit 1.81, video 1.84), and converted every image to 8-bit grayscale with Pillow; "
        f"the edited-versus-source still row uses the same {w}x{h} size.",
        f"Edges come from a numpy Canny with Gaussian sigma {SIGMA}, Sobel L2 magnitude, 4-direction "
        f"non-maximum suppression, and hysteresis thresholds {LOW:g}/{HIGH:g}, fixed for every image.",
        f"IoU is the intersection over union of the two edge maps after each is dilated by {DILATE} pixels "
        f"(three passes of a 3x3 maximum).",
        f"Recall is the fraction of undilated reference edge pixels that have a test edge within {DILATE} pixels; "
        f"the reference is the source still for A, B and the edited still, and the edited still for the "
        f"C video.",
        "",
    ]
    (ROOT / "docs/results.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
