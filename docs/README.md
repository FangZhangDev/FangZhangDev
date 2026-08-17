# AI Coding Contribution Profile — project docs

This repository doubles as a GitHub profile repository, so the root [`README.md`](../README.md)
is deliberately kept to visuals only: it is rendered as the profile landing page. All project
documentation lives here instead.

## What it does

Turns local Claude Code and Codex activity into a long-lived, public-safe profile:

- normalized daily usage records suitable for a public Git repository;
- SVG cards in light and dark variants: the README carries a prompt calendar and a terminal
  summary (which absorbs the old tool-split and model-ranking cards); each tool gets its own
  heatmap and model card under a `<details>` toggle;
- an incremental SQLite cache so recurring updates do not reparse unchanged files;
- an offline HTML report with a theme toggle and per-tool filter buttons.

The collector reads local logs but never publishes prompts, source paths, credentials, raw
transcripts, or repository names. Only aggregated usage facts reach `data/daily.jsonl` and
`dist/`.

## Quick start

Requires Python 3.11 or newer (for `tomllib`). No third-party packages.

```bash
cd /path/to/ai-coding-profile
cp config.example.toml config.toml   # then edit the paths
python3 profile.py update --config config.toml
python3 profile.py validate --config config.toml
```

The example config uses the paths discovered on the development machine; use absolute paths on
a scheduled runner.

## Configuration

```toml
[profile]
title = "Your Name"          # used in the terminal card title bar
subtitle = "…"               # shown in the local HTML report
timezone = "Asia/Shanghai"   # buckets events into local days and hours
window_days = 365            # heatmap window
repo = "you/you"             # builds raw.githubusercontent URLs for the README
branch = "main"

[paths]
claude_glob  = "~/.claude/projects/**/*.jsonl"
codex_homes  = ["~/.codex", "~/.local/state/agent-config/codex/*"]
claude_stats_cache = "~/.claude/stats-cache.json"   # backfill, see below
claude_history     = "~/.claude/history.jsonl"      # prompt calendar
cache_db     = "data/profile.sqlite"   # local only, git-ignored
daily_ledger = "data/daily.jsonl"      # public
output_dir   = "dist"                  # public
readme       = "README.md"             # gallery block gets rewritten in place
```

Leave `repo` empty to emit repository-relative image paths instead of absolute raw URLs.

## Generated files

| Path | Visibility | Contents |
| --- | --- | --- |
| `data/daily.jsonl` | public | append-only daily ledger |
| `data/profile.sqlite` | local | incremental parse cache, git-ignored |
| `dist/*-dark.svg`, `dist/*-light.svg` | public | every card, both themes |
| `dist/profile.svg` | public | alias for the dark heatmap, kept for old embeds |
| `dist/profile.html` | local | offline report with a theme toggle, git-ignored |
| `dist/profile.json` | public | machine-readable daily rows plus summary |

## How the README stays current

`profile.py update` rewrites only the block between these two markers in the root README:

```html
<!-- profile:gallery:begin -->
<!-- profile:gallery:end -->
```

Everything outside the markers is hand-written and never touched. Each image URL carries a
`?v=<sha256 prefix>` cache key derived from the SVG contents, so GitHub's image proxy picks up
a new card the moment it actually changes — and not before.

Card layout is declared in `GALLERY_ROWS` in `profile.py`; cards on the same row render side by
side. Drop a card by removing its name, reorder rows freely. Half-width cards are exactly
`CARD_WIDTH / 2`, and the generator emits them with no whitespace between the `<picture>` tags —
a newline there renders as a word space and pushes the pair past the full-width cards, which is
exactly the misalignment it is there to prevent.

Per-tool views are `<details>` blocks. A README cannot run JavaScript and an SVG served through
camo does not respond to clicks, so real filter buttons are impossible on GitHub; the disclosure
widget is the only native interaction available. `dist/profile.html` does have real buttons.

Links in the root README are written out in full rather than as `./docs/README.md`. A profile
README renders at `github.com/<user>`, so a relative link resolves against the user page instead
of the repository and lands on a 404. Inside `docs/` relative links are fine.

## Rendering notes

`render.py` holds the whole visual system. Constraints worth knowing before editing it:

- GitHub proxies SVGs through camo and renders them as images: **no JavaScript, no external
  fonts, no `<title>` tooltips.** Everything must be drawn, and fonts come from a system stack.
- CSS animations *do* play. Every animated element is authored so that its untouched state is
  the final state, so a renderer that ignores animation still shows a correct card.
- Light and dark are two separate files chosen by `<picture>` + `prefers-color-scheme`, which is
  more reliable across browsers than a media query inside a single SVG.
- Both palettes live in the `DARK` and `LIGHT` `Theme` instances at the top of `render.py`.
  Change colors there and every card follows.
- Card chrome, type scale, cell geometry (`CELL` / `GAP` / `RADIUS`), the month scale and the
  `Less □□□□□ More` legend all mirror GitHub's contribution box, so the cards sit on a profile
  without looking imported. The ramps deliberately do **not** use GitHub's green: these grids
  count tokens and prompts, and borrowing the commit colors would invite reading them as commits.
  Ramps live in the `RAMPS` table keyed by hue, not on the `Theme`: mauve is the
  primary metric (the combined prompt calendar and the all-tools heatmap), and each tool
  gets its own hue from `TOOL_RAMPS` (claude-code teal, codex pink) shared by its heatmap,
  and the bars in the terminal card - one hue per thing being measured.

## Long-term publishing

Run the updater daily from a private machine or a scheduled CI job. Publish only the ledger,
the `dist/` cards, the READMEs, and workflow files. Never put `~/.claude`, `~/.codex`, API keys,
or raw session files in the public repository.

```bash
scripts/publish_profile.sh
```

which is equivalent to:

```bash
python3 profile.py update --config config.toml
git add data/daily.jsonl dist README.md
git commit -m "chore: update coding activity profile"
git push
```

## Retention and backfill

Claude Code deletes local session transcripts after `cleanupPeriodDays` (default 30). A collector
that reads only transcripts therefore watches its own history evaporate — early activity vanishes
a month after it happened. Two files survive that cleanup and are read as a fallback:

| Source | Coverage | Carries tokens |
| --- | --- | --- |
| session transcripts | last `cleanupPeriodDays` days | yes, split into input / output / cache |
| `stats-cache.json` → `dailyModelTokens` | since the feature shipped | yes, per model, no split |
| `stats-cache.json` → `dailyActivity` | since `firstSessionDate` | no, sessions and messages only |
| `stats-cache.json` → `modelUsage` | all time | yes, but **undated** |
| `history.jsonl` (one per tool) | longest of all | no, prompt timestamps only |

Merge rules, in `merge_backfill`:

- Transcripts always win. A day is backfilled only where transcripts carry no `claude-code`
  contribution — tested per source, not per day, because early days often hold Codex records that
  would otherwise mask a missing Claude contribution.
- Backfilled rows get `"estimated": true`. They have a real `total_tokens` but zeroed
  `input_tokens` / `output_tokens` / `cache_*`, since the aggregate cache does not break tokens down.
- `modelUsage` has no date axis, so it never enters the heatmap. It is recorded in the summary as
  `claude_lifetime_tokens` for reference only; every card uses the dated figures so the numbers on
  the cards always reconcile with the ledger.
- `history.jsonl` supplies only per-day prompt counts for the calendar card. Prompt text and
  project paths are never read into memory beyond the line being parsed, and never written out.
- Every tool keeps its **own** prompt history, and they must all be listed under
  `prompt_histories` — Claude Code has one, Codex has one per home. Miss a file and the calendar
  quietly undercounts with nothing on the card to reveal it. The two formats differ: Claude writes
  `timestamp` in milliseconds as an integer, Codex writes `ts` in seconds as a string.
- The calendar counts **prompts you sent, not model responses**, and prompt history carries no
  model field — so the figure spans every model, and cannot be broken down by one. It can be
  broken down by tool, which is what the per-tool `<details>` blocks show.

### Codex

Codex needs no equivalent fallback. It ships no cleanup setting, and every `rollout_path` recorded
in `state_5.sqlite` still resolves to a file on disk across all configured homes — nothing has been
pruned. Its earliest session is therefore a real start date, not a truncation artifact. Note that
`logs_2.sqlite` *does* roll over after a few days, but that is application logging, not usage data,
and nothing reads it.

Because Codex has no aggregate cache to fall back on, `data/daily.jsonl` is its only long-term
archive. That is why `write_ledger` merges rather than overwrites: a day already recorded survives
even if its source file later disappears.

### Stopping the loss

Raise the retention period to stop losing data going forward:

```json
// ~/.claude/settings.json
{ "cleanupPeriodDays": 3650 }
```

## Data model

Each row in `data/daily.jsonl`:

| Field | Meaning |
| --- | --- |
| `date` | local calendar day |
| `sources` | tokens per tool (`claude-code`, `codex`) |
| `models` | tokens per model id |
| `sessions` | distinct session count |
| `turns` | assistant responses recorded |
| `input_tokens` / `output_tokens` | reported usage units |
| `cache_read_tokens` / `cache_write_tokens` | prompt-cache traffic, kept separate |
| `total_tokens` | sum of the four token fields |
| `estimated` | present and `true` when part of the day came from the aggregate cache rather than a transcript, meaning `total_tokens` is real but the four component fields are not |

Token fields are reported usage units, not a bill. Cached input is tracked separately so the
public cards can quote a less misleading activity metric.

The summary in `dist/profile.json` adds `hours` (24 buckets) and `weekdays` (7 buckets),
counting turns only. Neither reveals anything beyond when the keyboard was busy.
