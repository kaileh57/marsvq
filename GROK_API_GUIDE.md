# xAI / Grok Imagine API: instructions for the agent swarm

You (Grok, in Cursor) are leading a team of Claude Code subagents. Give every subagent the **Rules** section, plus whichever API section it needs. Everything marked *tested* was confirmed by real calls on 2026-10-16. Anything else comes from the docs and hasn't been tried yet.

## Rules (every agent)

1. **The key is a secret.** Read it from `$XAI_API_KEY`, falling back to the file `~/.config/xai/key`. Never print it, log it, paste it into code, commit it, or send it to a subagent as text. Pass along the file path instead.
2. **Budget is shared and small.** All usage comes out of one Premium weekly pool: about $40–46 a week, with about $37 left until it resets on Oct 20. The pool is also shared with Cursor and Grok Bot, so your own token usage draws from it too.
3. **Additional usage is capped at $0.** When the pool runs out, or the API decides a call is overflow, the call is **rejected**, not billed. Treat a billing or quota error as "stop and report to the lead". Don't retry in a loop.
4. **Log the cost of every call.** Every video response includes `usage.cost_in_usd_ticks`. 1 tick is $0.0000000001, so `1300000000` means $0.13. Append one line per call to `~/Projects/xai-test/costs.jsonl` with the agent name, model, seconds or count, and cost in USD.
5. **Ask the lead before spending.** No single agent spends more than $2 without approval. Prefer cheap settings: Lite video, short durations, one image at a time.
6. **Hackathon rule:** until DubHacks hacking officially starts, use the API only for experiments and learning: prompts, styles, timing, cost. Don't build the project yet.

## Models and prices

| Use | Model | Price | Notes |
|---|---|---|---|
| Images | `grok-imagine-image-2.0` | $0.04 / image | *Tested.* Up to 10 per request, 1K/2K |
| Video (default) | `grok-imagine-video-1.5-lite` | from $0.02 / sec | *Tested:* 6s = $0.13, 15s = $0.31 (with image input). Up to 15s |
| Video (premium) | `grok-imagine-video-1.5` | from $0.08 / sec | 4x the cost. Use only with the lead's OK |
| Text / code | `grok-4.7` | $2 / 1M in, $6 / 1M out | Not tested via API |

Rough capacity of the remaining pool (about $37): about 110 Lite clips of 15 seconds, or about 280 clips of 6 seconds, or about 900 images.

## Image generation (*tested*)

```bash
curl -sS https://api.x.ai/v1/images/generations \
  -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"grok-imagine-image-2.0","prompt":"...","n":1,"response_format":"b64_json"}'
```

The response holds `data[0].b64_json`, a base64 PNG. Decode it and save the image. Each call takes a few seconds.

## Video generation (*tested*, asynchronous)

1. Start the job:
   ```
   POST https://api.x.ai/v1/videos/generations
   {"model": "grok-imagine-video-1.5-lite",
    "prompt": "what should happen",
    "image": {"url": "data:image/png;base64,<...>"},   // optional start frame; a public URL also works
    "duration": 6}                                      // seconds, max 15
   ```
   The response is `{"request_id": "..."}`.
2. Poll `GET https://api.x.ai/v1/videos/{request_id}` every 5 seconds until `status` is `"done"`. Stop if it's `"failed"` or `"expired"`.
3. When it's done, read `video.url` for the MP4 and download it right away, since the URL may expire. Record `usage.cost_in_usd_ticks`.

Jobs took 17–44 seconds. Two jobs at the same time worked fine. Text-only video (no `image`) and resolution options are in the docs but haven't been tested, so try one cheap call before relying on them.

Working reference code: `~/Projects/xai-test/test_video.py`, which takes `python3 test_video.py <model> <seconds>`, and `~/Projects/xai-test/test_imagine.sh`.

## Errors

| What you see | What to do |
|---|---|
| HTTP 401/403 | The key is missing or wrong. Check the file path; never ask for the key value |
| A billing, quota or limit error | The pool is empty or the call was flagged as overflow. Stop and tell the lead |
| HTTP 429 | Wait 30 seconds and retry once, then report |
| `failed` or `expired` status | Usually the prompt was rejected by content policy. Reword it once, then report |

## Checking the budget (lead only)

Usage page: https://grok.com/dashboard/usage. The weekly bar shows a rounded percentage, but the exact value is in the bar's `width` style, for example `width: 14.4745%`. One percentage point is about $0.40–0.46 of API usage. The events table shows each call as **Included** (free) or **Additional usage** (charged). If anything shows up as Additional, tell Kellen.
