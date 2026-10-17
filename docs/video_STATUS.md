# Video status: docs/demo.mp4

Rendered by `marsvq/demo/build_video.py` from `data/pairs/demo_pairs.json`. This replaces the earlier 37 s cut of three sol-104 frames.

- 25.0 s, 1200x960, 24 fps, H.264 (yuv420p, CRF 20), one video stream, no audio.
- 5 pairs in drive order (sol 102 drive 350 to sol 109 drive 810; drives 408, 570, 910 removed for adding objects). Each pair shows the NavCam source for 2.5 s, then the Grok Imagine edit for 2.5 s, with hard cuts.
- Both shots of a pair carry the same `path.json` as one 3 px #39e639 line. The edit is resized to 1200x900 before drawing so the path pixels line up.
- One caption line under the image: sol, drive, and either "Source (NASA/JPL-Caltech)" or "Grok Imagine edit, edge recall" with the value from `docs/drive_edit_metrics.json`.

Three of the edits in the video add objects that are not in the source (drives 408, 570, and 910). See the edge check table in `README.md`.
