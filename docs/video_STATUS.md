# Video status: docs/demo.mp4

Cut 2026-10-17. This file replaces the earlier `docs/demo.mp4` (35.1 s, 37 MB).

- **Duration:** 37.0 s (1110 frames at 30 fps)
- **Format:** 1920×1080, H.264 (yuv420p, CRF 18), one video stream, no audio
- **Look:** #0e0e0e background, hard cuts only, one Georgia caption line per shot (`/System/Library/Fonts/Supplemental/Georgia.ttf`)

## Stems used

| Mast az | Stem |
|---|---|
| 0° (359.8°) | `NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200` |
| 10° (10.1°) | `NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200` |
| 83° (83.3°) | `NLF_0104_0676181382_036ECM_N0040510NCAM03104_01_295J01_1200` |

**Skipped:** `NLF_0104_0676181093_823ECM_N0040510NCAM03104_01_295J01_1200` (mast az 298.5°). This is the fourth frame with an `edit.jpg`. `marsvq/path/STATUS.md` says the arm turret hides the path below about v ≈ 320 in this frame. Three frames were left, so the fallback to all four edits did not apply.

## Shot list

| Time (s) | Shot | Caption |
|---|---|---|
| 0–5 | az 0° source + path | Perseverance NavCam, sol 104, mast az 0°. Synthetic path, projected with the camera model. |
| 5–10 | az 0° edit + path | Grok Imagine edit of the same frame. Same path, same pixels. |
| 10–15 | az 10° source + path | (as above, az 10°) |
| 15–20 | az 10° edit + path | (as above) |
| 20–25 | az 83° source + path | (as above, az 83°) |
| 25–30 | az 83° edit + path | (as above) |
| 30–34 | `data/sim/terrain.png` | Separate datum. HiRISE elevation, Neretva Vallis. Not these frames. |
| 34–37 | End card | Grok Imagine. Cursor. Claude. |

## Path overlay

The path is drawn as a 3 px #39e639 polyline in output pixels. Both the source (1200×900) and the edit (1152×864) are scaled to the same 1280×960 display area. `path.json` coordinates are in 1200×900 pixel space, so they are multiplied by 1280/1200. The line therefore sits at the same pixels in each source/edit pair. The first few path points have v > 900, below the image, and are clipped at its bottom edge.

## Rebuild

The render script and stills are in `/tmp/marsvq_video/` (`render.py`, `list.txt`, `frames/`). They are not in the repo.
