#!/usr/bin/env python3
"""Build a public-safe long-term profile from Claude Code and Codex logs."""

from __future__ import annotations

import argparse
import dataclasses
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
    asset_cdn: str
    asset_ref: str  # 覆盖 branch 的不可变引用，通常是 commit SHA
    claude_glob: str
    codex_homes: tuple[str, ...]
    claude_stats_cache: str
    prompt_histories: tuple[tuple[str, str], ...]
    cache_db: Path
    daily_ledger: Path
    prompt_ledger: Path
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
        asset_cdn=str(profile.get("asset_cdn", "jsdelivr")),
        asset_ref="",  # 只由 `profile.py pin --ref <sha>` 设置，不写进配置文件
        claude_glob=str(paths.get("claude_glob", "")),
        codex_homes=tuple(str(item) for item in paths.get("codex_homes", [])),
        claude_stats_cache=str(paths.get("claude_stats_cache", "")),
        prompt_histories=tuple(
            (str(item.get("source", "unknown")), str(item.get("glob", "")))
            for item in paths.get("prompt_histories", [])
            if item.get("glob")
        ),
        cache_db=Path(paths.get("cache_db", "data/profile.sqlite")),
        daily_ledger=Path(paths.get("daily_ledger", "data/daily.jsonl")),
        prompt_ledger=Path(paths.get("prompt_ledger", "data/prompts.jsonl")),
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
    models_by_source: dict[str, Counter[str]] = {}
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
        models_by_source.setdefault(event["source"], Counter())[event["model"]] += event["total_tokens"]
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
        # 不截断：卡片自己决定显示几行，但百分比的分母必须是全部模型，否则算出来
        # 的是「占前 N 名的比例」而不是「占全部用量的比例」
        "top_models": model_counts.most_common(), "top_providers": provider_counts.most_common(8),
        "sources": dict(source_counts), "first_date": next(iter(ordered), None),
        "last_date": next(reversed(ordered), None),
        "hours": hours, "weekdays": weekdays,
        "models_by_source": {
            source: dict(counter.most_common()) for source, counter in models_by_source.items()
        },
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


def merge_prompt_ledger(config: Config,
                        live: dict[str, dict[str, int]]) -> tuple[dict[str, dict[str, int]], int]:
    """把现读到的提示日历并进账本，返回 (合并结果, 仅存在于旧账本的天数)。

    和 token 账本一样只增不减，理由也一样：提示历史文件是各工具自己在维护的，
    会被裁剪、会随家目录一起换机器。之前这份日历每次都从 history.jsonl 现读、
    结果只写进 dist/profile.json 而从不读回来，源文件一旦被裁，日历就会静默变短，
    并且在 git 里表现为删除 —— 已经记下来的日子不该这样消失。

    合并粒度是「日 × 工具」：同一天同一个工具有新数字才覆盖，否则保留旧值。取
    max 而不是直接覆盖，是因为某些工具的历史文件是环形缓冲，重读时可能只剩后半段。
    """
    archived: dict[str, dict[str, int]] = {}
    if config.prompt_ledger.exists():
        with config.prompt_ledger.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                day = str(row.get("date") or "")
                counts = row.get("sources")
                if day and isinstance(counts, dict):
                    archived[day] = {str(k): number(v) for k, v in counts.items()}

    # live 是 {source: {day: count}}，账本按天存 {day: {source: count}}
    fresh: dict[str, dict[str, int]] = {}
    for source, by_day in live.items():
        for day, count in by_day.items():
            fresh.setdefault(day, {})[source] = count

    merged = {day: dict(counts) for day, counts in archived.items()}
    for day, counts in fresh.items():
        row = merged.setdefault(day, {})
        for source, count in counts.items():
            row[source] = max(row.get(source, 0), count)
    retained = sum(1 for day in archived if day not in fresh)

    config.prompt_ledger.parent.mkdir(parents=True, exist_ok=True)
    with config.prompt_ledger.open("w", encoding="utf-8") as handle:
        for day in sorted(merged):
            counts = {k: v for k, v in sorted(merged[day].items()) if v}
            if counts:
                handle.write(json.dumps({"date": day, "sources": counts},
                                        ensure_ascii=False) + "\n")

    # 还原成 read_prompt_calendar 的形状，下游不用改
    out: dict[str, dict[str, int]] = {}
    for day, counts in merged.items():
        for source, count in counts.items():
            if count:
                out.setdefault(source, {})[day] = count
    return out, retained


def read_prompt_calendar(config: Config) -> dict[str, dict[str, int]]:
    """从各工具的提示历史里数出每天提交了多少条提示，按工具分开返回。

    只读时间戳。两种工具的字段名和类型都不一样：Claude 用 `timestamp`（毫秒整
    数），Codex 用 `ts`（秒，且是字符串），所以两个键都试、字符串也接受。提示
    原文和项目路径不进入任何输出。
    """
    zone = ZoneInfo(config.timezone_name)
    calendars: dict[str, Counter[str]] = {}
    for source, pattern in config.prompt_histories:
        for path in expand_paths([pattern]):
            counts = calendars.setdefault(source, Counter())
            try:
                with path.open(encoding="utf-8", errors="ignore") as handle:
                    for line in handle:
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        stamp = row.get("timestamp", row.get("ts"))
                        try:
                            seconds = float(stamp)
                        except (TypeError, ValueError):
                            continue
                        if seconds > 1e11:  # 毫秒
                            seconds /= 1000
                        counts[datetime.fromtimestamp(seconds, zone).date().isoformat()] += 1
            except OSError:
                continue
    return {source: dict(counts) for source, counts in calendars.items() if counts}


def merge_backfill(daily: dict[str, dict[str, Any]], summary: dict[str, Any],
                   stats: dict[str, Any],
                   prompts: dict[str, dict[str, int]]) -> tuple[dict, dict]:
    """把回填数据并进日账本与汇总。

    transcript 永远优先：它有 input/output/cache 拆分，聚合缓存没有。回填只填
    transcript 完全没有覆盖的日子，并打上 estimated 标记，免得把粗粒度数字
    当成精确数字读。
    """
    added = 0
    backfilled_models: Counter[str] = Counter()
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
    summary["top_models"] = models.most_common()  # 全量，理由同 aggregate
    summary["sources"] = dict(sources)

    # 回填的 token 一定来自 claude-code，并进分工具明细。这里用回填时单独攒的
    # 计数，而不是去读 row["models"] —— 部分回填的日子里那份 dict 混着 Codex 的
    # 模型，无法区分谁是回填来的。
    if backfilled_models:
        by_source = summary.setdefault("models_by_source", {})
        claude = Counter(by_source.get("claude-code", {}))
        claude.update(backfilled_models)
        by_source["claude-code"] = dict(claude.most_common())

    summary["backfilled_days"] = added
    # Claude 的终身累计（stats-cache 的 modelUsage）没有日期维度，无法进热力图，
    # 只作为参考留在 profile.json 里；卡片一律用有日期的口径，保持前后一致。
    summary["claude_lifetime_tokens"] = stats.get("lifetime_tokens", 0)
    # 提示日历跨全部工具汇总；分工具明细留在 profile.json 里备查
    merged: Counter[str] = Counter()
    for counts in prompts.values():
        merged.update(counts)
    summary["prompt_calendar"] = dict(sorted(merged.items()))
    summary["prompt_calendar_by_source"] = {
        source: dict(sorted(counts.items())) for source, counts in sorted(prompts.items())
    }
    summary["prompt_total"] = sum(merged.values())
    summary["prompt_sources"] = {
        source: sum(counts.values()) for source, counts in sorted(prompts.items())
    }
    summary["prompt_first"] = next(iter(summary["prompt_calendar"]), None)
    return ordered, summary


def write_ledger(config: Config, daily: dict[str, dict[str, Any]]) -> int:
    """把当前聚合结果合并进日账本，返回仅存在于旧账本里的天数。

    账本是这个项目唯一的长期归档，所以必须真的只增不减：Claude Code 会删会话
    记录，聚合缓存也会轮转，如果每次都整份覆盖，那些日子就会从公开账本里悄悄
    消失 —— 而且是在 git 里显示为删除。已经记下来的日子一律保留，同一天有新数
    据才覆盖。
    """
    config.daily_ledger.parent.mkdir(parents=True, exist_ok=True)
    archived: dict[str, dict[str, Any]] = {}
    if config.daily_ledger.exists():
        with config.daily_ledger.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                day = str(row.get("date") or "")
                if day:
                    archived[day] = row
    retained = sum(1 for day in archived if day not in daily)
    merged = {**archived, **daily}
    with config.daily_ledger.open("w", encoding="utf-8") as handle:
        for day in sorted(merged):
            handle.write(json.dumps(merged[day], ensure_ascii=False, sort_keys=True) + "\n")
    return retained



# ---------------------------------------------------------------- 输出

GALLERY_BEGIN = "<!-- profile:gallery:begin -->"
GALLERY_END = "<!-- profile:gallery:end -->"

# README 图集布局：每行一个卡片名列表，同行的卡片会并排显示。
# token 口径集中在终端卡里；分工具热力图/模型榜放 <details> 折叠区（见下）。
GALLERY_ROWS: tuple[tuple[str, ...], ...] = (
    ("calendar",),
    ("terminal",),
)

CARD_ALT = {
    "calendar": "Prompt calendar",
    "terminal": "Terminal-style summary",
}


def asset_url(config: Config, name: str, digest: str) -> str:
    """卡片地址。配了 repo 就用绝对地址，否则退回仓库内相对路径。

    asset_ref 给定时用它代替分支名（发布脚本会传刚提交的 commit SHA）。这一步是
    必要的而不是优化：jsDelivr 的 @branch 地址会在边缘缓存 12 小时，**并且忽略
    查询串**，所以 ?v=<digest> 对它不起作用；实测 push 之后 purge 都报 finished，
    仍有多个边缘节点在发上一版的文件。@<sha> 则是不可变资源，回源立刻就是对的，
    而且带 max-age=31536000, immutable —— 既不用 purge，缓存还从 7 天变成一年。

    asset_cdn 决定用哪个源，这直接影响读者能不能看到图：

    - "jsdelivr"（默认）：走 cdn.jsdelivr.net。GitHub 只代理第三方域名的图，所以
      这个地址会被改写成 camo.githubusercontent.com，浏览器拿到的缓存是
      max-age=691200（8 天）。图成功加载一次就能管一周多。
    - "raw"：走 raw.githubusercontent.com。GitHub 认得这是自家域名，原样放行、
      不经 camo，浏览器直连；而且 raw 只给 max-age=300（5 分钟），等于每隔
      5 分钟就要重新撞一次这个域名。网络不稳时图会时有时无。

    两者都带内容摘要做 cache-bust：图变了地址就变，camo 和 jsDelivr 的边缘缓存
    都会当成新资源重新回源，不会卡着旧图。
    """
    if not config.repo:
        return f"./{config.output_dir.as_posix()}/{name}.svg"
    path = f"{config.output_dir.as_posix()}/{name}.svg"
    ref = config.asset_ref or config.branch
    if config.asset_cdn == "raw":
        base = f"https://raw.githubusercontent.com/{config.repo}/{ref}"
    else:
        base = f"https://cdn.jsdelivr.net/gh/{config.repo}@{ref}"
    return f"{base}/{path}?v={digest}"


def picture(config: Config, card: str, digests: dict[str, str], alt: str, width: int) -> str:
    """一张亮/暗自适应的图。<picture> 按读者的 GitHub 主题选对应文件。"""
    dark = asset_url(config, f"{card}-dark", digests.get(f"{card}-dark", ""))
    light = asset_url(config, f"{card}-light", digests.get(f"{card}-light", ""))
    return (
        "<picture>"
        f'<source media="(prefers-color-scheme: dark)" srcset="{dark}">'
        f'<source media="(prefers-color-scheme: light)" srcset="{light}">'
        f'<img alt="{html.escape(alt)}" src="{light}" width="{width}">'
        "</picture>"
    )


def gallery_markdown(config: Config, digests: dict[str, str],
                     summary: dict[str, Any]) -> str:
    """生成 README 中的图集区块。

    每行独立包在 <p align="center"> 里：GitHub 的 Markdown 会把它当成一个完整
    HTML 块，比依赖外层 <div> 更稳（块内空行会中断 HTML 解析）。同一行的多张图
    之间不能有空白字符，否则会被渲染成词间空格，两张 440 宽的卡片加起来就超过
    880，和整宽卡片对不齐。
    """
    blocks: list[str] = []
    for row in GALLERY_ROWS:
        pictures = [
            picture(config, card, digests, CARD_ALT.get(card, card),
                    render.CARD_SIZES.get(card, (render.CARD_WIDTH, 0))[0])
            for card in row
        ]
        blocks.append('<p align="center">' + "".join(pictures) + "</p>")

    # 分工具视图。README 里跑不了 JS，<details> 是 GitHub 唯一支持的原生交互，
    # 所以「只看某个工具」做成折叠区而不是按钮。
    #
    # 所有工具收进同一个折叠：每加一个 agent 就多一个折叠的话，主页会被摘要行堆满，
    # 而这些摘要彼此是同一类信息。合成一个之后，加 qwen、gemini 之类只是往里面多
    # 一节，主页高度不变。
    half = render.HALF_WIDTH
    tools = [t for t in sorted(summary.get("sources", {}))
             if f"heatmap-{t}-dark" in digests]
    if tools:
        grand = sum(summary["sources"].values()) or 1
        chips = " &nbsp;·&nbsp; ".join(
            f"<b>{html.escape(t)}</b> {summary['sources'][t] / grand * 100:.0f}%"
            for t in sorted(tools, key=lambda t: -summary["sources"][t])
        )
        sections = []
        for tool in tools:
            share = summary["sources"][tool] / grand
            prompts = (summary.get("prompt_sources") or {}).get(tool)
            detail = (f"{render.compact(summary['sources'][tool])} tokens "
                      f"&nbsp;·&nbsp; {share * 100:.0f}% of total")
            if prompts:
                detail += f" &nbsp;·&nbsp; {prompts:,} prompts"
            sections.append(
                f'<p align="center"><b>{html.escape(tool)}</b> '
                f"&nbsp;·&nbsp; {detail}</p>\n"
                f'<p align="center">'
                + picture(config, f"heatmap-{tool}", digests,
                          f"{tool} activity heatmap", render.CARD_WIDTH)
                + "</p>\n"
                f'<p align="center">'
                + picture(config, f"models-{tool}", digests, f"{tool} models", half)
                + "</p>"
            )
        blocks.append(
            f"<details>\n<summary>&nbsp;<b>By tool</b> &nbsp;·&nbsp; {chips}</summary>\n"
            f"<br>\n" + "\n".join(sections) + "\n</details>"
        )

    # 往年的提示日历。当前档案年在主页，更早的收进折叠区，摘要行写明起止日期。
    spans = summary.get("calendar_spans") or []
    past = [s for s in spans[:-1] if f"{s['key']}-dark" in digests]
    if past:
        labels = ", ".join(f"{s['start']} → {s['end']}" for s in reversed(past))
        body = "\n".join(
            f'<p align="center">'
            + picture(config, s["key"], digests,
                      f"Prompt calendar {s['start']} to {s['end']}", render.CARD_WIDTH)
            + "</p>"
            for s in reversed(past)
        )
        blocks.append(
            f"<details>\n<summary>&nbsp;<b>Earlier years</b> &nbsp;·&nbsp; "
            f"{html.escape(labels)}</summary>\n<br>\n{body}\n</details>"
        )
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

    # 兼容旧引用：profile.svg 始终指向当前的主视觉卡（现在是热力图）
    (config.output_dir / "profile.svg").write_text(cards["heatmap-dark"], encoding="utf-8")

    payload = {"daily": daily, "summary": summary}
    (config.output_dir / "profile.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (config.output_dir / "profile.html").write_text(
        render.report_html(config.title, config.subtitle, cards, summary), encoding="utf-8"
    )
    update_readme(config, gallery_markdown(config, digests, summary))


def run_update(config: Config) -> None:
    changed = update_cache(config)
    events = read_events(config)
    daily, summary = aggregate(events)
    prompts, prompt_retained = merge_prompt_ledger(config, read_prompt_calendar(config))
    daily, summary = merge_backfill(
        daily, summary, read_stats_cache(config), prompts
    )
    retained = write_ledger(config, daily)
    write_outputs(config, daily, summary)
    report = {k: v for k, v in summary.items()
              if k not in ("prompt_calendar", "prompt_calendar_by_source", "models_by_source")}
    print(json.dumps(
        {"changed_files": changed, "ledger_only_days": retained,
         "prompt_ledger_only_days": prompt_retained, **report},
        ensure_ascii=False, indent=2,
    ))


def run_pin(config: Config, ref: str) -> None:
    """把 README 里的图片地址钉到某个 commit SHA 上，只改 README，不碰 dist/。

    发布流程是两步：先提交 dist/（得到 SHA），再用这个命令把 README 指向那个
    SHA、单独提交。不能重跑 update 来做这件事 —— update 会重新生成卡片，而 token
    和提示数一直在涨，重跑出来的图和已经提交的那份就对不上了。

    摘要直接从磁盘上已提交的 SVG 算，保证和 dist/ 里的字节完全一致。
    """
    digests: dict[str, str] = {}
    for path in sorted(config.output_dir.glob("*.svg")):
        if path.stem == "profile":  # 兼容用的别名，不出现在图集里
            continue
        digests[path.stem] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()[:8]
    if not digests:
        raise SystemExit(f"No cards in {config.output_dir}; run update first")

    payload = json.loads((config.output_dir / "profile.json").read_text(encoding="utf-8"))
    pinned = dataclasses.replace(config, asset_ref=ref)
    changed = update_readme(pinned, gallery_markdown(pinned, digests, payload["summary"]))
    print(json.dumps({"pinned_ref": ref, "cards": len(digests), "readme_updated": changed},
                     ensure_ascii=False, indent=2))


def run_validate(config: Config) -> None:
    events = read_events(config)
    _, summary = aggregate(events)
    if not events or summary["total_tokens"] <= 0:
        raise SystemExit("No positive usage events found; run update and check config paths")
    print(json.dumps({"valid": True, "events": len(events), **summary}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "validate", "pin"))
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--ref", default="",
                        help="pin 用：把 README 的图片地址钉到这个 commit SHA")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "update":
        run_update(config)
    elif args.command == "pin":
        if not args.ref:
            raise SystemExit("pin requires --ref <commit-sha>")
        run_pin(config, args.ref)
    else:
        run_validate(config)


if __name__ == "__main__":
    main()
