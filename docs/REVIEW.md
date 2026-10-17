# Adversarial review, 2026-10-17

Reviewed at commit `7620347` (the commit on `origin/main`). I read the code, the metrics JSON, the README, the devpost text, and the logs. For every one of the 9 drive edits, I rendered source and edit side by side with the path drawn on both and looked at the full frame and a crop of the path corridor. Pixel coordinates below are in the 1152x864 edit frame.

## 1. Was a driving model trained?

No. The repo has no training code, no loss, no checkpoint, and no held-out number.

- A search of every `.py`, `.md`, `.html` and `.json` file outside the venv and the design spec for `torch`, `loss`, `train`, `optim`, `epoch`, `checkpoint`, `sklearn` and `policy` finds no training code. The only hits are sentences that say no model exists: `README.md:5` ("There is no trained policy here") and `docs/devpost.md:41` ("no trained model").
- The design spec plans the model that is missing. `MarsVQ_spec.md:25` calls "a table of path error (ADE/FDE) and hazard recall … with the sim-only model next to the Imagine-trained model" the headline result. Line 36 (G4) calls for "a path net trained twice (sim-only vs. sim + Imagine)", and line 447 lists `model/pathnet.py losses.py train.py eval.py`. No `marsvq/model/` directory exists.
- No `.pt`, `.pth`, `.ckpt`, `.safetensors`, `.onnx`, `.npz` or `.pkl` file exists. The only venv (`marsvq/sim/.venv`) has rasterio and numpy, and no ML framework.
- The only numbers in the repo are Canny edge recall and IoU between each edit and its source (`docs/drive_edit_metrics.json`). They measure the image edit. They say nothing about driving.

## 2. Are the path labels real driving, or synthetic?

They are synthetic, and worse: all five demo labels are the same curve.

`marsvq/path/build_paths.py` builds one fixed arc for every frame: 33 points out to 20 m, a constant left bend of 1/80 per m, started from the camera footprint and pointed along the boresight. The arc depends only on the camera pose. It never looks at the image, the terrain, or where the rover went next.

Every kept frame has the same mast pose: azimuth 359.80° to 359.81°, elevation −29.88° (`data/pairs/drive_index.json`). So the five labels in `data/pairs/demo_pairs.json` agree to within 0.02 px in each coordinate. Each one runs from (606, 1202) to (520, 154) in 1200x900 pixels. In the viewer, the green line stays in the same place as you step through pairs.

The arc is not a drive the rover would take:

- In sol 107 drive 638, the far end of the arc runs onto a rock on the hillside at about (515, 160), in the source as well as the edit.
- The first point is at v = 1202, below the 900-px frame, so the bottom of every line is clipped. Only 26 of the 33 points are in frame.
- The left bend is a constant (`TURN = "left"`). It ignores the terrain.

A network trained on these pairs would not learn to drive. Its best output is a constant, the arc, and it would reach zero loss by ignoring the input. Even with varied labels, a net trained on labels from a closed-form projection learns the projection.

The repo already holds what real labels would need. `data/raw/real/m2020_sol0101_0110_ncam_drive/raw_image_api_metadata.json` stores each frame's site-frame rover position (`extended.xyz`) and attitude quaternion (`attitude`). Between the 16 stops, the rover moved 4.9 m to 51.1 m. The code never reads these fields.

## 3. Do the edits keep the scene well enough that the same path is a valid label?

Discrete rocks mostly survive. The ground under the line does not. I counted with these definitions:

- **Adds an object:** a new discrete object, such as a rock or a planet, or new relief that reads as an obstacle on the line.
- **Moves a rock:** a source rock whose position visibly shifts in the edit.
- **Changes the ground under the line:** new relief with visible height (ridges, drifts, mounds, cracks, slab edges) in the path corridor where the source is flat regolith.

| Sol / drive | Recall | IoU | Adds an object or obstacle on the line | Moves a rock | Changes the ground under the line | What I saw |
|---|---|---|---|---|---|---|
| 102 / 350 | 0.880 | 0.204 | no | no | yes | Rocks stay in place. Smooth sand ripples near the rover become sculpted snow drifts on both sides of the line (y ≈ 630 to 830). The light, flat outcrop patches next to the line at mid-range vanish into the white. |
| 104 / 488 | 0.749 | 0.195 | no | no | yes | The three pebbles I checked near the line stay put. The flat, pebbly plain becomes a crust with raised scalloped ridges that cross the line (y ≈ 380 to 430 and 580 to 730). The pebble texture is gone. |
| 107 / 638 | 0.743 | 0.417 | **yes** | no | yes | A flat, light bedrock patch on the line becomes a raised mound sitting on the line at about (600, 380). A flat patch left of the line near the rover becomes a large mound like a boulder (x 460 to 570, y 640 to 780). Three more mounds rise right of the line (x 630 to 730, y 620 to 690). This pair has the highest IoU of the nine. |
| 108 / 710 | 0.871 | 0.307 | **yes** | no | yes | The pebbles match closely. The edit adds dark open crevasses across the ground, and one crosses the line near the rover (x 570 to 630, y 690 to 810). The source is flat there. |
| 109 / 810 | 0.699 | 0.308 | no | no | yes | The large rock stays in place. Most pebbles near the rover are erased. Drift banks cross the line at mid-range (y ≈ 280 to 380). |

Totals over the 5 demo pairs:

- **New discrete objects: 0 of 5.** Hand-removing drives 408, 570 and 910 (`ADDS_OBJECTS` in `marsvq/demo/build_pairs.py`) did remove every planet and invented rock.
- **New obstacles on the line: 2 of 5.** These are the mound in 638 and the crevasse in 710. A label that drives straight across them is wrong for the edited image.
- **Moved rocks: 0 of 5** at the scale I checked. I didn't match features pixel by pixel, so shifts of a few pixels would go unseen.
- **Ground under the line changed: 5 of 5.** The prompt turns flat regolith into terrain with relief in every pair. A path label for flat sand is not plainly valid on fractured slabs and drifts.

The edge metric can't see this. It scores 638, the pair with the most invented relief, as the best IoU in the set (0.417). Recall can't fall when edges are added, and the edits have 2 to 4 times the source edge density (`edit_dilated_edge_density` 0.32 to 0.64 against 0.15 to 0.21 for the sources). The README says both of these things itself. Its "What the edit added" column is still blank for all five demo rows, and that blank reads as "clean." That is not what the pixels show.

The README also understates the dropped pair 408. Besides the rock beside the path, the edit turns the whole corridor into pools of open blue ice with snow banks (I checked this crop as well).

## 4. Is the demo a system or a slideshow?

It is a slideshow built by a pipeline. The scripts chain together (project with `build_paths.py`, select with `select_drive.py`, edit with `batch_edit.py`, score with `navcam_edits.py`, publish with `build_pairs.py`). What a judge sees is five fixed image pairs with one fixed polyline:

- `marsvq/demo/index.html` holds the five pairs as a JSON block written into the page. It shows an image and strokes the stored points. Nothing is computed, predicted, or run at view time.
- `docs/demo.mp4` is 25.0 s of the same five pairs at 2.5 s per image.
- The two quality gates are a person looking at pictures. `ADDS_OBJECTS = {408, 570, 910}` in `build_pairs.py` is a hand-picked list. The saturation threshold in `select_drive.py` was "set by looking at the 11 ground-facing frames" (its docstring).
- n = 9 edits, 5 shown. That is a sample, not a dataset.
- It can't be reproduced from the public clone. `docs/drive_edit_metrics.json` and `data/pairs/drive_index.json` point at `data/raw/...`, which `.gitignore` excludes. `marsvq/demo/STATUS.md` still says the viewer shows 8 pairs. It shows 5.

## 5. Would a DubHacks judge believe Grok Imagine was used as a world model to train driving?

No. Claiming a world model for driving means something was trained on the generated data and drove better for it. Here, nothing was trained. The generator was used as a style filter on stills, not as a world model that responds to actions. The label is one constant curve. In three minutes, a judge sees a green line that never moves on five images that turn from orange to white, and the edited ground grows ridges and cracks the line drives through. Anyone who presses the arrow key twice sees that the label doesn't change.

The writing is honest. The README and devpost say "no trained model" and "synthetic paths." That honesty is what will keep a judge from believing the headline claim. The devpost header adds to the confusion: "Title track: Visa … Visa is the submission slot; the work is the driving-pair system."

## Minimum build that would change NO to YES

It is 15:36 PT, which leaves about 7 hours before 22:30. A YES needs three things: labels that change with the image and come from real motion, a model trained on them, and one held-out number showing whether the Grok edits helped. In priority order:

1. **Real labels from the pose fields already in the repo (about 1.5 h).** For each stop, rotate the next stop's `extended.xyz` into the current rover frame with `attitude`, then project the chord, clipped to 20 m, through the frame's CAHVORE model. Check 3 frames by eye: the projected endpoint should land on ground the rover then reached. Then print the spread of label bearings across frames. If the bearings barely vary, or the projection can't be checked, stop: the labels are constant again and no training will produce a credible number.
2. **Enough frames to split (about 1.5 h, mostly API wait).** Pull 60 to 100 forward-facing NavCam frames at stops whose next stop is known, from the sols the CTO scan already covered. Keep a different site or sol range (for example sols 340 to 360) as the real held-out test set. Edit only the training frames. 60 to 100 edits at $0.07 cost $4.20 to $7.00. That is over the $4 batch cap recorded in `docs/CTO.md`, and the top end is over the $6 session cap. **This spend needs your approval.**
3. **An automatic edit filter to replace `ADDS_OBJECTS` (about 45 min).** Flag new blobs above the projected horizon row, and flag a corridor edge-density or relief jump of more than k times the source. At 60 edits, hand-checking becomes the bottleneck. A judge's first question will be how you know the label still holds.
4. **One small model and one table (about 1.5 h).** Use frozen pretrained image features with a linear or ridge head that predicts label bearing, or endpoint u, from the image. Split by stop, never at random, because neighboring frames are near-duplicates. Train three versions: a constant baseline, Mars-only, and Mars plus the edits. Test all three on the **real** held-out site. Testing on edits of held-out frames would only measure the generator. If Mars plus edits doesn't beat Mars-only on real held-out frames, report that, and the sign-off stays NO.
5. **A demo that shows predictions (about 1 h, only if steps 1 to 4 land).** On held-out real frames, show the predicted path next to the real next-stop path, with the table from step 4 on screen. That replaces the slideshow.

Steps 1, 2, 4 and 5 are the minimum. Step 3 is what makes step 2 defensible. If step 1 fails, nothing after it can change the verdict.

SIGN-OFF: NO
