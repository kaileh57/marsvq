# CTO log, 2026-10-17

## What I measured

The four NavCam edits already in `data/pairs/` were scored against their source JPEGs with the edge code from `marsvq/metrics/geometry.py` (`marsvq/metrics/navcam_edits.py`, output `docs/navcam_edit_metrics.json`, n=4). Recall was 0.749, 0.995, 0.463, and 0.790. Median recall was 0.769 and median IoU 0.223. That is above the 0.6 bar, so I built the forward-looking set.

Two caveats came out of that first pass, and both hold for the drive set too. First, the edits have 2 to 3 times the edge density of their sources, so an unrelated edit would score a recall of roughly 0.32 to 0.64. Second, the 0.995 frame looks across the rover deck: the rover hardware survives the edit, and the edit invents large rocks on the ground.

The drive set came from the NASA raw-image API. I scanned sols 100 to 140, 200 to 215, and 340 to 360 for full-frame NavCam images with the mast within 25° of straight ahead. No single sol had more than 6 such stops, so I took one frame per stop across sols 101 to 110 at site 4: 16 frames, 273 m of travel. Seven were dropped (`marsvq/path/select_drive.py`). Five point the mast 25° above the horizon, and in two the near path crosses the deck rail. I found the rail crossings by looking at the frames. The saturation threshold in the script records that check and has not been tested on other frames.

Seven new edits plus the two that already existed give 9 scored drive edits (`docs/drive_edit_metrics.json`). Median recall is 0.744 and median IoU 0.241. Eight pass the 0.5 cut and are in the demo. Looking at them by eye, 4 of the 9 add objects the prompt forbids: a planet in three skies, and a rock beside the path in drive 408. The cut removed only one. The table in `README.md` marks each case.

## What I spent

$0.49, which is 7 image edits at $0.07 under agent `drive-batch` in `~/Projects/xai-test/costs.jsonl`. No 402s or billing errors. No video generation calls. The session cap was $6 and the batch cap $4. Every logged row on the key adds up to $1.51.

## What I shipped

- `docs/navcam_edit_metrics.json` (gate, n=4) and `docs/drive_edit_metrics.json` (drive set, n=9)
- `docs/frame_sources.md`: all 16 frame URLs, with the keep or drop decision and the reason for each
- 7 new `edit.jpg` files and `source.jpg` copies for the 8 demo pairs, so the viewer and video work from a clone
- `marsvq/demo/index.html`: steps through the 5 pairs. Arrow keys and E. One text line and the NASA credit.
- `docs/demo.mp4`: 25.0 s, silent, hard cuts, one caption line, 5 pairs
- `README.md` and `docs/devpost.md`, rewritten to match these files. Devpost keeps `DISCORD_TBD`. The video line now points at `docs/demo.mp4` on GitHub, because the mp4 is in the repo. If Devpost's video field requires YouTube or Vimeo, someone has to upload it there.
- Scripts: `select_drive.py`, `navcam_edits.py`, `build_pairs.py`, `build_video.py`. `build_paths.py` and `batch_edit.py` now take explicit inputs. The path definition and the edit prompt are unchanged.

## What I refused to spend on

- Video generation. The edge check is too weak to call any edit "passed" in a sense that would justify animating it, and video failed the geometry check on PIA24765.
- Re-editing frame 0676181181. It already had an edit, which failed, and the task says to skip existing edits.
- More frames to pad the count. Eight pairs is enough for the demo.
- Retrying the 3 visibly flawed edits that stayed in the demo. A retry with the same prompt is a coin flip, and a better test would have to come first.

## What I'd do next

Before spending anything else, write a check that detects added objects. I tried the cheap version, edge precision (the fraction of edit edges within 3 px of a source edge), and it does not work. It ranges from 0.22 to 0.58 across the 9 drive edits, because the ice texture adds edges everywhere, and the 3 flawed demo edits score 0.23 to 0.33, inside the range of the clean ones. A useful check has to be local. Candidates are new edges above the projected horizon row, which would catch a planet in the sky, and new dark blobs within a few pixels of the path, which would catch a rock. I have not built either.
