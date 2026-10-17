# Source-geometry overlap, PIA24765 crop

n=1 per condition. This is not a benchmark.

| condition | compared to | t_sec | IoU | recall | test density | chance IoU |
|---|---|---|---|---|---|---|
| A_drive | source still | 0 | 0.623 | 0.807 | 0.314 | 0.202 |
| A_drive | source still | 1 | 0.364 | 0.551 | 0.336 | 0.211 |
| A_drive | source still | 2 | 0.328 | 0.524 | 0.375 | 0.226 |
| A_drive | source still | 4 | 0.296 | 0.482 | 0.373 | 0.225 |
| A_drive | source still | 5 | 0.254 | 0.440 | 0.407 | 0.237 |
| B_prompted_europa | source still | 0 | 0.620 | 0.807 | 0.314 | 0.202 |
| B_prompted_europa | source still | 1 | 0.215 | 0.373 | 0.418 | 0.241 |
| B_prompted_europa | source still | 2 | 0.238 | 0.411 | 0.424 | 0.243 |
| B_prompted_europa | source still | 4 | 0.257 | 0.459 | 0.443 | 0.249 |
| B_prompted_europa | source still | 5 | 0.240 | 0.419 | 0.442 | 0.249 |
| C_edit_still | source still | still | 0.511 | 0.874 | 0.480 | 0.260 |
| C_video_from_edit | edited still | 0 | 0.673 | 0.871 | 0.438 | 0.297 |
| C_video_from_edit | edited still | 1 | 0.371 | 0.545 | 0.465 | 0.309 |
| C_video_from_edit | edited still | 2 | 0.370 | 0.541 | 0.465 | 0.309 |
| C_video_from_edit | edited still | 4 | 0.356 | 0.535 | 0.486 | 0.318 |
| C_video_from_edit | edited still | 5 | 0.363 | 0.577 | 0.531 | 0.337 |

Dilated-edge density of the reference: source still 0.362, edited still 0.480 (fraction of pixels). For independent maps at reference density p and test density q, chance IoU is pq/(p+q-pq) and chance recall is q. Frame 0 of the A video is not a pixel copy of the source: its gray values correlate with the resized source at about 0.53 and the framing differs.

## Method

For each video we took the frames nearest 0, 1, 2, 4 and 5 s (frames 0, 24, 48, 96, 120 at 24 fps), resized the reference still to the 736x400 frame size with Lanczos (a small aspect stretch, source 1.78, edit 1.81, video 1.84), and converted every image to 8-bit grayscale with Pillow; the edited-versus-source still row uses the same 736x400 size.
Edges come from a numpy Canny with Gaussian sigma 1.4, Sobel L2 magnitude, 4-direction non-maximum suppression, and hysteresis thresholds 30/60, fixed for every image.
IoU is the intersection over union of the two edge maps after each is dilated by 3 pixels (three passes of a 3x3 maximum).
Recall is the fraction of undilated reference edge pixels that have a test edge within 3 pixels; the reference is the source still for A, B and the edited still, and the edited still for the C video.
