"""Batch image edit: each sol 104 Navcam frame restyled as Europa ice.

    python3 -m marsvq.imagine.batch_edit

Runs as agent "batch" with a $0.60 budget. One /v1/images/edits call per frame, same prompt for
all. A frame whose edit.jpg already exists is skipped, so a rerun never spends twice. A failed
download is never re-sent: the response (with its URL) stays in edit.response.json for a free refetch.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import client, restyle

# restyle.py sets these at import time, so they must be set after importing it.
client.AGENT = "batch"
client.BUDGET_USD = 0.60
EST_EDIT_USD = 0.07

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "data/raw/real/m2020_sol0104_ncam"
PAIRS = ROOT / "data/pairs"
STATUS = Path(__file__).with_name("STATUS.md")

PROMPT = (
    "Restyle this photo as photoreal Europa ice: turn the ground into water ice and frost. "
    "Keep every rock exactly in place, with the same size, shape and count. Keep the same horizon. "
    "Keep the same camera position, angle, framing and lens. Add no new objects."
)


def edit_one(src: Path) -> dict:
    out_dir = PAIRS / src.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "edit.jpg"
    resp_path = out_dir / "edit.response.json"
    client._check_budget(EST_EDIT_USD)
    body = {"model": client.IMAGE_MODEL, "prompt": PROMPT,
            "image": {"url": client.image_ref(str(src)), "type": "image_url"}}
    try:
        res = client._request("POST", f"{client.API}/images/edits", body)
    except client.ImagineError:
        client.log_cost(client.IMAGE_MODEL, 0.0, ok=False, count=1)
        raise
    resp_path.write_text(json.dumps(res, indent=1) + "\n")
    cost = client._cost(res) or EST_EDIT_USD
    item = res["data"][0]
    try:
        data = base64.b64decode(item["b64_json"]) if item.get("b64_json") else restyle._download(item["url"])
    except Exception as e:
        client.log_cost(client.IMAGE_MODEL, cost, ok=False, count=1)
        raise client.ImagineError(f"edit ok (${cost:.2f}) but download failed: {e}; URL kept in {resp_path.name}") from None
    note = None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        png = out.with_suffix(".png")
        png.write_bytes(data)
        subprocess.run(["sips", "-s", "format", "jpeg", str(png), "--out", str(out)], check=True, capture_output=True)
        note = "returned PNG, converted to JPEG with sips"
    else:
        out.write_bytes(data)
    client.log_cost(client.IMAGE_MODEL, cost, ok=True, count=1)
    resp_path.write_text(json.dumps(restyle._strip_urls(res), indent=1) + "\n")
    meta = {"endpoint": "/v1/images/edits", "model": client.IMAGE_MODEL, "prompt": PROMPT,
            "source": str(src.relative_to(ROOT)), "out": str(out.relative_to(ROOT)), "cost_usd": cost,
            "mime_type": item.get("mime_type"), "usage": res.get("usage"), "note": note}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _dims(path: Path) -> str:
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)], capture_output=True, text=True)
    vals = [line.split()[-1] for line in r.stdout.splitlines()[1:]]
    return "×".join(vals) if len(vals) == 2 else "?"


def main() -> int:
    frames = sorted(SRC_DIR.glob("*.jpg"))
    rows, stopped = [], None
    try:
        for src in frames:
            out = PAIRS / src.stem / "edit.jpg"
            if out.exists():
                rows.append((src.stem, "skipped, edit.jpg already exists", None))
                continue
            try:
                meta = edit_one(src)
            except client.BillingError as e:
                rows.append((src.stem, f"billing/quota stop: {e}", None))
                stopped = str(e)
                break
            except client.BudgetError as e:
                rows.append((src.stem, f"budget stop: {e}", None))
                stopped = str(e)
                break
            except client.ImagineError as e:
                rows.append((src.stem, f"failed: {e}", None))
                print(f"{src.stem}: failed: {e}", file=sys.stderr)
                continue
            rows.append((src.stem, "ok", meta))
            print(f"{src.stem}: ok  ${meta['cost_usd']:.3f}  {_dims(out)}")
    finally:
        _write_status(frames, rows, stopped)
    return 0 if not stopped else 1


def _write_status(frames: list[Path], rows: list, stopped: str | None) -> None:
    ok = sum(1 for _, s, _ in rows if s == "ok")
    spent = client.spent_usd()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "", f"## Batch edit: sol 104 Navcam frames to Europa ice (agent `batch`, {day})", "",
        f"**{ok} of {len(frames)} edits succeeded. Spend: ${spent:.2f} of the $0.60 approval** "
        "(agent `batch` rows in `costs.jsonl`). No video was made.", "",
        f"- Script: `marsvq/imagine/batch_edit.py`. One `POST /v1/images/edits` call per frame, model "
        f"`{client.IMAGE_MODEL}`, outputs in `data/pairs/<frame_stem>/edit.jpg` with `edit.json` and "
        "`edit.response.json` (URL removed) beside each.",
        f"- Prompt, the same for all frames: \"{PROMPT}\"",
    ]
    if stopped:
        lines.append(f"- Stopped early: {stopped}")
    lines.append("")
    for stem, status, meta in rows:
        if meta:
            extra = f", {meta['note']}" if meta.get("note") else ""
            lines.append(f"- `{stem}`: ok, ${meta['cost_usd']:.2f}, {_dims(ROOT / meta['out'])} (input 1200×900){extra}")
        else:
            lines.append(f"- `{stem}`: {status}")
    for src in frames[len(rows):]:
        lines.append(f"- `{src.stem}`: not attempted")
    with STATUS.open("a") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
