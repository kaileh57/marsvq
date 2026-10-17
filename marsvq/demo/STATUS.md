# marsvq/demo status

`index.html` steps through the 8 demo pairs listed in `data/pairs/demo_pairs.json`. Each frame fills the window with its `path.json` drawn as one 3 px #39e639 line. It needs no server, build step, or network.

```sh
open marsvq/demo/index.html
```

| Key | Action |
|---|---|
| `→` or `↓` | Next pair (wraps around) |
| `←` or `↑` | Previous pair (wraps around) |
| `E` | Switch between the NavCam source and the Grok Imagine edit |

The text line at the top shows the sol, the drive number, and which image is showing.

## Where the data comes from

`build_pairs.py` picks the pairs: frames marked `kept` in `data/pairs/drive_index.json` whose edit has recall of at least 0.5 in `docs/drive_edit_metrics.json`. It copies each source JPEG to `data/pairs/<stem>/source.jpg`, because `data/raw/` is not in git. It also writes the pair list into `index.html` between the `PAIRS-BEGIN` and `PAIRS-END` markers, since pages opened from `file://` can't fetch JSON. To change the pairs, rerun the script. Don't edit the block by hand.

Path points are pixels in the 1200x900 source. The edits are 1152x864. Each point is drawn at `x / 1200 × shown_width` and `y / 900 × shown_height`, so the same line lands on the same image content in both views.

`build_video.py` renders `docs/demo.mp4` from `data/pairs/demo_pairs.json` with the same line and mapping.
