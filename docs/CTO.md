# CTO log, 2026-10-17 (evening): real labels, a model, a held-out number

I built the minimum from `docs/REVIEW.md`. The held-out result is negative: the Imagine edits made the model worse, and the model trained on real frames alone did no better than a constant. I am not signing off.

## Bearing spread (step 1)

`marsvq/path/next_stop.py` rotates the next stop's `extended.xyz` into the current rover frame with the current `attitude` quaternion, clips the chord to 20 m and projects it through the frame's CAHVORE model.

At the literal next drive counter, the labels are constant and fail the gate. In sols 101 to 110, each of the 7 forward, mast-down frames with its endpoint in view is followed by a 5 m straight bump. Their bearings have an sd of 1.1° and run from −0.6° to +2.1° (`data/real/step1_sol101_110_next_drive.json`).

So I changed the definition: the label is the first later stop at least 10 m away. I chose this, and the CEO's stop rule was written for the literal counter. With the 10 m rule, the 6 forward frames in sols 101 to 110 with an endpoint in view run from −33.1° to +2.8° (sd 14.2°). Over the full dataset, the bearings relative to the camera are:

| Set | Stops | Mean | SD | Min | Max |
|---|---|---|---|---|---|
| Train, sols 1 to 339, sites 3 to 8 | 81 | −6.2° | 19.7° | −44.6° | +44.3° |
| Test, sols 340 to 460, sites 9, 10, 23 to 25 | 46 | −0.8° | 19.4° | −36.9° | +45.3° |

The eye checks support the geometry. In 5 frames (drives 218, 350, 372, 738 and 822), every chord lies on ground below the horizon, and negative bearings land left of center. In drive 408, the light rock and sand streak left of the chord show up lower and further left in drive 430, taken 5 m forward, which fits a straight drive along the line. The 7 straight-bump bearings all come out within 2° of zero, which is what a correct quaternion convention gives for a rover driving forward. Two contact sheets of 12 random train and test frames looked right too. None of these checks matches the endpoint to the exact ground the rover reached; that would need a rear-looking frame from the next stop.

## Dollars spent

$5.11 logged: 73 image edits at $0.07 under agent `cto-real` in `~/Projects/xai-test/costs.jsonl`, all `ok`. No 402 or other billing error, no video calls, no premium model.

One caveat. The first batch process was killed by a 10-minute tool timeout at about 22:57 UTC, right after a logged call at 22:56:54. A request was probably in flight, so up to $0.07 more may have been charged without a log line. The worst case is $5.18, inside the $8 approval.

The other 8 training frames already had edits from earlier sessions, made with the same prompt and paid for then.

## Held-out table (step 4)

| Run | Training images | MAE | Median error | Within 10° |
|---|---|---|---|---|
| Constant (training mean, −6.2°) | 81 | 15.33° | 11.65° | 41% |
| Mars only | 81 | 15.72° | 11.49° | 37% |
| Mars + Imagine edits | 117 (36 edits) | 19.21° | 19.72° | 28% |

Paired bootstrap over the 46 test stops, 10,000 resamples:

- Mars + edits minus Mars only: +3.49°, 95% CI [+1.45°, +5.51°]
- Mars only minus constant: +0.39°, 95% CI [−1.70°, +2.52°]
- Mars + edits minus constant: +3.88°, 95% CI [+0.38°, +7.35°]

Cross-validation on the training sols, grouped by sol, gave MAE 15.84° for the constant (from an inline script, not `train_eval.py`), 14.84° for Mars only (alpha 3162) and 14.12° for Mars + edits (alpha 1000). The edits looked helpful in training and hurt on the new sites. The edit model shifts its test predictions left (mean −12.1° against a true mean of −0.8°). Site 24 holds 24 of the 46 test stops, 23 of them grayscale (against 30 of the 81 training frames), and it carries most of the loss (12.7°, 13.9° and 19.8° for the three runs).

One run outside the plan, from an inline script that is not committed: Mars plus all 81 unfiltered edits. Cross-validation picked alpha 5623 for it, and it scored 15.73° held-out, the same as Mars only. So the filtered run's larger error comes mostly from the weaker penalty that cross-validation picked on that subset, not from the edits being bad in themselves. Either way, no run beats the constant.

## What I built

- Labels: `marsvq/path/next_stop.py`, `fetch_meta.py` (NASA metadata for sols 1 to 460, free), `select_real.py` (one forward, ground-facing frame per stop, endpoint in view, automatic rules), `fetch_frames.py`. Outputs are `data/real/train_labels.json` and `data/real/test_labels.json`.
- Edits: 73 new `data/pairs/<stem>/edit.jpg`, made by `marsvq/imagine/batch_edit.py` with its unchanged prompt. No test frame was edited.
- Filter: `marsvq/metrics/edit_filter.py`. It drops an edit for new edges above the projected horizon (above 0.002 density), new edges concentrated in the 2.8 m path corridor (above 1.5 times the rest of the ground), or corridor shading that changes more than the rest of the ground (above 1.15 times). I set the thresholds on the 9 edits the review judged, before scoring any new edit (`data/real/edit_filter_calibration.json`). On those 9 it drops 510, 570 and 910 (planets), 710 (crevasse), 638 (mound) and 488 (ridges), and keeps 350, 810 and 408. 408 is a miss, because its added rock sits beside the path. 8 of those 9 calibration edits are also among the 81 training edits, so the filter was tuned partly on the data it then filtered. That doesn't touch the test set. On the 81 training edits it kept 36 (`data/real/edit_filter_train.json`). I looked at 4 of its calls (2 drops, 2 keeps) and agreed with all 4. `ADDS_OBJECTS` in `build_pairs.py` is no longer used.
- Model: `marsvq/model/features.py` (frozen DINOv2 ViT-S/14, grayscale input, CLS plus a 4x3 patch grid) and `train_eval.py` (ridge, alpha chosen by grouped CV on training frames only, each run tested once). The output is `data/real/results.json`.
- Demo: `marsvq/demo/build_heldout.py` writes `marsvq/demo/index.html`, `data/real/demo/` and `docs/demo.mp4` (56 s: 16 held-out frames, every third test stop in sol order, then the table). Green is the prediction, white is the real path. No glow, one caption line per frame.
- `README.md` and `docs/devpost.md` rewritten to these numbers.

## What I'd do next

The test number is too noisy to tune against, and tuning against it would spoil it. Better uses of the remaining time:

- More training stops: two or three frames per stop at different mast azimuths, still split by stop.
- Fix the ridge penalty in advance instead of picking it per run, so the edit comparison isn't confounded by the alpha choice.
- Check whether the real-only model fails because site 24 is almost all grayscale and unlike the training sites. That needs a second held-out range.

None of these changes the answer reported here.
