"""Edge-geometry overlap between each NavCam edit.jpg and its source JPEG.

Run: marsvq/sim/.venv/bin/python marsvq/metrics/navcam_edits.py [index_json] [out_json]
Defaults: data/pairs/index.json (the sol-104 frames) -> docs/navcam_edit_metrics.json.
Scores every index entry that has an edit.jpg and is not marked "kept": false.

Same edge method as geometry.py (its canny, dilate and score are imported, not copied).
The source is resized to the edit's size with Lanczos, as geometry.py does for its reference.
"""

import json
import statistics
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from geometry import DILATE, HIGH, LOW, SIGMA, canny, dilate, gray, score  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    index = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data/pairs/index.json")
    out = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "docs/navcam_edit_metrics.json")
    rows = []
    for e in json.loads(index.read_text()):
        edit = ROOT / "data/pairs" / e["stem"] / "edit.jpg"
        if e.get("kept") is False or not edit.exists():
            continue
        src = ROOT / e["jpeg"]
        test_im = Image.open(edit)
        size = test_im.size
        ref = canny(gray(Image.open(src), size))
        test = canny(gray(test_im, size))
        iou, rec = score(ref, test)
        rows.append({
            "stem": edit.parent.name,
            "source": str(src.relative_to(ROOT)),
            "edit": str(edit.relative_to(ROOT)),
            "size": list(size),
            "recall": round(rec, 4),
            "iou": round(iou, 4),
            "source_dilated_edge_density": round(float(dilate(ref, DILATE).mean()), 4),
            "edit_dilated_edge_density": round(float(dilate(test, DILATE).mean()), 4),
        })
        print(f"{edit.parent.name[:40]}  recall={rec:.3f}  iou={iou:.3f}", file=sys.stderr)
    recalls = [r["recall"] for r in rows]
    ious = [r["iou"] for r in rows]
    doc = {
        "index": str(index.relative_to(ROOT)),
        "n": len(rows),
        "median_recall": round(statistics.median(recalls), 4) if rows else None,
        "median_iou": round(statistics.median(ious), 4) if rows else None,
        "method": (f"geometry.py Canny (sigma {SIGMA}, hysteresis {LOW:g}/{HIGH:g}) on 8-bit grayscale; "
                   f"source resized to the edit size with Lanczos. Recall: fraction of source edge pixels "
                   f"with an edit edge within {DILATE} px. IoU: both edge maps dilated {DILATE} px. "
                   f"Chance recall for an unrelated edit is about its dilated edge density."),
        "pairs": rows,
    }
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"n={doc['n']} median recall={doc['median_recall']} median iou={doc['median_iou']}", file=sys.stderr)


if __name__ == "__main__":
    main()
