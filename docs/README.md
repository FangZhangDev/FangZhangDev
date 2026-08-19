# AI Coding Contribution Profile — project docs

This repository doubles as a GitHub profile repository, so the root [`README.md`](../README.md)
is deliberately kept to visuals only: it is rendered as the profile landing page. All project
documentation lives here instead.

## What it does

Turns local Claude Code, Codex and dsh (DeepSeek Harness) activity into a long-lived,
public-safe profile:

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
repo = "you/you"             # builds the README image URLs
branch = "main"
asset_cdn = "jsdelivr"       # "jsdelivr" (proxied by camo, 8-day cache) or "raw" (direct, 5-min cache)

[paths]
claude_glob  = "~/.claude/projects/**/*.jsonl"
codex_homes  = ["~/.codex", "~/.local/state/agent-config/codex/*"]
dsh_glob     = "~/.dsh/sessions/**/session.jsonl.zstd"   # DeepSeek Harness 会话
claude_stats_cache = "~/.claude/stats-cache.json"   # backfill, see below
claude_history     = "~/.claude/history.jsonl"      # prompt calendar
cache_db      = "data/profile.sqlite"  # local only, git-ignored
daily_ledger  = "data/daily.jsonl"     # public, append-only
prompt_ledger = "data/prompts.jsonl"   # public, append-only
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
# with asset_cdn = "jsdelivr", also purge the CDN — see below
curl -X POST https://purge.jsdelivr.net/ -H 'Content-Type: application/json' \
     -d '{"path":["/gh/you/you@main/dist/terminal-dark.svg", "…"]}'
```

### Why the cards are served through jsDelivr

GitHub only proxies images hosted on third-party domains. `raw.githubusercontent.com` is one of
its own, so a README pointing there is left untouched and the reader's browser connects to raw
directly — with `cache-control: max-age=300`. Five minutes later the cache is cold and every
visit has to reach that host again. On a network where githubusercontent is unreliable, the
cards then show up as alt text on exactly those reloads that land after the cache expires.

Pointing at `cdn.jsdelivr.net` instead makes the URL third-party, so GitHub rewrites it to
`camo.githubusercontent.com`, which serves `cache-control: max-age=691200` — eight days. The
image still travels the same kind of network, but the browser has to fetch it roughly three
orders of magnitude less often, so there are far fewer chances to fail.

The cost is staleness. jsDelivr caches a `@branch` path at the edge for 12 hours **and ignores
the query string**, so the `?v=<digest>` cache-buster that works on camo does nothing here — after
a push, `cdn.jsdelivr.net/…@main/dist/terminal-dark.svg?v=<new>` still returns the previous file.
`scripts/publish_profile.sh` therefore calls the purge API for every jsDelivr path it finds in
the README right after pushing. Purging the same path twice in quick succession can come back
`"throttled": true`, in which case that one file keeps serving the old copy until the 12 hours
elapse; re-running the purge for it a little later clears it.

Set `asset_cdn = "raw"` to go back to direct raw URLs — images are then always current, at the
cost of the 5-minute cache and the reliability that comes with it. The publish script's purge
step finds no jsDelivr URLs in the README and skips itself.

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

### The two ledgers

Every source above belongs to some other tool, and every one of them is pruned on somebody
else's schedule. So neither ledger is ever rewritten from scratch — a day that has been recorded
stays recorded:

| Ledger | Written by | Guarantee |
| --- | --- | --- |
| `data/daily.jsonl` | `write_ledger` | a day is overwritten only when that day has new data |
| `data/prompts.jsonl` | `merge_prompt_ledger` | per day **and per tool**, keeps `max(archived, live)` |

`prompts.jsonl` matters because the prompt calendar has no other archive: `read_prompt_calendar`
re-reads each tool's `history.jsonl` on every run, and before this ledger existed the result only
ever landed in `dist/profile.json`, which the code never reads back. A trimmed history file, or a
move to a new machine, would silently shorten the calendar — and show up in git as a deletion.
The per-tool `max` handles the case where a history file is a ring buffer and a later read returns
only its tail.

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

### dsh

dsh (DeepSeek Harness) stores each session as a zstd-compressed JSONL event stream at
`~/.dsh/sessions/<project>/<session-id>/session.jsonl.zstd`. The collector decompresses it with
the `zstandard` module when installed and falls back to the `zstd` binary otherwise, so the
project still needs no third-party packages.

One session file carries everything the profile needs, so it is listed both as a token source
(`dsh_glob`) and as a prompt-history source (`prompt_histories` with `source = "dsh"`):

- `assistant/message` events carry per-step `usage` (input / output / cache-read tokens) plus the
  model and provider, one row per step — the same shape as a Claude transcript row;
  `reasoningTokens` is folded into the output count;
- `user/message` events with `source.kind = "user"` are the prompts you sent. Plugin-injected
  context snapshots are `kind = "plugin"` and are not counted. dsh has no separate
  `history.jsonl`, so the session files are the only prompt archive;
- the session id comes from the leading `session` event, with the directory name as fallback.

dsh has no cleanup setting today, but its files are written live: a session being recorded right
now has an incomplete trailing frame. `zstd -dc` still returns the complete prefix, which is
accepted; a file that cannot be decompressed at all is skipped and re-parsed on the next run,
when its mtime has changed. Prompts are likewise safe to lose on a truncated read because
`merge_prompt_ledger` keeps `max(archived, live)` per day and per tool.

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
| `sources` | tokens per tool (`claude-code`, `codex`, `dsh`) |
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
