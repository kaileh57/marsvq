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

## Batch edit: Navcam frames to Europa ice (agent `drive-batch`, 2026-10-17)

**7 new edits succeeded out of 9 frames. Agent spend: $0.49 of the $4.00 cap** (agent `drive-batch` rows in `costs.jsonl`). No video was made.

- Script: `marsvq/imagine/batch_edit.py`. One `POST /v1/images/edits` call per frame, model `grok-imagine-image-2.0`, outputs in `data/pairs/<frame_stem>/edit.jpg` with `edit.json` and `edit.response.json` (URL removed) beside each.
- Prompt, the same for all frames: "Restyle this photo as photoreal Europa ice: turn the ground into water ice and frost. Keep every rock exactly in place, with the same size, shape and count. Keep the same horizon. Keep the same camera position, angle, framing and lens. Add no new objects."

- `NLF_0102_0675997770_933ECM_N0040350NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0103_0676090594_606ECM_N0040408NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0105_0676265805_788ECM_N0040570NCAM00309_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0107_0676448037_177ECM_N0040638NCAM00309_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0108_0676529483_823ECM_N0040710NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0109_0676621552_135ECM_N0040810NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0110_0676710381_120ECM_N0040910NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)

## Batch edit: Navcam frames to Europa ice (agent `cto-real`, 2026-10-17)

**12 new edits succeeded out of 81 frames. Agent spend: $5.11 of the $8.00 cap** (agent `cto-real` rows in `costs.jsonl`). No video was made.

- Script: `marsvq/imagine/batch_edit.py`. One `POST /v1/images/edits` call per frame, model `grok-imagine-image-2.0`, outputs in `data/pairs/<frame_stem>/edit.jpg` with `edit.json` and `edit.response.json` (URL removed) beside each.
- Prompt, the same for all frames: "Restyle this photo as photoreal Europa ice: turn the ground into water ice and frost. Keep every rock exactly in place, with the same size, shape and count. Keep the same horizon. Keep the same camera position, angle, framing and lens. Add no new objects."

- `NLF_0015_0668277041_793ECM_N0030346NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0016_0668366769_902ECM_N0030548NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0016_0668370075_696ECM_N0030578NCAM03016_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0031_0669698138_570ECM_N0031008NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0033_0669876929_412ECM_N0031374NCAM03033_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0044_0670852110_105ECM_N0031416NCAM03044_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0047_0671117663_231ECM_N0031668NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0047_0671117849_758ECM_N0031698NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0048_0671206749_147ECM_N0031798NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0048_0671207014_883ECM_N0031840NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0049_0671299940_653ECM_N0031904NCAM00302_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0049_0671300154_616ECM_N0031940NCAM00302_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0052_0671561864_884ECM_N0032016NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672718637_237ECM_N0032046TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719237_277ECM_N0032117TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719266_543ECM_N0032122TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719449_820ECM_N0032127TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719482_507ECM_N0032128TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719550_660ECM_N0032138TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719603_371ECM_N0032144TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0065_0672719709_543ECM_N0032150TRAV12002_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672794632_678ECM_N0032156TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672794756_941ECM_N0032162TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672794825_632ECM_N0032168TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672794895_635ECM_N0032174TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672795025_036ECM_N0032180TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672795054_661ECM_N0032186TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672795206_387ECM_N0032191TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672795240_050ECM_N0032192TRAV12006_02_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0066_0672795381_631ECM_N0032198TRAV12002_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLF_0066_0672809614_074ECM_N0032208NCAM02066_01_295J01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673341693_319ECM_N0032274TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673341767_410ECM_N0032280TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673341922_789ECM_N0032285TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673341956_493ECM_N0032286TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342023_481ECM_N0032296TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342198_527ECM_N0032302TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342305_367ECM_N0032307TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342338_554ECM_N0032308TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342406_415ECM_N0032318TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342459_567ECM_N0032324TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342494_367ECM_N0032330TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342574_911ECM_N0032337TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLM_0072_0673342599_222ECM_N0032342TRAV12006_01_2LLJ01_1200`: skipped, edit.jpg already exists
- `NLF_0072_0673345418_523ECM_N0032346NCAM03072_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0086_0674582955_630ECM_N0040012NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0091_0675026909_363ECM_N0040112NCAM00308_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0091_0675031663_102ECM_N0040136NCAM03091_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0099_0675733205_786ECM_N0040182NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0099_0675737782_019ECM_N0040218NCAM03099_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0102_0675997770_933ECM_N0040350NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0102_0676000653_617ECM_N0040372NCAM03101_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0103_0676090594_606ECM_N0040408NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0103_0676094195_382ECM_N0040430NCAM03103_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0105_0676265805_788ECM_N0040570NCAM00309_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0105_0676269377_099ECM_N0040592NCAM03105_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0108_0676529483_823ECM_N0040710NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0108_0676532592_679ECM_N0040738NCAM03108_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0109_0676621552_135ECM_N0040810NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0109_0676625420_165ECM_N0040822NCAM03109_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0110_0676710381_120ECM_N0040910NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0110_0676713972_675ECM_N0040922NCAM03110_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0113_0676982365_975ECM_N0041062NCAM03113_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0123_0677868335_380ECM_N0041606NCAM00301_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0123_0677872318_058ECM_N0041644NCAM01123_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0130_0678490500_195ECM_N0050000NCAM03130_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0131_0678575451_757ECM_N0050500NCAM03131_01_295J01_1200`: skipped, edit.jpg already exists
- `NLF_0136_0679017140_612ECM_N0051532NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0137_0679102303_497ECM_N0051762NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0169_0681951459_785ECM_N0060410NCAM03169_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0170_0682034365_033ECM_N0060864NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0173_0682308672_489ECM_N0061648NCAM03173_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0201_0684789140_293ECM_N0071314NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0202_0684875553_303ECM_N0071534NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0204_0685057916_324ECM_N0071786NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0210_0685590357_659ECM_N0072038NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0237_0687986112_550ECM_N0072216NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0280_0691798140_632ECM_N0080186NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
- `NLF_0285_0692243906_145ECM_N0080706NCAM00301_01_295J01_1200`: ok, $0.07, 1152×864 (input 1200×900)
