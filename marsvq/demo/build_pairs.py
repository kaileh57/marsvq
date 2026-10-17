"""Pick the demo pairs and write them into index.html.

Run: python3 -I marsvq/demo/build_pairs.py

A pair is in the demo when data/pairs/drive_index.json marks the frame kept and
docs/drive_edit_metrics.json gives its edit a recall of at least 0.5, unless its drive is in
ADDS_OBJECTS: edits that add an object the prompt forbids, found by looking at the images. Each kept source JPEG is
copied to data/pairs/<stem>/source.jpg so the page and the video work from a clone (data/raw/
is not in git). Writes data/pairs/demo_pairs.json and the PAIRS block of index.html.
"""

import json
import os
import re
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MIN_RECALL = 0.5
ADDS_OBJECTS = {408, 570, 910}  # rock beside the path; banded planet; Jupiter


def main():
    os.chdir(ROOT)
    index = json.load(open("data/pairs/drive_index.json"))
    recall = {r["stem"]: r["recall"] for r in json.load(open("docs/drive_edit_metrics.json"))["pairs"]}
    meta = {r["imageid"] + "01_1200": r for r in json.load(
        open(os.path.join(os.path.dirname(index[0]["jpeg"]), "raw_image_api_metadata.json")))}
    pairs = []
    for e in index:
        if not e["kept"] or recall.get(e["stem"], 0) < MIN_RECALL:
            continue
        r = meta[e["stem"]]
        if int(r["drive"]) in ADDS_OBJECTS:
            continue
        d = os.path.join("data/pairs", e["stem"])
        shutil.copyfile(e["jpeg"], os.path.join(d, "source.jpg"))
        pairs.append({
            "stem": e["stem"],
            "sol": r["sol"],
            "drive": int(r["drive"]),
            "source": os.path.join(d, "source.jpg"),
            "edit": os.path.join(d, "edit.jpg"),
            "recall": recall[e["stem"]],
            "image_size": e["image_size"],
            "points": json.load(open(e["path"])),
        })
    with open("data/pairs/demo_pairs.json", "w") as f:
        json.dump(pairs, f, indent=1)
        f.write("\n")

    html_path = "marsvq/demo/index.html"
    html = open(html_path).read()
    block = "const PAIRS = [\n" + ",\n".join(json.dumps(
        {k: p[k] for k in ("stem", "sol", "drive", "source", "edit", "image_size", "points")},
        separators=(",", ":")) for p in pairs) + "\n];"
    html = re.sub(r"(// PAIRS-BEGIN\n).*?(\n// PAIRS-END)", lambda m: m.group(1) + block + m.group(2),
                  html, flags=re.S)
    open(html_path, "w").write(html)
    for p in pairs:
        print(p["sol"], p["drive"], p["recall"], p["stem"])
    print(len(pairs), "pairs")


if __name__ == "__main__":
    main()
