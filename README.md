# MarsVQ

MarsVQ builds driving-data pairs from real Mars rover photos. Each pair has three parts: a Perseverance NavCam frame, a driving path projected into that frame through its own CAHVORE camera model, and a Grok Imagine edit of the same frame restyled as Europa ice. The edit prompt asks the model to keep every rock, the horizon, and the camera unchanged, so the one path label is drawn on both images.

The demo shows 5 pairs from Perseverance's drive across the Jezero crater floor, sols 102 to 109 (June 2021). There is no trained policy here, only the data and a check of how well the edits keep the source geometry.

## Open the demo

From the repo root, run:

```sh
open marsvq/demo/index.html
```

The page needs no server, build step, or network connection. It loads images through `../../data/pairs/`, so keep the repo layout as it is. The arrow keys step through the 5 pairs. `E` switches between the NavCam source and the edit. Both views show the same path as one 3 px green line. The page was checked in headless Chrome. Safari and Firefox were not tested.

`docs/demo.mp4` (25 s, silent) shows the same 5 pairs, source then edit, 2.5 s each.

## How the pairs are made

1. `marsvq/path/build_paths.py` reads the NASA raw-image API record for each frame and projects a flat-ground arc into it with the full CAHVORE model. The arc has 33 points out to 20 m, bends left at 1/80 per m, and follows the camera boresight. These are synthetic paths, not the path the rover drove.
2. `marsvq/path/select_drive.py` drops frames where the path can't serve as a label. The rules and their results are in `data/pairs/drive_index.json`.
3. `marsvq/imagine/batch_edit.py` sends each kept frame to `POST /v1/images/edits` (model `grok-imagine-image-2.0`) with one fixed prompt. Each edit cost $0.07 and comes back at 1152x864.
4. `marsvq/metrics/navcam_edits.py` compares Canny edge maps of each edit and its source, using the edge code in `marsvq/metrics/geometry.py`.
5. `marsvq/demo/build_pairs.py` keeps pairs with edge recall of at least 0.5, copies their sources to `data/pairs/<stem>/source.jpg`, and writes the viewer's pair list. `marsvq/demo/build_video.py` renders the video from the same list.

## Frames

`docs/frame_sources.md` lists the 16 NavCam frames that were downloaded, with their URLs. Each comes from a different stop between drive 218 and drive 922 at site 4, sols 101 to 110. For each stop, the frame with the mast pointed closest to straight ahead was chosen. Seven frames were dropped:

- Five frames point the mast 25° above the horizon. Their near path falls below the image.
- Two frames (drive 430 and drive 738) point the mast 10° to 16° left. Their near path crosses the rover's deck rail.

That leaves 9 frames. Two of them were already edited in an earlier sol-104 batch, so 7 new edits were made.

## Edge check

Recall is the fraction of source edge pixels that have an edge in the edit within 3 px. IoU is the overlap of the two edge maps after each is dilated by 3 px. An edit with no relation to its source would still score a recall of about its own dilated edge density, which is 0.32 to 0.64 for these edits. So a recall of 0.7 means less than it sounds.

The first check scored the four existing sol-104 edits (`docs/navcam_edit_metrics.json`, n=4). Median recall was 0.769 and median IoU 0.223, which cleared the 0.6 bar set for building the drive set. The highest score there, 0.995, comes from a frame that looks across the rover deck, where the edit keeps the rover hardware and invents large rocks on the ground.

The drive set (`docs/drive_edit_metrics.json`, n=9) has median recall 0.744 and median IoU 0.241.

| Sol | Drive | Recall | Chance recall | IoU | In demo | What the edit added |
|---|---|---|---|---|---|---|
| 102 | 350 | 0.880 | 0.545 | 0.204 | yes | |
| 103 | 408 | 0.701 | 0.439 | 0.258 | no (adds an object) | a rock about 50 px left of the path, mid-distance, on bare sand; blue channels |
| 104 | 488 | 0.749 | 0.476 | 0.195 | yes | |
| 104 | 510 | 0.463 | 0.432 | 0.180 | no | Jupiter and a starry sky |
| 105 | 570 | 0.758 | 0.641 | 0.211 | no (adds an object) | a small banded planet and a starry sky |
| 107 | 638 | 0.743 | 0.318 | 0.417 | yes | |
| 108 | 710 | 0.871 | 0.480 | 0.307 | yes | |
| 109 | 810 | 0.699 | 0.500 | 0.308 | yes | |
| 110 | 910 | 0.506 | 0.406 | 0.241 | no (adds an object) | Jupiter and a starry sky |

The "What the edit added" column comes from looking at the images, not from the metric. Four of the 9 edits add something the prompt forbids ("Add no new objects"). The 0.5 recall cut removed one of them. Recall can't see the others, because adding an object removes no source edges, so those three (drives 408, 570, and 910) were taken out of the demo by hand. The rock in drive 408 sits next to the path, so for that pair the label no longer described the terrain it is drawn on. Their metric rows stay in the table and in `docs/drive_edit_metrics.json`.

## Known limits

- The path assumes flat ground at z = 0 in the rover frame and ignores rover tilt.
- The labels carry no occlusion mask. The rover's own hardware sits at the bottom edge of every frame.
- Edge recall measures whether source edges survive. It does not detect added objects. Telling apart a kept rock and a moved one needs a stronger check than this.
- n is 9. These numbers describe these edits, not the edit model in general.

## Earlier test on PIA24765

Before the NavCam work, a single NASA Mastcam-Z photo (PIA24765) was edited to Europa ice and also animated as video. `docs/results.md` has the numbers, n=1 per condition. The edited still kept clearly more source edges than chance (IoU 0.511 against 0.260). A video prompted directly as Europa fell to IoU 0.215 against a chance level of 0.241 by 1 s. That result is why this project edits stills and not video.

## Credits

NavCam frames and PIA24765: NASA/JPL-Caltech, used under the [JPL image use policy](https://www.jpl.nasa.gov/jpl-image-use-policy). Edits: xAI Grok Imagine.

`data/sim/` holds an elevation mesh from an earlier experiment and is not part of the demo. It comes from the USGS Mars Sample Return Terrain Relative Navigation HiRISE DTM and Orthoimage Mosaics, version soc_003, CC0 1.0 (DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)). HiRISE imagery credit: NASA/JPL/University of Arizona.
