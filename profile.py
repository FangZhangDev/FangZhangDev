#!/usr/bin/env python3
"""Build a public-safe long-term profile from Claude Code and Codex logs."""

from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    parsed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    source TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    turns INTEGER NOT NULL DEFAULT 1,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS events_timestamp_idx ON events(timestamp);
"""


@dataclass(frozen=True)
class Config:
    title: str
    subtitle: str
    timezone_name: str
    window_days: int
    claude_glob: str
    codex_homes: tuple[str, ...]
    cache_db: Path
    daily_ledger: Path
    output_dir: Path


def load_config(path: Path) -> Config:
    try:
        import tomllib
    except ModuleNotFoundError as exc:
        raise RuntimeError("Python 3.11 or newer is required") from exc
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    profile = raw.get("profile", {})
    paths = raw.get("paths", {})
    return Config(
        title=str(profile.get("title", "AI Coding Contribution Profile")),
        subtitle=str(profile.get("subtitle", "Claude Code + Codex")),
        timezone_name=str(profile.get("timezone", "UTC")),
        window_days=int(profile.get("window_days", 365)),
        claude_glob=str(paths.get("claude_glob", "")),
        codex_homes=tuple(str(item) for item in paths.get("codex_homes", [])),
        cache_db=Path(paths.get("cache_db", "data/profile.sqlite")),
        daily_ledger=Path(paths.get("daily_ledger", "data/daily.jsonl")),
        output_dir=Path(paths.get("output_dir", "dist")),
    )


def number(value: Any) -> int:
    """Return a safe integer for usage values, including nested cache objects."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, dict):
        return sum(number(item) for item in value.values())
    return 0


def parse_timestamp(value: Any, timezone_name: str) -> str:
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(timezone_name)).isoformat(timespec="seconds")


def expand_paths(patterns: Iterable[str]) -> list[Path]:
    paths: set[Path] = set()
    for pattern in patterns:
        for item in glob.glob(os.path.expanduser(pattern), recursive=True):
            path = Path(item)
            if path.is_file():
                paths.add(path.resolve())
    return sorted(paths)


def expand_directories(patterns: Iterable[str]) -> list[Path]:
    paths: set[Path] = set()
    for pattern in patterns:
        for item in glob.glob(os.path.expanduser(pattern), recursive=True):
            path = Path(item)
            if path.is_dir():
                paths.add(path.resolve())
    return sorted(paths)


def codex_state_models(home: Path) -> dict[str, tuple[str, str, str]]:
    """Load model metadata without reading Codex prompts or credentials."""
    db = home / "state_5.sqlite"
    if not db.exists():
        return {}
    result: dict[str, tuple[str, str, str]] = {}
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "threads" not in tables:
            return result
        for rollout_path, provider, model, session_id in connection.execute(
            "SELECT rollout_path, model_provider, model, id FROM threads"
        ):
            if not rollout_path:
                continue
            path = Path(rollout_path)
            if not path.is_absolute():
                path = home / path
            result[str(path.resolve())] = (
                str(provider or home.name), str(model or "unknown"), str(session_id or "")
            )
    except sqlite3.Error:
        return result
    finally:
        if connection is not None:
            connection.close()
    return result


def parse_claude(path: Path, timezone_name: str) -> list[tuple[Any, ...]]:
    events: list[tuple[Any, ...]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("type") != "assistant":
                continue
            message = row.get("message") or {}
            usage = message.get("usage") or {}
            if not isinstance(usage, dict):
                continue
            timestamp = parse_timestamp(row.get("timestamp"), timezone_name)
            if not timestamp:
                continue
            input_tokens = number(usage.get("input_tokens"))
            output_tokens = number(usage.get("output_tokens"))
            cache_read = number(usage.get("cache_read_input_tokens"))
            cache_write = number(usage.get("cache_creation_input_tokens"))
            total = input_tokens + output_tokens + cache_read + cache_write
            if total == 0:
                continue
            events.append((
                str(path), "claude-code", "claude-code", str(message.get("model") or "unknown"),
                timestamp, str(row.get("sessionId") or ""), 1,
                input_tokens, output_tokens, cache_read, cache_write, total,
            ))
    return events


def parse_codex(path: Path, timezone_name: str, metadata: tuple[str, str, str]) -> list[tuple[Any, ...]]:
    provider, model, session_id = metadata
    events: list[tuple[Any, ...]] = []
    previous = {"input": 0, "output": 0, "cache_read": 0, "total": 0}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = row.get("payload") or {}
            if payload.get("type") != "token_count":
                continue
            cumulative = (payload.get("info") or {}).get("total_token_usage") or {}
            if not isinstance(cumulative, dict):
                continue
            values = {
                "input": number(cumulative.get("input_tokens")),
                "output": number(cumulative.get("output_tokens")),
                "cache_read": number(cumulative.get("cached_input_tokens")),
                "total": number(cumulative.get("total_tokens")),
            }
            deltas: dict[str, int] = {}
            for key, current in values.items():
                old = previous[key]
                deltas[key] = current if current < old else current - old
                previous[key] = current
            timestamp = parse_timestamp(row.get("timestamp"), timezone_name)
            total = deltas["total"] or deltas["input"] + deltas["output"] + deltas["cache_read"]
            if not timestamp or total <= 0:
                continue
            events.append((
                str(path), "codex", provider, model, timestamp, session_id, 1,
                deltas["input"], deltas["output"], deltas["cache_read"], 0, total,
            ))
    return events


def source_files(config: Config) -> list[tuple[Path, str, dict[str, tuple[str, str, str]]]]:
    result: list[tuple[Path, str, dict[str, tuple[str, str, str]]]] = []
    for path in expand_paths([config.claude_glob]):
        result.append((path, "claude-code", {}))
    for home in expand_directories(config.codex_homes):
        model_map = codex_state_models(home)
        for path in expand_paths([str(home / "sessions" / "**" / "*.jsonl")]):
            result.append((path, "codex", model_map))
    return result


def update_cache(config: Config) -> int:
    config.cache_db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.cache_db)
    connection.executescript(SCHEMA)
    seen: set[str] = set()
    changed = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for path, source, model_map in source_files(config):
        key = str(path)
        seen.add(key)
        stat = path.stat()
        fingerprint = connection.execute("SELECT size, mtime_ns FROM files WHERE path = ?", (key,)).fetchone()
        if fingerprint == (stat.st_size, stat.st_mtime_ns):
            continue
        connection.execute("DELETE FROM events WHERE path = ?", (key,))
        if source == "claude-code":
            events = parse_claude(path, config.timezone_name)
        else:
            metadata = model_map.get(key, ("codex", "unknown", ""))
            events = parse_codex(path, config.timezone_name, metadata)
        connection.executemany(
            "INSERT INTO events (path, source, provider, model, timestamp, session_id, turns, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, total_tokens) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            events,
        )
        connection.execute(
            "INSERT INTO files (path, source, size, mtime_ns, parsed_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET source=excluded.source, size=excluded.size, mtime_ns=excluded.mtime_ns, parsed_at=excluded.parsed_at",
            (key, source, stat.st_size, stat.st_mtime_ns, now),
        )
        changed += 1
    for (path,) in connection.execute("SELECT path FROM files").fetchall():
        if path not in seen:
            connection.execute("DELETE FROM events WHERE path = ?", (path,))
            connection.execute("DELETE FROM files WHERE path = ?", (path,))
    connection.commit()
    connection.close()
    return changed


def read_events(config: Config) -> list[dict[str, Any]]:
    connection = sqlite3.connect(config.cache_db)
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY timestamp")]
    connection.close()
    return rows


def aggregate(events: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    daily: dict[str, dict[str, Any]] = {}
    model_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    sessions: set[str] = set()
    for event in events:
        day = event["timestamp"][:10]
        row = daily.setdefault(day, {
            "date": day, "sources": {}, "models": {}, "sessions": set(), "turns": 0,
            "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "total_tokens": 0,
        })
        row["sources"][event["source"]] = row["sources"].get(event["source"], 0) + event["total_tokens"]
        row["models"][event["model"]] = row["models"].get(event["model"], 0) + event["total_tokens"]
        row["turns"] += event["turns"]
        for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "total_tokens"):
            row[key] += event[key]
        if event["session_id"]:
            row["sessions"].add(event["session_id"])
            sessions.add(event["session_id"])
        model_counts[event["model"]] += event["total_tokens"]
        provider_counts[event["provider"]] += event["total_tokens"]
        source_counts[event["source"]] += event["total_tokens"]
    for row in daily.values():
        row["sessions"] = len(row["sessions"])
        row["sources"] = dict(sorted(row["sources"].items()))
        row["models"] = dict(sorted(row["models"].items()))
    ordered = {day: daily[day] for day in sorted(daily)}
    summary = {
        "total_tokens": sum(row["total_tokens"] for row in ordered.values()),
        "input_tokens": sum(row["input_tokens"] for row in ordered.values()),
        "output_tokens": sum(row["output_tokens"] for row in ordered.values()),
        "cache_read_tokens": sum(row["cache_read_tokens"] for row in ordered.values()),
        "cache_write_tokens": sum(row["cache_write_tokens"] for row in ordered.values()),
        "active_days": len(ordered), "sessions": len(sessions),
        "turns": sum(row["turns"] for row in ordered.values()),
        "top_models": model_counts.most_common(8), "top_providers": provider_counts.most_common(8),
        "sources": dict(source_counts), "first_date": next(iter(ordered), None),
        "last_date": next(reversed(ordered), None),
    }
    return ordered, summary


def write_ledger(config: Config, daily: dict[str, dict[str, Any]]) -> None:
    config.daily_ledger.parent.mkdir(parents=True, exist_ok=True)
    with config.daily_ledger.open("w", encoding="utf-8") as handle:
        for day in daily:
            handle.write(json.dumps(daily[day], ensure_ascii=False, sort_keys=True) + "\n")


def intensity_levels(values: list[int]) -> dict[int, int]:
    positive = sorted(value for value in values if value > 0)
    if not positive:
        return {}
    thresholds = [positive[max(0, math.ceil(len(positive) * fraction) - 1)] for fraction in (0.25, 0.5, 0.75)]
    return {value: min(4, 1 + sum(value > threshold for threshold in thresholds)) for value in set(values) if value > 0}


def heatmap_svg(daily: dict[str, dict[str, Any]], end_date: date, window_days: int) -> str:
    start = end_date - timedelta(days=window_days - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    days = (end_date - start).days + 1
    values = [daily.get((start + timedelta(days=i)).isoformat(), {}).get("total_tokens", 0) for i in range(days)]
    levels = intensity_levels(values)
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    cell, gap = 11, 3
    columns = math.ceil(days / 7)
    width = columns * (cell + gap) + 42
    height = 7 * (cell + gap) + 24
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Coding activity heatmap" width="{width}" height="{height}">']
    parts.append('<style>text{font-family:Inter,Arial,sans-serif;font-size:10px;fill:#8b949e}.cell{stroke:#0d1117;stroke-width:1}</style>')
    for index, value in enumerate(values):
        current = start + timedelta(days=index)
        column, row = index // 7, (current.weekday() + 1) % 7
        title = f"{current.isoformat()}: {value:,} tokens"
        parts.append(f'<rect class="cell" x="{36 + column * (cell + gap)}" y="{row * (cell + gap) + 10}" width="{cell}" height="{cell}" rx="2" fill="{colors[levels.get(value, 0)]}"><title>{html.escape(title)}</title></rect>')
    parts.append('<text x="0" y="20">Mon</text><text x="0" y="44">Wed</text><text x="0" y="68">Fri</text>')
    return "".join(parts) + "</svg>"


def compact(value: int) -> str:
    for unit, divisor in (("b", 1_000_000_000), ("m", 1_000_000), ("k", 1_000)):
        if value >= divisor:
            return f"{value / divisor:.1f}{unit}"
    return str(value)


def card_svg(config: Config, summary: dict[str, Any], heatmap: str) -> str:
    top_models = " · ".join(f"{html.escape(name)} ({compact(value)})" for name, value in summary["top_models"][:4]) or "No model data"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="300" viewBox="0 0 1000 300" role="img" aria-label="{html.escape(config.title)}">
<defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#0d1117"/><stop offset="1" stop-color="#161b22"/></linearGradient></defs>
<rect width="1000" height="300" rx="18" fill="url(#bg)"/><text x="32" y="42" fill="#f0f6fc" font-size="24" font-family="Inter,Arial,sans-serif" font-weight="700">{html.escape(config.title)}</text>
<text x="32" y="68" fill="#8b949e" font-size="14" font-family="Inter,Arial,sans-serif">{html.escape(config.subtitle)} · {summary.get('first_date') or '—'} to {summary.get('last_date') or '—'}</text>
<text x="32" y="112" fill="#f0f6fc" font-size="28" font-family="Inter,Arial,sans-serif" font-weight="700">{compact(summary['total_tokens'])}</text><text x="32" y="134" fill="#8b949e" font-size="12" font-family="Inter,Arial,sans-serif">reported token units</text>
<text x="180" y="112" fill="#f0f6fc" font-size="28" font-family="Inter,Arial,sans-serif" font-weight="700">{summary['active_days']}</text><text x="180" y="134" fill="#8b949e" font-size="12" font-family="Inter,Arial,sans-serif">active days</text>
<text x="280" y="112" fill="#f0f6fc" font-size="28" font-family="Inter,Arial,sans-serif" font-weight="700">{summary['sessions']}</text><text x="280" y="134" fill="#8b949e" font-size="12" font-family="Inter,Arial,sans-serif">sessions</text>
<text x="32" y="164" fill="#8b949e" font-size="12" font-family="Inter,Arial,sans-serif">Top models</text><text x="32" y="184" fill="#c9d1d9" font-size="12" font-family="Inter,Arial,sans-serif">{top_models}</text>
<g transform="translate(32,205)">{heatmap}</g></svg>'''


def write_outputs(config: Config, daily: dict[str, dict[str, Any]], summary: dict[str, Any]) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    end_date = date.fromisoformat(summary["last_date"]) if summary["last_date"] else date.today()
    heatmap = heatmap_svg(daily, end_date, config.window_days)
    (config.output_dir / "profile.svg").write_text(card_svg(config, summary, heatmap), encoding="utf-8")
    payload = {"daily": daily, "summary": summary}
    (config.output_dir / "profile.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = "".join(f"<tr><td>{html.escape(str(name))}</td><td>{value:,}</td></tr>" for name, value in summary["top_models"])
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(config.title)}</title><style>body{{background:#0d1117;color:#f0f6fc;font-family:Inter,Arial,sans-serif;margin:40px;max-width:1100px}}.muted{{color:#8b949e}}.stats{{display:flex;gap:28px;flex-wrap:wrap}}.stat{{font-size:28px;font-weight:700}}.stat small{{display:block;color:#8b949e;font-size:12px;font-weight:400}}.panel{{border:1px solid #30363d;border-radius:14px;padding:24px;margin-top:24px;overflow:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #21262d;text-align:left}}</style></head><body><h1>{html.escape(config.title)}</h1><p class="muted">{html.escape(config.subtitle)}</p><div class="stats"><div class="stat">{summary['total_tokens']:,}<small>reported token units</small></div><div class="stat">{summary['active_days']}<small>active days</small></div><div class="stat">{summary['sessions']}<small>sessions</small></div><div class="stat">{summary['turns']}<small>usage events</small></div></div><div class="panel">{heatmap}</div><div class="panel"><h2>Top models</h2><table><tr><th>Model</th><th>Tokens</th></tr>{rows}</table></div></body></html>'''
    (config.output_dir / "profile.html").write_text(page, encoding="utf-8")


def run_update(config: Config) -> None:
    changed = update_cache(config)
    events = read_events(config)
    daily, summary = aggregate(events)
    write_ledger(config, daily)
    write_outputs(config, daily, summary)
    print(json.dumps({"changed_files": changed, **summary}, ensure_ascii=False, indent=2))


def run_validate(config: Config) -> None:
    events = read_events(config)
    _, summary = aggregate(events)
    if not events or summary["total_tokens"] <= 0:
        raise SystemExit("No positive usage events found; run update and check config paths")
    print(json.dumps({"valid": True, "events": len(events), **summary}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "validate"))
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "update":
        run_update(config)
    else:
        run_validate(config)


if __name__ == "__main__":
    main()
