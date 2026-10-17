"""One-shot restyle experiment: image edit of PIA24765 into Europa ice, then animate the edited still.

    python3 -m marsvq.imagine.restyle

Runs as agent "imagine-restyle" with its own $0.25 budget. The edit is tried exactly once:
any non-429 HTTP error is final and the video step is skipped.
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import client

client.AGENT = "imagine-restyle"
client.BUDGET_USD = 0.25

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/imagine/src/PIA24765_crop.jpg"
EDIT_OUT = ROOT / "data/imagine/pia24765_europa_edit.jpg"
RESP_OUT = ROOT / "data/imagine/pia24765_europa_edit.response.json"
VIDEO_OUT = ROOT / "data/imagine/pia24765_europa_from_edit.mp4"

EDIT_PROMPT = (
    "Restyle this photo as the surface of Europa. Turn the sand and soil into fractured water ice: "
    "white and pale blue-grey ice plates split by thin reddish-brown cracks, with frost on every rock. "
    "Keep every rock and boulder exactly where it is, with the same size, shape and count. Keep the "
    "horizon line, the distant ridge and the dune slope exactly where they are. Keep the same camera "
    "position, angle, framing and lens. Change only materials and colors."
)
VIDEO_PROMPT = "slow forward camera move, keep the terrain and ice blocks exactly in place"


def edit_image() -> dict:
    client._check_budget(client.EST_IMAGE_USD)
    body = {"model": client.IMAGE_MODEL, "prompt": EDIT_PROMPT,
            "image": {"url": client.image_ref(str(SRC)), "type": "image_url"}}
    try:
        res = client._request("POST", f"{client.API}/images/edits", body)
    except client.ImagineError:
        client.log_cost(client.IMAGE_MODEL, 0.0, ok=False, count=1)
        raise
    # Keep the response (and its URL) before downloading, so a failed fetch doesn't lose the image.
    RESP_OUT.write_text(json.dumps(res, indent=1) + "\n")
    cost = client._cost(res) or client.EST_IMAGE_USD
    item = res["data"][0]
    try:
        data = base64.b64decode(item["b64_json"]) if item.get("b64_json") else _download(item["url"])
    except Exception as e:
        client.log_cost(client.IMAGE_MODEL, cost, ok=False, count=1)
        raise client.ImagineError(f"edit ok but download failed: {e}") from None
    out = EDIT_OUT.with_suffix(".png") if data[:8] == b"\x89PNG\r\n\x1a\n" else EDIT_OUT
    out.write_bytes(data)
    client.log_cost(client.IMAGE_MODEL, cost, ok=True, count=1)
    RESP_OUT.write_text(json.dumps(_strip_urls(res), indent=1) + "\n")
    meta = {"endpoint": "/v1/images/edits", "model": client.IMAGE_MODEL, "prompt": EDIT_PROMPT,
            "source": str(SRC.relative_to(ROOT)), "cost_usd": cost, "mime_type": item.get("mime_type"),
            "usage": res.get("usage")}
    meta["out"] = str(out)
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _download(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "image/*,*/*"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        # Only an xAI host may see the key; never send it to a third-party signed-URL host.
        host = urllib.parse.urlparse(url).hostname or ""
        if e.code != 403 or not (host == "x.ai" or host.endswith(".x.ai")):
            raise
    headers["Authorization"] = f"Bearer {client._key()}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
        return r.read()


def _strip_urls(res: dict) -> dict:
    res = dict(res)
    res["data"] = [{k: v for k, v in d.items() if k not in ("url", "b64_json")} for d in res.get("data", [])]
    return res


def main() -> int:
    try:
        meta = edit_image()
    except client.ImagineError as e:
        print(f"edit failed ({type(e).__name__}): {e}", file=sys.stderr)
        return 1
    print(f"edit saved {meta['out']}  cost ${meta['cost_usd']:.3f}")
    if "--edit-only" in sys.argv:
        return 0
    try:
        res = client.generate_video(VIDEO_PROMPT, VIDEO_OUT, image=meta["out"], seconds=6,
                                    on_status=lambda s, t: print(f"  {t:5.0f}s  {s}", file=sys.stderr))
    except client.ImagineError as e:
        print(f"video failed ({type(e).__name__}): {e}", file=sys.stderr)
        return 1
    print(f"video saved {VIDEO_OUT}  {res['elapsed_s']:.0f}s  cost ${res['cost_usd']:.3f}")
    print(f"imagine-restyle spend ${client.spent_usd():.2f} of ${client.BUDGET_USD:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
