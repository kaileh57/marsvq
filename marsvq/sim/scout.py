"""Scout remote USGS Jezero HiRISE DTM tiles for a high-relief, nodata-free window."""
import sys
import numpy as np
import rasterio
from rasterio.windows import Window

BASE = "/vsicurl/https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/HiRISE/"
TILES = sys.argv[1:] or ["DL", "W", "C"]
SIZE = 400

for t in TILES:
    url = f"{BASE}DTM_MOLAtopography_DeltaGeoid_Jezero_{t}_Edited_affine_1m_Eqc_latTs0_lon0.tif"
    with rasterio.open(url) as d:
        best = []
        for fy in np.linspace(0.1, 0.8, 4):
            for fx in np.linspace(0.1, 0.8, 3):
                c, r = int(fx * (d.width - SIZE)), int(fy * (d.height - SIZE))
                a = d.read(1, window=Window(c, r, SIZE, SIZE))
                if (a == d.nodata).any() or not np.isfinite(a).all():
                    continue
                relief = np.percentile(a, 98) - np.percentile(a, 2)
                best.append((relief, c, r, float(a.min()), float(a.max())))
        best.sort(reverse=True)
        print(t, d.width, d.height, [tuple(round(v, 1) for v in b) for b in best[:4]], flush=True)
