# MarsVQ

Team: solo, Kellen Heraty (Discord: DISCORD_TBD)

Title track: Visa

Side track: SpaceXAI

Other tracks: none

Repo: https://github.com/kaileh57/marsvq

Video: https://github.com/kaileh57/marsvq/blob/main/docs/demo.mp4

Visa is the submission slot. The project is a test of Grok Imagine edits as driving training data.

## What it does

MarsVQ tests whether Grok Imagine edits of Mars rover photos help train a driving model. It labels real Perseverance NavCam frames with the direction the rover actually drove next. It trains a small model on those frames, once alone and once with Imagine edits of them, and tests both on stops from a later part of the mission that neither model saw.

The edits had no detectable effect in either direction. On 46 held-out stops (sols 340 to 460), the error in the next-stop direction was 15.7° for the model trained on real frames and 17.3° for the model trained with edits, both at the same ridge penalty. Resampling the 14 test sols, the 95% confidence interval on the difference is −1.3° to +3.0°. Predicting a constant scored 15.3°, so the real-only model shows no skill on the new sites either.

The demo and the 56 s video show 16 of those held-out frames. Each has the model's predicted direction in green and the real next-stop direction in white, and the results table closes the video.

## How I built it

Each NASA raw-image API record carries the rover's site-frame position, its attitude quaternion, and the camera's CAHVORE model. For each stop, I rotate the next stop's position into the current rover frame and project the chord into the image through that camera model. The first attempt used the literal next drive counter. It gave a 5 m straight bump after almost every forward frame, with bearings within 2° of zero. A label that never changes trains nothing, so I took the first later stop at least 10 m away. Those bearings range from −45° to +45°.

Metadata for sols 1 to 460 gave 81 training stops (sols 1 to 339) and 46 test stops (sols 340 to 460) at different sites. Each stop contributes one forward, ground-facing NavCam frame, picked by fixed rules.

I edited all 81 training frames into Europa ice with grok-imagine-image-2.0 and the same prompt as before, for $5.11. An automatic filter then dropped any edit that added edges above the projected horizon, or that changed the 2.8 m corridor under the path more than the rest of the ground. It kept 36 of the 81.

The model is frozen DINOv2 ViT-S/14 features with a ridge regression head. Cross-validation on the training sols, grouped by sol, picked the ridge strength once on the real-only model, and the edit model used the same value. Each edit took its source frame's label and stayed in that frame's fold.

## What failed

The main result is a failure: edits did not help, and the real-only model did not generalize to new sites. In cross-validation on the training sols, both models beat the constant baseline by 1 to 2°. Neither gain survived a change of site.

The result is also noisy. With 81 training stops, the choice of ridge penalty moves the answer by several degrees. When each model got its own penalty, the edit model scored 19.2° and looked clearly worse. With one penalty for both, the gap shrinks to 1.6° and its interval crosses zero.

The filter is a calibrated guess. I set its thresholds on 9 earlier edits that a reviewer had judged by eye. The reviewer flagged 6 of those for an added object or an obstacle on the path. The filter catches 5 and misses a rock placed beside the path.

Earlier in the weekend, the labels were a synthetic arc, identical on every frame, and nothing was trained. A review caught it, and this version replaces it.

## Built with

Python, numpy, PyTorch, DINOv2, scikit-learn, OpenCV, Pillow, ffmpeg, xAI Grok Imagine image edit (grok-imagine-image-2.0), NASA Mars 2020 raw-image API.

## Credits

NavCam images: NASA/JPL-Caltech. DINOv2: Meta AI.
