# MarsVQ

MarsVQ builds driving-data pairs from real Mars rover photos. Each pair has three parts:

- A real Perseverance NavCam frame from sol 104.
- A ground-plane driving path projected into that frame through the frame's own CAHVORE camera model.
- A Grok Imagine edit of the same frame, restyled as Europa ice.

The edit keeps the camera position and framing, so the path drawn for the source frame can be reused as the path label for the edited frame.

## What is in the repo

The six source frames are 1200×900 NavCam left-eye browse JPEGs from Perseverance on sol 104 (2021-06-05 UTC). Five of them come from one rover stop and look out at different azimuths. The sixth was taken about 5 m away. They form a panorama set, not a drive sequence.

`marsvq/path/build_paths.py` writes one path per frame to `data/pairs/<stem>/path.json` and lists all six in `data/pairs/index.json`. It uses the full CAHVORE model from the NASA raw-image API, which is a fisheye model (type 2). The path is a flat-ground arc of 33 points out to 20 m. It bends left at a curvature of 1/80 m⁻¹ and follows each frame's camera boresight. In every frame, 26 of the 33 points fall inside the image. The predicted horizon row matches the visible far-plain edge in all six frames to within about 10 to 25 px. These are synthetic paths, not paths the rover drove.

`marsvq/imagine/batch_edit.py` sends each frame to the xAI image edit endpoint (`POST /v1/images/edits`, model `grok-imagine-image-2.0`) with one fixed prompt. The prompt asks for Europa ice and asks the model to keep every rock, the horizon, and the camera unchanged. Each edit is saved as `data/pairs/<stem>/edit.jpg` at 1152×864.

The batch stopped at 4 edits of 6. The fifth call returned HTTP 402 with code `personal-team-blocked:spending-limit`, and the sixth was not attempted. The four edits cost $0.07 each.

## Open the demo

From the repo root, run:

```sh
open marsvq/demo/index.html
```

The page needs no server, build step, or network connection. It loads images through `../../data/...`, so keep the repo layout as it is.

Each frame fills the window with its path drawn as a green line. To move between frames, press the arrow keys. To switch between the source JPEG and `edit.jpg`, press `E`. Frames without an edit show `edit pending` and display the source instead. The same `path.json` is drawn on both views, scaled to the image size. The demo was checked in headless Chrome. Safari and Firefox were not tested.

## Known limits

- In two of the six frames, the camera looks sideways at the rover and the path runs across the rover deck. The labels carry no occlusion mask.
- The frame 3 edit adds Jupiter to the sky, even though the prompt says "Add no new objects."
- The path assumes flat ground at z = 0 in the rover frame and ignores about 1.6° of rover tilt.

## Edge overlap check

`docs/results.md` compares edge maps from an earlier test on a different photo, a crop of NASA PIA24765 (a Mastcam-Z view of the Jezero crater floor). There is n=1 per condition, so this is not a benchmark.

| Condition | Compared to | Time | Edge IoU | Chance IoU |
|---|---|---|---|---|
| Image edit to Europa | source still | still | 0.511 | 0.260 |
| Video prompted as Europa | source still | 1 s | 0.215 | 0.241 |
| Video animated from the edited still | edited still | 5 s | 0.363 | 0.337 |

The edited still keeps clearly more source edges than chance. The video prompted directly as Europa falls below chance by 1 s.

## Credits

The NavCam frames are NASA/JPL-Caltech raw images, used with the credit "NASA/JPL-Caltech" under the JPL image use policy. PIA24765 is also NASA imagery.

The separate elevation mesh comes from the USGS Mars Sample Return Terrain Relative Navigation HiRISE DTM and Orthoimage Mosaics, version soc_003, released under CC0 1.0 (DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)). Citation: Bland, M. T., Galuszka, D. M., Hare, T. M., Mayer, D. P., Redding, B. L., Wheeler, B. H., 2024, *Mars Sample Return Terrain Relative Navigation HiRISE DTM and Orthoimage Mosaics*, USGS Data Release. HiRISE imagery credit: NASA/JPL/University of Arizona. DTM production by USGS Astrogeology. This DTM strip does not cover the sol 104 site, so the mesh and the NavCam frames show different places.
