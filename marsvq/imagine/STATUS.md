# marsvq/imagine status

**2026-10-17. Session spend: $0.30 of the $1.50 cap** (1 image at $0.04, 2 Lite 6 s videos at $0.13 each). No errors and no retries. Each call is logged to `~/Projects/xai-test/costs.jsonl` with agent `imagine`.

## What's here

- `client.py`: stdlib-only client. It reads the key from `$XAI_API_KEY` or `~/.config/xai/key` and never prints it. It allows only `grok-imagine-image-2.0` and `grok-imagine-video-1.5-lite`, and caps clips at 6 s. Before every call it checks the budget against the `imagine` rows in `costs.jsonl` (`MARSVQ_IMAGINE_BUDGET_USD`, default 1.50). On HTTP 429 it waits 30 s and retries once. A billing, quota or limit error raises `BillingError`. Sidecar `.json` files leave out the signed video URL.
- `cli.py`: `python3 -m marsvq.imagine image --prompt ... --out ...` and `python3 -m marsvq.imagine video --prompt ... --image <file-or-url> --seconds 6 --out ...`. On a billing or budget stop, it appends the error to this file. There's no `pyproject.toml` yet. To get the `marsvq-imagine` command, add `marsvq-imagine = "marsvq.imagine.cli:main"` under `[project.scripts]`.
- Prompts are in `configs/prompts.yaml`. It holds the spec §5 world templates and a new `i2v` section with the two prompts used here.
- API notes: image generation returns **JPEG** (`mime_type: image/jpeg`) with `usage.cost_in_usd_ticks`, so the client saves it as `.jpg`. Lite output is 736×400, 24 fps, 145 frames (6.04 s). Each job took about 18 s, and the two jobs ran at the same time.

## Outputs (`data/imagine/`)

- Start frame: NASA PIA24765, a Perseverance Mastcam-Z view of the Jezero crater floor, cropped to 1000×562 to remove the black mosaic borders. Files: `src/PIA24765.jpg` and `src/PIA24765_crop.jpg`.
- `pia24765_mars_drive.mp4`: photoreal forward drive.
- `pia24765_europa_ice.mp4`: the same frame prompted as Europa ice.
- `europa_ref.jpg`: smoke test of the image command (a Europa reference still).

## Did the geometry hold?

It held only partly for the Mars drive, and not at all for Europa. I judged this by eye from frames at 0, 2, 4 and 6 s; I didn't compute any metrics. The Mars clip starts exactly on the photo, and the far field stays intact for all 6 s: the rocky ridge on the horizon, its individual boulders and the dune slope on the right keep their outlines and grow slightly as the camera moves forward. The near field doesn't hold. The camera also tilts up a little, so the horizon drops about 30 px. As the rover "drives," the real foreground rocks leave the frame and the model invents the newly revealed ground. That ground looks plausible but has no ground truth, so only the far field is anchored to the photo. The Europa clip doesn't restyle the scene; it replaces it. Ice slabs grow over the sand from the center by 0.25 s, and by 1 s the whole frame is new: generic cracked slabs and pyramid-shaped ice blocks that don't match the original rocks in position, size or count. The horizon drops from about y=15 to y=120 of 400 to make room for a new sky with a sun, and only a faint trace of the right-hand dune remains. Conclusion: Lite image-to-video is fine for a showcase "drive forward" clip (spec S1), but it can't do world transfer with labels kept. Europa, Titan and other restyles need the video edit endpoint the spec plans (§4.7). Another option, not yet tested, is to restyle the still with image edit first and then animate the restyled frame.

## Restyle experiment: image edit, then animate (agent `imagine-restyle`, 2026-10-17)

**Spend: $0.14 of the $0.25 approval** (2 image edits at $0.07 each, logged in `costs.jsonl`). No video was made.

- `POST /v1/images/edits` returned **HTTP 200** on both calls. The body is JSON: `model`, `prompt` and `image: {"url": <data URI>, "type": "image_url"}`. Following the docs, I left out `response_format`, and the response returned `data[0].url` rather than base64.
- **Deviation from "try once":** the first call succeeded, but my script got HTTP 403 downloading the result URL (probably the CDN rejecting Python's default User-Agent), and the URL was lost. I sent the identical body a second time, with a browser User-Agent and the response saved before the download. That fetch worked. The first call's $0.07 is assumed from the second call's reported 700000000 ticks.
- An edit costs **$0.07, not $0.04** like a generation. At $0.14 spent, a $0.13 Lite clip would bring the total to $0.27, over the approval, so I stopped before step 2. `pia24765_europa_from_edit.mp4` doesn't exist. Animating the still needs $0.02 more approval, or $0.13 from a fresh approval.
- Outputs: `data/imagine/pia24765_europa_edit.jpg` (1360×752 JPEG), its `.json` sidecar, and `.response.json` (URL removed). Script: `marsvq/imagine/restyle.py`; `--edit-only` skips the video.

**Did the rocks stay (still only, judged by eye against `src/PIA24765_crop.jpg`)?** Yes, closely. This is the opposite of the image-to-video Europa clip. The three horizon rock clusters (left, center and right) keep their positions and outlines. The horizon stays at the top edge, and the dune slope on the upper right is still there. The two-rock group in the left foreground, the dark pit near center, the bedrock patches at lower right, and most of the scattered small stones line up with the photo once you allow for the 1.36× scale. The camera and framing are unchanged. The edit swapped the sand for white ice and painted a network of red-brown cracks across the middle ground and foreground. The cracks are new detail with no ground truth, and some low sand ripples became smooth ice plates, but no rock was moved, added in an obvious way, or removed. So image edit is a workable first step for a restyle that keeps labels. Whether Lite video then holds the edited frame is still untested.

- **Lite video from the edit:** one 6 s call cost **$0.13**, which brings imagine-restyle spend to $0.27. Comparing frames at 0 s and 5 s by eye, the three horizon rock clusters held their places and outlines, but the foreground did not: most red cracks faded out and new ice ridges and small stones appeared, more than a slow forward move explains, so the rocks stayed only near the horizon.

## Batch edit: sol 104 Navcam frames to Europa ice (agent `batch`, 2026-10-17)

**4 of 6 edits succeeded. Spend: $0.28 of the $0.60 approval** (agent `batch` rows in `costs.jsonl`). No video was made.

- Script: `marsvq/imagine/batch_edit.py`. One `POST /v1/images/edits` call per frame, model `grok-imagine-image-2.0`, outputs in `data/pairs/<frame_stem>/edit.jpg` with `edit.json` and `edit.response.json` (URL removed) beside each.
- Prompt, the same for all frames: "Restyle this photo as photoreal Europa ice: turn the ground into water ice and frost. Keep every rock exactly in place, with the same size, shape and count. Keep the same horizon. Keep the same camera position, angle, framing and lens. Add no new objects."
- Stopped early: HTTP 402: {"code":"personal-team-blocked:spending-limit","error":"You have run out of credits or need a Grok subscription. Add credits at https://grok.com/?_s=usage or upgrade at https://grok.com/supergrok."}

- `NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0104_0676181093_823ECM_N0040510NCAM03104_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0104_0676181382_036ECM_N0040510NCAM03104_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0104_0676181486_802ECM_N0040510NCAM02104_01_295J01_1200`: billing/quota stop: HTTP 402: {"code":"personal-team-blocked:spending-limit","error":"You have run out of credits or need a Grok subscription. Add credits at https://grok.com/?_s=usage or upgrade at https://grok.com/supergrok."}
- `NLF_0104_0676181611_043ECM_N0040510NCAM02104_01_295J01_1200`: not attempted
