# marsvq/demo status

**2026-10-17.** `index.html` is a single-image driving-data viewer. Each NavCam frame fills the window, and the frame's `path.json` is drawn on top as one green line. It needs no server, no build step and no network.

## How to open it

```sh
open marsvq/demo/index.html
```

Keep the repo layout as it is. The page loads images through `../../data/...`.

## Keys

| Key | Action |
|---|---|
| `→` or `↓` | Next frame (wraps around) |
| `←` or `↑` | Previous frame (wraps around) |
| `E` | Toggle between the source JPEG and `edit.jpg` |

The text line in the top left shows the frame stem plus `source`, `edit`, or `edit pending`. `edit pending` means edit view is on but the frame has no `edit.jpg`, so the page shows the source instead. The toggle applies to every frame, so stepping while in edit view stays in edit view.

## Pairs found

At 13:56 on 2026-10-17, `data/pairs/index.json` listed **6 pairs, 4 of them with an `edit.jpg`**. All six are sol-104 NavCam frames from `data/raw/real/m2020_sol0104_ncam/`.

| Frame stem | edit.jpg |
|---|---|
| `NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200` | yes |
| `NLF_0104_0676181093_823ECM_N0040510NCAM03104_01_295J01_1200` | yes |
| `NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200` | yes |
| `NLF_0104_0676181382_036ECM_N0040510NCAM03104_01_295J01_1200` | yes |
| `NLF_0104_0676181486_802ECM_N0040510NCAM02104_01_295J01_1200` | pending |
| `NLF_0104_0676181611_043ECM_N0040510NCAM02104_01_295J01_1200` | pending |

## How it finds data

- **Edits are checked when the page loads.** The page tries to load `data/pairs/<stem>/edit.jpg` as an image. When one of the two pending edits lands, reload the page and it shows up.
- **Index and paths are copied into the page.** Pages opened from `file://` can't fetch JSON, so `index.html` contains the stem, source JPEG path, `image_size` and path points for each pair, between the `PAIRS-BEGIN` and `PAIRS-END` markers. If `index.json` gains pairs or any `path.json` changes, regenerate that block from the files on disk. Never type the values in by hand.
- **Path mapping.** Path points are pixels in the source image (1200×900). Each point is drawn at `x / source_width × shown_width` and `y / source_height × shown_height`. The edits are 1152×864, and this mapping scales the line to fit them. The same `path.json` is drawn on both views. The first point of each path is below the image (y ≈ 1200), and the canvas clips it.

## Checks

Checked in headless Chrome from `file://` on 2026-10-17:

- Frame 1 in source view and in edit view, at 1200×900: the line sits in the same place on both images.
- Frame 3 in edit view and frame 6 with `edit pending`, at 1440×900: the image is letterboxed and the canvas stays aligned with it.
- The copied path arrays match all six `path.json` files on disk exactly (checked with a script).

Safari and Firefox weren't tested.

## Notes

- In frames 5 and 6 the path runs across the rover deck. These frames look sideways at the rover. The page draws `path.json` as it is.
- The frame 3 edit adds Jupiter to the sky, even though the edit prompt says "Add no new objects."
- The previous page, which showed PIA24765 clips with a terrain iframe, has been replaced. `marsvq/demo/frames/` is no longer used by the page.
