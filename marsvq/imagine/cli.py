"""marsvq-imagine: generate one image or one image-to-video clip with Grok Imagine.

    marsvq-imagine image --prompt "..." --out data/imagine/x.png
    marsvq-imagine video --prompt "..." --image <file-or-url> --seconds 6 --out data/imagine/x.mp4
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import client

STATUS = Path(__file__).resolve().parent / "STATUS.md"


def _record_stop(err: Exception) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with STATUS.open("a") as f:
        f.write(f"\n## Stopped: {type(err).__name__} ({ts})\n\n{err}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="marsvq-imagine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    img = sub.add_parser("image", help="text-to-image")
    img.add_argument("--prompt", required=True)
    img.add_argument("--out", required=True)

    vid = sub.add_parser("video", help="image-to-video (or text-to-video without --image)")
    vid.add_argument("--prompt", required=True)
    vid.add_argument("--image", help="start frame: local file or public URL")
    vid.add_argument("--seconds", type=int, default=client.MAX_SECONDS)
    vid.add_argument("--out", required=True)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "image":
            res = client.generate_image(args.prompt, args.out)
            print(f"saved {res['out']}  cost ${res['cost_usd']:.3f}")
        else:
            res = client.generate_video(
                args.prompt, args.out, image=args.image, seconds=args.seconds,
                on_status=lambda s, t: print(f"  {t:5.0f}s  {s}", file=sys.stderr),
            )
            print(f"saved {args.out}  request {res['request_id']}  "
                  f"{res['elapsed_s']:.0f}s  cost ${res['cost_usd']:.3f}")
        print(f"imagine session spend ${client.spent_usd():.2f} of ${client.BUDGET_USD:.2f}")
        return 0
    except (client.BillingError, client.BudgetError) as e:
        _record_stop(e)
        print(f"stopped: {e} (written to {STATUS})", file=sys.stderr)
        return 2
    except client.ImagineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
