# Sim status: real Mars terrain + scripted rover path

Last built 2026-10-17. No physics engine (MuJoCo isn't installed). The terrain is a static heightfield mesh with a scripted path drawn on top.

## Source

- **DEM** (pinned as `DEFAULT_DEM` in `build_terrain.py`): `data/raw/hirise/msr_soc003_strip1_neretva_n/1_DTM_MSR_HiRISE_Neretva_N_1m_MOLATopography_DeltaGeoid_eqc_c0.tif`
  (USGS Mars Sample Return HiRISE DTM, v003, https://doi.org/10.5066/P13CPYYU; see `data/raw/hirise/msr_soc003_docs/README.md`).
  The data agent supplied this file. The sim agent didn't download anything.
- **Full grid:** 6625 × 8361 posts at about 1.0 m (0.9975 m E, 0.9996 m N), float32, nodata −32767. Equirectangular, Mars sphere 3396190 m.
- **Crop:** pixel window col 1697, row 2894, 401 × 401 posts. Projected bounds (m): x 4580726–4581126, y 1093032–1093433. No nodata inside the window.
  The window is chosen automatically. The builder scans a 12 × 12 grid of 400 m windows, keeps those where at least 75% of the ground is under 15° slope, and ranks them by relief after removing the best-fit plane. Ranking by raw relief picked a featureless tilted crater wall instead.

## Grid and vertical range

| | |
|---|---|
| Heightfield grid | 401 × 401, post 0.997 m, 399 m × 399 m |
| Elevation (vs. Mars geoid, the "delta geoid" product) | −1954.5 m to −1872.2 m |
| Relief in tile | 82.3 m |
| Rover path | 446 m, 12 waypoints, Catmull-Rom smoothed |
| Path planner | A* on 5 m cells (SW corner → NE corner), slope cost, blocked above 15° at 5 m scale. Local 1 m slope along the path reaches 23.9°. |

## How to open the view

Double-click `marsvq/sim/view.html`, or run `open marsvq/sim/view.html`. It works from `file://` with no server and no network, because three.js r147 is vendored in `marsvq/sim/vendor/` and the terrain data is inlined in `data/sim/terrain_data.js`.

- Drag to orbit, right-drag or shift-drag to pan, scroll to zoom.
- Top-right panel: vertical exaggeration (1, 1.5, 2 or 3; 1.5 by default), animate the rover along the path, and auto-orbit.
- `view.html?poster=1` gives the fixed poster camera without UI. `&exag=2` overrides the exaggeration.

## Outputs (`data/sim/`)

| File | Contents |
|---|---|
| `terrain.png` | 1920×1080 poster, a headless Chrome (SwiftShader WebGL) screenshot of `view.html?poster=1` |
| `heightfield.png` | 16-bit grayscale, 0..65535 maps linearly to z_min..z_max, row 0 = north |
| `heightfield.json` | Source, window, post spacing, z range, path stats |
| `texture.png` | Hillshade × Mars colour ramp on detrended height. This isn't the orthoimage. |
| `path.json` | Waypoints and dense path in local ENU meters (origin at tile center, z above tile minimum) |
| `terrain_data.js` | Everything above, inlined for `view.html` |

## Rebuild

```sh
uv venv -p python3.12 marsvq/sim/.venv
uv pip install -p marsvq/sim/.venv/bin/python numpy pillow rasterio
marsvq/sim/.venv/bin/python marsvq/sim/build_terrain.py          # pinned Neretva N DTM
marsvq/sim/.venv/bin/python marsvq/sim/build_terrain.py some.tif # or an explicit DEM
marsvq/sim/.venv/bin/python marsvq/sim/render_poster.py          # data/sim/terrain.png
```

- `build_terrain.py --fetch`: if `data/raw/hirise/` is empty, this reads a 400 m window of the Mars 2020 TRN Jezero delta DTM (`..._Jezero_DL_...`) from the public USGS S3 bucket. It saves the window there and appends the source to `data/raw/SOURCES.md`. This hasn't been needed so far.
- `render_poster.py` falls back to a plain numpy/PIL oblique render when Chrome is missing or returns a blank frame. It prints which renderer it used.
- `scout.py` is the throwaway script that found the remote delta window.

## Known gaps

- The ground is shaded from the DEM. The real HiRISE orthoimage isn't draped yet: `Orthoimages (nadir)/1_ESP_062530_1985...` in the MSR archive would be the match for this strip.
- There are no rocks, rover physics, camera sensor renders or labels. The spec items G1 and §4.6 (MuJoCo hfield, RGB, depth and segmentation) aren't covered. `heightfield.png` + `heightfield.json` carry what a MuJoCo `hfield` needs: `nrow = ncol = 401`, `size = [199.5, 199.5, 82.34, base]`.
