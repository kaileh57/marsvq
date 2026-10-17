# marsvq/demo status

`index.html` steps through 16 held-out NavCam frames (every third test stop in sol order) and shows the held-out results table. On each frame, the green line is the Mars + edits model's predicted direction to the next stop and the white line is the real one. The arrow keys step through frames. The page needs no server, build step or network.

```sh
open marsvq/demo/index.html
```

`build_heldout.py` writes the page, the frames in `data/real/demo/` and `docs/demo.mp4` from `data/real/results.json`. Rerun it after `marsvq/model/train_eval.py`; don't edit the page by hand.

`build_pairs.py` and `build_video.py` built the earlier synthetic-arc demo. They are superseded, and running `build_pairs.py` would fail because the page no longer has its `PAIRS-BEGIN` markers.
