"""Fetch NavCam-left full-frame records from the NASA raw-image API, one JSON file per sol.

Run: python3 -I marsvq/path/fetch_meta.py OUT_DIR SOL_FROM SOL_TO
Writes OUT_DIR/sol_NNNN.json (a list of API records). A sol whose file exists is skipped.
The API is free and needs no key.
"""

import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = ("https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&num=100&page={page}"
       "&order=sol+desc&search=%7CNAVCAM_LEFT&condition_2={sol}:sol:gte&condition_3={sol}:sol:lte"
       "&extended=sample_type::full,")


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + 3 * attempt)
    raise RuntimeError("failed: " + url)


def fetch_sol(out_dir, sol):
    path = os.path.join(out_dir, "sol_%04d.json" % sol)
    if os.path.exists(path):
        return sol, None
    recs, page = [], 0
    while True:
        res = get(URL.format(page=page, sol=sol))
        imgs = res.get("images") or []
        recs += imgs
        if len(imgs) < 100:
            break
        page += 1
    with open(path, "w") as f:
        json.dump(recs, f)
    return sol, len(recs)


def main():
    out_dir, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        for sol, n in ex.map(lambda s: fetch_sol(out_dir, s), range(lo, hi + 1)):
            if n is not None:
                print("sol %d: %d records" % (sol, n), flush=True)


if __name__ == "__main__":
    main()
