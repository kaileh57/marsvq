"""Download the 1200x900 browse JPEG for every entry of a label file.

Run: python3 -I marsvq/path/fetch_frames.py LABELS_JSON OUT_DIR
"""

import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def main():
    labs, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)

    def one(e):
        path = os.path.join(out, e["stem"] + ".jpg")
        if not os.path.exists(path):
            urllib.request.urlretrieve(e["url"], path)
        return path

    with ThreadPoolExecutor(8) as ex:
        paths = list(ex.map(one, labs))
    print("%d frames in %s" % (len(paths), out))


if __name__ == "__main__":
    main()
