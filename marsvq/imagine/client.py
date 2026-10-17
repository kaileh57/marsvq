"""Small stdlib-only client for Grok Imagine image and image-to-video generation.

The API key comes from $XAI_API_KEY or ~/.config/xai/key and is never printed or logged.
Every call appends one line to ~/Projects/xai-test/costs.jsonl.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.x.ai/v1"
IMAGE_MODEL = "grok-imagine-image-2.0"
VIDEO_MODEL = "grok-imagine-video-1.5-lite"  # premium video is deliberately not allowed
MAX_SECONDS = 6
COST_LOG = Path.home() / "Projects/xai-test/costs.jsonl"
AGENT = "imagine"
TICK_USD = 1e-10
# Conservative pre-call estimates, used only by the budget guard.
EST_IMAGE_USD = 0.04
EST_VIDEO_USD_PER_S = 0.025
BUDGET_USD = float(os.environ.get("MARSVQ_IMAGINE_BUDGET_USD", "1.50"))
POLL_S = 5
POLL_TIMEOUT_S = 15 * 60
BILLING_WORDS = ("billing", "quota", "limit", "credit", "spend", "insufficient", "payment", "overage")


class ImagineError(RuntimeError):
    pass


class BillingError(ImagineError):
    """Billing, quota or limit rejection. Callers must stop, not retry."""


class BudgetError(ImagineError):
    """The next call would exceed the session budget."""


def _key() -> str:
    key = os.environ.get("XAI_API_KEY")
    if not key:
        path = Path.home() / ".config/xai/key"
        if not path.exists():
            raise ImagineError("no API key: set $XAI_API_KEY or create ~/.config/xai/key")
        key = path.read_text().strip()
    return key


def _scrub(text: str) -> str:
    key = os.environ.get("XAI_API_KEY") or ""
    path = Path.home() / ".config/xai/key"
    if not key and path.exists():
        key = path.read_text().strip()
    return text.replace(key, "<redacted>") if key else text


def log_cost(model: str, cost_usd: float, ok: bool, seconds: int | None = None, count: int | None = None) -> None:
    rec = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "agent": AGENT, "model": model}
    if seconds is not None:
        rec["seconds"] = seconds
    if count is not None:
        rec["count"] = count
    rec.update(cost_usd=round(cost_usd, 4), ok=ok)
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")


def spent_usd() -> float:
    """Sum of logged costs for this agent."""
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text().splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("agent") == AGENT:
            total += float(rec.get("cost_usd") or 0)
    return total


def _check_budget(estimate: float) -> None:
    spent = spent_usd()
    if spent + estimate > BUDGET_USD:
        raise BudgetError(f"budget cap: spent ${spent:.2f} + est ${estimate:.2f} > ${BUDGET_USD:.2f}")


def _cost(res: dict) -> float:
    ticks = (res.get("usage") or {}).get("cost_in_usd_ticks")
    return ticks * TICK_USD if ticks is not None else 0.0


def _request(method: str, url: str, body: dict | None = None, retried: bool = False) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = _scrub(e.read().decode(errors="replace")[:500])
        if e.code == 429 and not retried and not any(w in detail.lower() for w in ("quota", "billing", "credit")):
            time.sleep(30)
            return _request(method, url, body, retried=True)
        msg = f"HTTP {e.code}: {detail}"
        if e.code in (402, 429) or any(w in detail.lower() for w in BILLING_WORDS):
            raise BillingError(msg) from None
        raise ImagineError(msg) from None
    except urllib.error.URLError as e:
        raise ImagineError(f"network error: {e.reason}") from None


def image_ref(src: str) -> str:
    """A public URL passes through; a local file becomes a data URI."""
    if src.startswith(("http://", "https://", "data:")):
        return src
    path = Path(src)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def generate_image(prompt: str, out: str | Path, model: str = IMAGE_MODEL) -> dict:
    if model != IMAGE_MODEL:
        raise ImagineError(f"model not allowed: {model}")
    _check_budget(EST_IMAGE_USD)
    try:
        res = _request("POST", f"{API}/images/generations",
                       {"model": model, "prompt": prompt, "n": 1, "response_format": "b64_json"})
    except ImagineError:
        log_cost(model, 0.0, ok=False, count=1)
        raise
    item = res["data"][0]
    out = Path(out)
    # The API returns JPEG even when asked for an image; keep the real extension.
    if item.get("mime_type") == "image/jpeg" and out.suffix.lower() == ".png":
        out = out.with_suffix(".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(item["b64_json"]))
    cost = _cost(res) or EST_IMAGE_USD
    log_cost(model, cost, ok=True, count=1)
    return {"out": str(out), "cost_usd": cost, "mime_type": item.get("mime_type")}


def generate_video(prompt: str, out: str | Path, image: str | None = None, seconds: int = MAX_SECONDS,
                   model: str = VIDEO_MODEL, on_status=None) -> dict:
    if model != VIDEO_MODEL:
        raise ImagineError(f"model not allowed: {model}")
    if not 1 <= seconds <= MAX_SECONDS:
        raise ImagineError(f"seconds must be 1..{MAX_SECONDS}")
    _check_budget(EST_VIDEO_USD_PER_S * seconds)
    body = {"model": model, "prompt": prompt, "duration": seconds}
    if image:
        body["image"] = {"url": image_ref(image)}
    try:
        rid = _request("POST", f"{API}/videos/generations", body)["request_id"]
    except ImagineError:
        log_cost(model, 0.0, ok=False, seconds=seconds)
        raise

    t0 = time.time()
    while True:
        try:
            res = _request("GET", f"{API}/videos/{rid}")
        except ImagineError:
            log_cost(model, 0.0, ok=False, seconds=seconds)
            raise
        status = res.get("status")
        if on_status:
            on_status(status, time.time() - t0)
        if status == "done":
            break
        if status in ("failed", "expired"):
            log_cost(model, _cost(res), ok=False, seconds=seconds)
            raise ImagineError(f"video {status}: {_scrub(json.dumps(_strip(res))[:500])}")
        if time.time() - t0 > POLL_TIMEOUT_S:
            log_cost(model, 0.0, ok=False, seconds=seconds)
            raise ImagineError(f"poll timeout after {POLL_TIMEOUT_S}s (request {rid})")
        time.sleep(POLL_S)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cost = _cost(res)
    try:
        urllib.request.urlretrieve(res["video"]["url"], out)
    except Exception as e:
        log_cost(model, cost, ok=False, seconds=seconds)
        raise ImagineError(f"download failed: {e}") from None
    log_cost(model, cost, ok=True, seconds=seconds)
    meta = {"request_id": rid, "model": model, "prompt": prompt, "seconds": seconds,
            "image": image if image and not image.startswith("data:") else None,
            "elapsed_s": round(time.time() - t0, 1), "cost_usd": cost, "response": _strip(res)}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _strip(res: dict) -> dict:
    """Response without the signed video URL."""
    res = dict(res)
    if isinstance(res.get("video"), dict):
        res["video"] = {k: v for k, v in res["video"].items() if k != "url"}
    return res
