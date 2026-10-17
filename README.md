# MarsVQ

MarsVQ asks whether Grok Imagine edits of Mars rover photos help train a driving model. It labels real Perseverance NavCam frames with the direction the rover drove next, trains a small model on them with and without Imagine edits, and tests both on a held-out stretch of the mission.

On the held-out frames, the edits made the model worse. A model trained on real frames alone did no better than predicting a constant.

## Result

The test set is sols 340 to 460: 46 real stops at sites 9, 10, 23, 24 and 25. Training uses sols 1 to 339 (81 stops, sites 3 to 8). No stop or site appears in both. The error is the absolute difference, in degrees, between the predicted and the real direction of the next stop.

| Run | Training images | MAE | Median error | Within 10° |
|---|---|---|---|---|
| Constant (training mean, −6.2°) | 81 | 15.3° | 11.7° | 41% |
| Mars only | 81 | 15.7° | 11.5° | 37% |
| Mars + Imagine edits | 117 (81 real, 36 edits) | 19.2° | 19.7° | 28% |

The test labels have a standard deviation of 19.4°. A paired bootstrap over the 46 test stops (10,000 resamples) gives these MAE differences:

- Edits minus Mars only: +3.5°, 95% CI [+1.4°, +5.5°]. The edits hurt.
- Mars only minus constant: +0.4°, 95% CI [−1.7°, +2.5°]. The real-only model shows no skill on the new sites.

In cross-validation on the training sols, both models beat the constant baseline, by 1.0° (Mars only) and 1.7° (with edits). Neither gain carried over to the held-out sites. The full output, including every test prediction, is in `data/real/results.json`.

## Open the demo

From the repo root, run:

```sh
open marsvq/demo/index.html
```

The page steps through 16 held-out frames (every third test stop in sol order) with the arrow keys and shows the table above. On each frame, the green line is the Mars + edits model's predicted direction and the white line is the real chord to the next stop. The model predicts direction only, so the green line is drawn to the same length as the white one. `docs/demo.mp4` (56 s, silent) shows the same frames and then the table.

## How it works

1. Labels (`marsvq/path/next_stop.py`). Each NASA raw-image API record has the rover's site-frame position (`extended.xyz`) and attitude quaternion. The script rotates the next stop's position into the current rover frame, clips the chord to 20 m, and projects it into the frame through the frame's own CAHVORE camera model. The next stop is the first later stop at least 10 m away. The literal next drive counter is a 5 m straight bump after almost every forward frame, so its bearing is close to 0° every time (sd 1.1° over 7 frames in sols 101 to 110).
2. Frames (`marsvq/path/fetch_meta.py`, `select_real.py`). Each stop contributes one frame: a full-frame NavCam-left image with the mast 15° to 45° below the horizon and within 30° of straight ahead, whose label endpoint lands inside the image. The selection rules are all automatic.
3. Edits (`marsvq/imagine/batch_edit.py`). Every training frame was sent to `grok-imagine-image-2.0` with the same Europa-ice prompt used before. No test frame was edited.
4. Edit filter (`marsvq/metrics/edit_filter.py`). The filter drops an edit for any of three reasons: new edges above the projected horizon (planets, stars, a new skyline), new edges concentrated in the 2.8 m corridor under the path (cracks, rocks), or corridor shading that changes more than the rest of the ground (mounds, ridges). It kept 36 of the 81 edits. Its thresholds were set on the 9 earlier edits that `docs/REVIEW.md` judged by eye. The review flagged 6 of those 9 for an added object or an obstacle on the path. The filter catches 5 and misses the rock beside the path in drive 408. It also drops drive 488, whose edit adds ridges across the path.
5. Model (`marsvq/model/features.py`, `train_eval.py`). Frozen DINOv2 ViT-S/14 features from the grayscale frame (the CLS token plus patch tokens pooled to a 4x3 grid) feed a ridge regression on the bearing. Cross-validation on the training sols, grouped by sol, sets the ridge strength. Each edit carries its source frame's label and stays in its source's fold. Each run touched the test set once.
6. Demo (`marsvq/demo/build_heldout.py`) renders the held-out frames, the page and the video.

## Known limits

- 46 test stops and 81 training stops are small numbers. The confidence intervals above reflect that.
- The label is the straight chord to the next stop. The rover's actual track between stops can curve, and labels skip any stop with no NavCam frame.
- The result is fragile. One run outside the plan used all 81 edits with no filter. Cross-validation picked a stronger ridge penalty for it, and it scored 15.7° MAE, the same as Mars only. The filtered run's larger error comes mostly from the weaker penalty that cross-validation picked for it. Neither run beats the constant baseline.
- The filter thresholds come from 9 judged edits. Treat it as a calibrated guess, not a tested classifier.

## Reproduce

The raw frames and API metadata live in `data/raw/`, which is not in git. The scripts download them again from NASA:

```sh
python3 -I marsvq/path/fetch_meta.py data/raw/real/m2020_navcam_meta 1 460
python3 -I marsvq/path/select_real.py data/raw/real/m2020_navcam_meta 1 339 data/real/train_labels.json
python3 -I marsvq/path/select_real.py data/raw/real/m2020_navcam_meta 340 460 data/real/test_labels.json
python3 -I marsvq/path/fetch_frames.py data/real/train_labels.json data/raw/real/m2020_navcam_select
python3 -I marsvq/path/fetch_frames.py data/real/test_labels.json data/raw/real/m2020_navcam_select
```

The edits are in git at `data/pairs/<stem>/edit.jpg`. The filter, features, model and demo need Python 3.12 with torch, torchvision, scikit-learn, opencv-python-headless and Pillow:

```sh
PY=path/to/venv/bin/python
$PY marsvq/metrics/edit_filter.py data/real/train_labels.json data/raw/real/m2020_navcam_select data/real/edit_filter_train.json
$PY marsvq/model/features.py data/real/features/train_real.npz $(python3 -c "import json;print(' '.join('data/raw/real/m2020_navcam_select/'+e['stem']+'.jpg' for e in json.load(open('data/real/train_labels.json'))))")
$PY marsvq/model/features.py data/real/features/test_real.npz $(python3 -c "import json;print(' '.join('data/raw/real/m2020_navcam_select/'+e['stem']+'.jpg' for e in json.load(open('data/real/test_labels.json'))))")
$PY marsvq/model/features.py data/real/features/train_edits.npz $(python3 -c "import json;print(' '.join('data/pairs/'+e['stem']+'/edit.jpg' for e in json.load(open('data/real/train_labels.json'))))")
$PY marsvq/model/train_eval.py
$PY marsvq/demo/build_heldout.py
```

## Earlier work in this repo

Before the model, the repo built image pairs with a synthetic arc as the label, the same arc on every frame (`marsvq/path/build_paths.py`, `docs/drive_edit_metrics.json`). `docs/REVIEW.md` explains why that could not train anything. Before that, a single Mastcam-Z photo (PIA24765) was edited and animated (`docs/results.md`, n=1). The video lost the source geometry by 1 s, which is why this project edits stills.

## Credits

NavCam frames and PIA24765: NASA/JPL-Caltech, used under the [JPL image use policy](https://www.jpl.nasa.gov/jpl-image-use-policy). Edits: xAI Grok Imagine. Features: DINOv2 (Meta AI, Apache 2.0).

`data/sim/` holds an elevation mesh from an earlier experiment and is not part of the demo. It comes from the USGS Mars Sample Return Terrain Relative Navigation HiRISE DTM and Orthoimage Mosaics, version soc_003, CC0 1.0 (DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)). HiRISE imagery credit: NASA/JPL/University of Arizona.
