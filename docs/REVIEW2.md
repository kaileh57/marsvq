# Review 2, 2026-10-17, 16:15 PT

Scope: `docs/CTO.md`, `data/real/results.json`, `data/real/{train,test}_labels.json`, `data/real/edit_filter_train.json`, the feature files in `data/real/features/`, `marsvq/path/next_stop.py`, `select_real.py`, `marsvq/model/features.py`, `train_eval.py`, `marsvq/demo/build_heldout.py`, `marsvq/demo/index.html`, `data/real/demo/` (all 16 frames and `table.png`), `docs/demo.mp4` (length only), `README.md` and `docs/devpost.md`. I didn't run any script in the repo. I ran read-only analyses on the committed labels, predictions and features. Nothing was edited, built or paid for.

## What matches the claim

The CTO built what `docs/CTO.md` says it built. Specifically:

- **Labels come from real motion and vary.** `next_stop.py` rotates the next stop's `extended.xyz` into the current rover frame with `attitude` and projects the chord through each frame's CAHVORE model. Test bearings run from −36.9° to +45.3° (sd 19.2°). This is no longer the constant arc from the first review.
- **The split is by site, with no shared stems.** Train covers sites 3 to 8 and test covers sites 9, 10, 23, 24 and 25. No stem and no site appears in both. The sols actually used are 15 to 285 (train) and 340 to 443 (test). "1 to 339" and "340 to 460" are the search ranges, not the data.
- **No test label reaches the model.** Features are standardized on training rows. The ridge alpha is picked by `GroupKFold` on training sols only, and edits stay in their source's fold. `train_eval.py` touches the test set once per run. The one exception is the uncommitted unfiltered-edits run, a second look at the test set. CTO.md and the README both disclose it.
- **The test label does shape test selection.** `select_real.py` keeps a frame only if the projected endpoint is in the image. That uses the test label, but the same rule applies to train, and it only bounds bearings to the camera's field of view. It is not a leak into the model.
- **Every table number matches `results.json`.** The cost ($5.11 logged, at most $5.18) is inside the $8 approval.
- **The demo shows varying predictions.** The green line moves frame to frame (predictions from −32.9° to +23.8°). Frames are every third test stop in sol order, not cherry-picked.

The experiment is real. The reported comparison is not sound.

## The headline comparison is confounded

The README, devpost, `index.html` and the video's closing card all say the edits made the model worse: +3.5° MAE, 95% CI [+1.4°, +5.5°]. Three problems sit under that number.

### 1. The two runs use different ridge penalties

Cross-validation picked alpha 3162 for Mars only and alpha 1000 for Mars + edits. Held-out MAE swings by several degrees with alpha alone. I refit both runs at matched alphas from the committed features:

| Alpha | Mars only | Mars + 36 filtered edits | Mars + the 36 source frames duplicated (no edits) | Mars + all 81 edits |
|---|---|---|---|---|
| 1000 | 17.49° | 19.21° | 18.24° | 19.40° |
| 3162 | 15.72° | 17.29° | 16.73° | 16.60° |
| 5623 | 15.01° | 16.41° | 16.04° | 15.73° |

At matched alpha, the edit penalty is 1.4° to 1.7°, not 3.5°. About 1.8° of the headline gap is Mars only scored at alpha 3162 against the edit run at alpha 1000.

The Mars-only versus constant verdict also flips with alpha. At alpha 5623, Mars only scores 15.01° and beats the constant (15.33°). Both headline claims ("edits hurt" and "no skill") depend on which alpha cross-validation happened to pick.

### 2. The filter selects edits by label, which shifts the training target

The filter decides from the path corridor, and the corridor is drawn from the label. The 36 kept edits have a mean source bearing of −12.2°. The 45 dropped ones have −1.5°. Adding the 36 kept rows pulls the training mean from −6.2° to −8.1°, while the test mean is −0.8°.

The third column of the table above is the control. It duplicates the same 36 real source frames, with no edit pixels, and it reproduces 0.75° to 1.0° of the 1.4° to 1.7° gap. What is left for the edit content itself is 0.4° to 0.7°.

The predictions say the same thing. Mars + edits correlates 0.97 with Mars only and averages −12.1° against Mars only's −6.5°, so it is mostly the Mars-only model shifted left.

### 3. The confidence interval treats correlated frames as independent

21 of the 46 test stops come from one drive on sol 427: VCE frames 10 to 13 m apart with identical mast pointing, several sharing a next stop. Training has the same problem, since sols 65, 66 and 72 supply 32 of the 81 stops.

A bootstrap over the 14 test sols instead of the 46 stops gives:

- Edits minus Mars only: +3.49°, 95% CI **[−0.73°, +5.68°]**
- Mars only minus constant: +0.39°, CI [−2.90°, +2.48°]
- Edits minus constant: +3.88°, CI [−3.13°, +6.83°]

Once resampled by sol, the "edits hurt" interval crosses zero even before the alpha and filter fixes. "The edits hurt" is not supported. What the data supports is no detectable effect in either direction, with this much noise.

### 4. The test set is out of distribution in a way nobody controlled

27 of the 46 test frames are `NLMV` products (TRAV and VCE drive-sequence frames). The training set has none: 51 are `NLF_` and 30 are `NLM_`. Site 24 alone is 24 of 46 and nearly all grayscale. CTO.md names the grayscale share but not the product type. This doesn't make the null wrong. It means "doesn't generalize to new sites" may really be "doesn't generalize to a new frame type."

## The writing

CTO.md is candid. It reports the alpha confound, the uncommitted runs and the calibration overlap. The README and devpost keep that candor in their limits sections, but each one contradicts its own headline:

- The README says "The edits hurt" with the per-stop CI. Its "Known limits" then says the larger error "comes mostly from the weaker penalty." Both can't be the finding.
- The devpost's "What it does" states "The edits made the model worse" with the CI. Its "What failed" calls the result fragile.
- The judge-facing artifacts carry only the headline. `table.png`, the `index.html` note and the video's final card show "+3.5°, 95% CI [+1.4°, +5.5°]" and nothing about the penalty or clustering.

A judge reading the devpost header or watching the video leaves with "the edits hurt, significantly." The repo's own control (unfiltered edits at 15.7°, equal to Mars only) and my clustered bootstrap say that isn't established. This isn't hiding the negative result. It overstates it, and it fails the same test.

## The demo

- **It shows predictions on real held-out frames, with the real path.** This is a real step up from the five-pair slideshow. Nothing runs at view time, which is acceptable for a demo.
- **The green line is the worst of the three models.** This is disclosed and is a legitimate choice. The green line's length and end height are copied from the true label. The README says so, but the page and video don't.
- **10 of the 16 frames are grayscale sol-427 and site-24 frames,** where green sits consistently left of white. A careful judge would see the leftward bias, which is honest.
- **The video has no title card or one-line setup.** Its first frame is a NavCam image with two lines and a caption. In a three-minute slot, a judge needs the question before the frames.

## Verdict

The experiment is real. The labels are real, the split is clean, the model is real, the demo shows predictions, and nothing leaks from the test set into training. The comparison it reports is confounded by the alpha choice and by label-dependent filtering, and its interval is too narrow for clustered test data. The judge-facing table, page and video state the confounded number as a finding. Under the rule for this review, a fragile or confounded comparison stays NO.

## Smallest change that could flip it before 22:30 PT

In `marsvq/model/train_eval.py`, fix one ridge alpha for every run, picked once by the existing grouped CV on Mars only, and make the paired bootstrap resample sols instead of stops. Then rerun `train_eval.py` and `build_heldout.py`. Rewrite the README and devpost headline sentence to whatever comes out. If the clustered interval spans zero, that sentence is "no detectable effect of the edits in either direction," not "the edits hurt."

SIGN-OFF: NO
