# Ship log

**2026-10-17**

- **Public repo:** https://github.com/kaileh57/marsvq (visibility PUBLIC, default branch `main`)
- **Pushed commit:** `97542fa34c2b05c824ae9eddc1d93cc710f10ef2`, "Add NavCam path pairs and Imagine edits for the driving demo." `origin/main` points at this commit.
- **Contents:** 68 files, including `README.md`, `docs/demo.mp4` (the 37 s cut, 3.4 MB), `docs/devpost.md`, `marsvq/`, `configs/`, and `data/{imagine,pairs,sim}`. The largest file is `data/imagine/pia24765_mars_drive.mp4` at 7.3 MB.

## Left out on purpose

These paths are excluded by `.gitignore`:

- `data/raw/` (142 MB of NASA and USGS source data). This also leaves `data/raw/SOURCES.md` out of the public repo. The README credits both sources and their licenses, but the full provenance notes stay local.
- `marsvq/sim/.venv/` and any other virtualenv.
- All `*.response.json` files (5 of them: four `data/pairs/*/edit.response.json` and `data/imagine/pia24765_europa_edit.response.json`).
- `.env`, `.env.*`, `*.key`. The repo contains no `.env` or key file. The xAI key lives in `~/.config/xai/key`, outside the repo. A scan of the staged files for key patterns found nothing.

## Not pushed

- `docs/devpost.md`: the `Repo:` line now holds the URL in place of `REPO_TBD`. `DISCORD_TBD` and `VIDEO_TBD` are unchanged. Another agent also edited this file after the commit (it added an "Other tracks: none" line, removed code formatting, and reworded the "What it does" paragraph). Those edits are not mine, and they are not pushed either.
- `README.md`: changed by another agent after the commit. Not pushed.
- `docs/SHIP.md`: this file. Not pushed.

No TBDs in `docs/devpost.md` needed filling from the STATUS files. By the time `README.md` appeared, the devpost had been rewritten, and its only TBDs were the Discord, repo and video placeholders.

No force-push. Git config is unchanged.
