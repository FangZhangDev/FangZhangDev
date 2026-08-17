#!/usr/bin/env python3
"""Build a public-safe long-term profile from Claude Code and Codex logs."""

from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import render


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
    repo: str
    branch: str
    claude_glob: str
    codex_homes: tuple[str, ...]
    claude_stats_cache: str
    claude_history: str
    cache_db: Path
    daily_ledger: Path
    output_dir: Path
    readme: Path


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
        repo=str(profile.get("repo", "")),
        branch=str(profile.get("branch", "main")),
        claude_glob=str(paths.get("claude_glob", "")),
        codex_homes=tuple(str(item) for item in paths.get("codex_homes", [])),
        claude_stats_cache=str(paths.get("claude_stats_cache", "")),
        claude_history=str(paths.get("claude_history", "")),
        cache_db=Path(paths.get("cache_db", "data/profile.sqlite")),
        daily_ledger=Path(paths.get("daily_ledger", "data/daily.jsonl")),
        output_dir=Path(paths.get("output_dir", "dist")),
        readme=Path(paths.get("readme", "README.md")),
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
    hours = [0] * 24
    weekdays = [0] * 7
    for event in events:
        day = event["timestamp"][:10]
        # 小时/星期分布只统计轮数，不含任何内容，可安全公开
        try:
            hours[int(event["timestamp"][11:13])] += event["turns"]
            weekdays[date.fromisoformat(day).weekday()] += event["turns"]
        except (ValueError, IndexError):
            pass
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
        "hours": hours, "weekdays": weekdays,
    }
    return ordered, summary


# ---------------------------------------------------------------- 历史回填
#
# Claude Code 默认 30 天就删掉本地会话记录（cleanupPeriodDays），所以只读
# transcript 会让早期活动凭空消失。两份不受该清理影响的文件可以补回来：
#
#   ~/.claude/stats-cache.json  聚合统计。dailyModelTokens 有每日每模型 token
#                               （但没有 input/output/cache 拆分）；dailyActivity
#                               有更早的消息/会话数，没有 token。
#   ~/.claude/history.jsonl     提示历史，覆盖期最长。只取时间戳算每日条数，
#                               提示原文和项目路径一律不读进来。


def read_stats_cache(config: Config) -> dict[str, Any]:
    """读 Claude Code 的聚合统计缓存。文件缺失或损坏都只当作没有回填数据。"""
    if not config.claude_stats_cache:
        return {}
    path = Path(os.path.expanduser(config.claude_stats_cache))
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    tokens: dict[str, dict[str, int]] = {}
    for row in raw.get("dailyModelTokens") or []:
        day = str(row.get("date") or "")
        by_model = row.get("tokensByModel") or {}
        if day and isinstance(by_model, dict):
            tokens[day] = {str(k): number(v) for k, v in by_model.items()}
    activity: dict[str, int] = {}
    for row in raw.get("dailyActivity") or []:
        day = str(row.get("date") or "")
        if day:
            activity[day] = number(row.get("sessionCount"))
    lifetime = 0
    for usage in (raw.get("modelUsage") or {}).values():
        if isinstance(usage, dict):
            lifetime += sum(
                number(usage.get(key)) for key in
                ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
            )
    return {"tokens": tokens, "sessions": activity, "lifetime_tokens": lifetime,
            "first_session": str(raw.get("firstSessionDate") or "")[:10]}


def read_prompt_calendar(config: Config) -> dict[str, int]:
    """从提示历史里数出每天提交了多少条提示。只读时间戳。"""
    if not config.claude_history:
        return {}
    path = Path(os.path.expanduser(config.claude_history))
    if not path.exists():
        return {}
    zone = ZoneInfo(config.timezone_name)
    counts: Counter[str] = Counter()
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                try:
                    stamp = json.loads(line).get("timestamp")
                except json.JSONDecodeError:
                    continue
                if not isinstance(stamp, (int, float)):
                    continue
                seconds = stamp / 1000 if stamp > 1e11 else stamp
                counts[datetime.fromtimestamp(seconds, zone).date().isoformat()] += 1
    except OSError:
        return {}
    return dict(counts)


def merge_backfill(daily: dict[str, dict[str, Any]], summary: dict[str, Any],
                   stats: dict[str, Any], prompts: dict[str, int]) -> tuple[dict, dict]:
    """把回填数据并进日账本与汇总。

    transcript 永远优先：它有 input/output/cache 拆分，聚合缓存没有。回填只填
    transcript 完全没有覆盖的日子，并打上 estimated 标记，免得把粗粒度数字
    当成精确数字读。
    """
    added = 0
    for day, by_model in sorted(stats.get("tokens", {}).items()):
        row = daily.get(day)
        # 判断依据是「这天有没有 claude-code 的 transcript」，而不是「这天有没有记录」。
        # 早期很多天只有 Codex 记录，按整天判断会把 Claude 的部分整块漏掉。
        if row is not None and "claude-code" in row["sources"]:
            continue
        total = sum(by_model.values())
        if total <= 0:
            continue
        if row is None:
            daily[day] = {
                "date": day, "sources": {"claude-code": total},
                "models": dict(sorted(by_model.items())),
                "sessions": stats.get("sessions", {}).get(day, 0), "turns": 0,
                "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                "cache_write_tokens": 0, "total_tokens": total,
                # 该日来自聚合缓存，只有 token 总数，没有 input/output/cache 分项
                "estimated": True,
            }
        else:
            row["sources"]["claude-code"] = total
            row["sources"] = dict(sorted(row["sources"].items()))
            for model, value in by_model.items():
                row["models"][model] = row["models"].get(model, 0) + value
            row["models"] = dict(sorted(row["models"].items()))
            row["sessions"] += stats.get("sessions", {}).get(day, 0)
            row["total_tokens"] += total
            row["estimated"] = True
        added += 1

    ordered = {day: daily[day] for day in sorted(daily)}
    for key in ("total_tokens", "input_tokens", "output_tokens",
                "cache_read_tokens", "cache_write_tokens"):
        summary[key] = sum(row[key] for row in ordered.values())
    summary["active_days"] = len(ordered)
    summary["sessions"] = sum(row["sessions"] for row in ordered.values())
    summary["turns"] = sum(row["turns"] for row in ordered.values())
    summary["first_date"] = next(iter(ordered), None)
    summary["last_date"] = next(reversed(ordered), None)

    models: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for row in ordered.values():
        models.update(row["models"])
        sources.update(row["sources"])
    summary["top_models"] = models.most_common(8)
    summary["sources"] = dict(sources)

    summary["backfilled_days"] = added
    # Claude 的终身累计（stats-cache 的 modelUsage）没有日期维度，无法进热力图，
    # 只作为参考留在 profile.json 里；卡片一律用有日期的口径，保持前后一致。
    summary["claude_lifetime_tokens"] = stats.get("lifetime_tokens", 0)
    summary["prompt_calendar"] = dict(sorted(prompts.items()))
    summary["prompt_total"] = sum(prompts.values())
    summary["prompt_first"] = next(iter(summary["prompt_calendar"]), None)
    return ordered, summary


def write_ledger(config: Config, daily: dict[str, dict[str, Any]]) -> None:
    config.daily_ledger.parent.mkdir(parents=True, exist_ok=True)
    with config.daily_ledger.open("w", encoding="utf-8") as handle:
        for day in daily:
            handle.write(json.dumps(daily[day], ensure_ascii=False, sort_keys=True) + "\n")



# ---------------------------------------------------------------- 输出

GALLERY_BEGIN = "<!-- profile:gallery:begin -->"
GALLERY_END = "<!-- profile:gallery:end -->"

# README 图集布局：每行一个卡片名列表，同行的卡片会并排显示
GALLERY_ROWS: tuple[tuple[str, ...], ...] = (
    ("hero",),
    ("heatmap",),
    ("calendar",),
    ("stats", "models"),
    ("clock", "weekdays"),
    ("trend",),
    ("terminal",),
)

CARD_ALT = {
    "hero": "AI coding profile summary",
    "heatmap": "Daily activity heatmap",
    "calendar": "Prompt calendar",
    "stats": "Token split by tool",
    "models": "Top models by usage",
    "clock": "Hourly coding rhythm",
    "weekdays": "Weekday distribution",
    "trend": "Recent 90-day trend",
    "terminal": "Terminal-style summary",
}


def asset_url(config: Config, name: str, digest: str) -> str:
    """卡片地址。配了 repo 就用 raw 绝对地址，否则退回仓库内相对路径。

    带上内容摘要做 cache-bust，让 GitHub 的 camo 代理在图变了之后立刻取新图。
    """
    if config.repo:
        base = f"https://raw.githubusercontent.com/{config.repo}/{config.branch}"
        return f"{base}/{config.output_dir.as_posix()}/{name}.svg?v={digest}"
    return f"./{config.output_dir.as_posix()}/{name}.svg"


def gallery_markdown(config: Config, digests: dict[str, str]) -> str:
    """生成 README 中的图集区块。

    每行独立包在 <p align="center"> 里：GitHub 的 Markdown 会把它当成一个完整
    HTML 块，比依赖外层 <div> 更稳（块内空行会中断 HTML 解析）。<picture> 负责
    按读者的亮/暗主题各取一张图。
    """
    blocks: list[str] = []
    for row in GALLERY_ROWS:
        pictures = []
        for card in row:
            dark = asset_url(config, f"{card}-dark", digests.get(f"{card}-dark", ""))
            light = asset_url(config, f"{card}-light", digests.get(f"{card}-light", ""))
            width = render.CARD_SIZES.get(card, (880, 0))[0]
            pictures.append(
                "  <picture>\n"
                f'    <source media="(prefers-color-scheme: dark)" srcset="{dark}">\n'
                f'    <source media="(prefers-color-scheme: light)" srcset="{light}">\n'
                f'    <img alt="{html.escape(CARD_ALT.get(card, card))}" src="{light}" width="{width}">\n'
                "  </picture>"
            )
        blocks.append('<p align="center">\n' + "\n".join(pictures) + "\n</p>")
    return "\n\n".join(blocks)


def update_readme(config: Config, gallery: str) -> bool:
    """只替换 README 里标记包裹的图集区块，手写文案原样保留。"""
    if not config.readme.exists():
        return False
    text = config.readme.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(GALLERY_BEGIN) + r".*?" + re.escape(GALLERY_END), re.DOTALL
    )
    if not pattern.search(text):
        return False
    replacement = f"{GALLERY_BEGIN}\n{gallery}\n{GALLERY_END}"
    updated = pattern.sub(lambda _: replacement, text, count=1)
    if updated == text:
        return False
    config.readme.write_text(updated, encoding="utf-8")
    return True


def write_outputs(config: Config, daily: dict[str, dict[str, Any]], summary: dict[str, Any]) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    cards = render.build_cards(
        daily, summary, config.title, config.subtitle, config.window_days
    )
    digests: dict[str, str] = {}
    for name, markup in cards.items():
        (config.output_dir / f"{name}.svg").write_text(markup, encoding="utf-8")
        digests[name] = hashlib.sha256(markup.encode("utf-8")).hexdigest()[:8]

    # 兼容旧引用：profile.svg 始终等于暗色主视觉卡
    (config.output_dir / "profile.svg").write_text(cards["hero-dark"], encoding="utf-8")

    payload = {"daily": daily, "summary": summary}
    (config.output_dir / "profile.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (config.output_dir / "profile.html").write_text(
        render.report_html(config.title, config.subtitle, cards, summary), encoding="utf-8"
    )
    update_readme(config, gallery_markdown(config, digests))


def run_update(config: Config) -> None:
    changed = update_cache(config)
    events = read_events(config)
    daily, summary = aggregate(events)
    daily, summary = merge_backfill(
        daily, summary, read_stats_cache(config), read_prompt_calendar(config)
    )
    write_ledger(config, daily)
    write_outputs(config, daily, summary)
    report = {k: v for k, v in summary.items() if k != "prompt_calendar"}
    print(json.dumps({"changed_files": changed, **report}, ensure_ascii=False, indent=2))


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
