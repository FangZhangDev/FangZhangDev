#!/usr/bin/env python3
"""渲染层：把聚合结果画成可嵌入 GitHub README 的 SVG 卡片。

卡片是贴在 GitHub 页面上的，所以底色、边框、圆角、字号、方格几何、月份刻度和
Less/More 图例都跟随 GitHub Primer，免得看起来像外来物。但色相另选：这里量的
是 token 和提示数而不是 commit，沿用贡献图的绿会让人误读成提交量。

渲染约束（GitHub 通过 <img> + camo 代理渲染 SVG）：
- 不执行 JavaScript，不加载外部字体，只能用系统字体栈；
- <title> 提示框不生效，所有信息必须画在图上；
- CSS 动画可用，但必须保证「动画不被支持时仍显示最终状态」；
- 亮/暗主题靠生成两份文件 + README 里的 <picture> 切换，比 SVG 内媒体查询可靠。
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Sequence


# GitHub 自己用的字体栈
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,"
        "sans-serif,'Apple Color Emoji','Segoe UI Emoji'")
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


@dataclass(frozen=True)
class Theme:
    """一套配色。取值来自 GitHub Primer 的 canvas / border / fg / accent 标度。"""

    name: str
    canvas: str  # 卡片底色，等于 GitHub 页面底色
    subtle: str  # 次级面板底色
    border: str
    fg: str  # 主文字
    muted: str  # 次要文字
    faint: str  # 刻度、脚注
    accents: tuple[str, ...]  # 分类色，取自 Primer 的 purple/pink/amber/cyan/green/blue


# 方格的几何、月份刻度、Less/More 图例都照搬 GitHub，但色相刻意避开贡献图的绿：
# 这里量的是 token 和提示数，不是 commit，撞色只会让人误读。两张网格各用一个色
# 相，读者扫一眼就知道它们不是同一个指标。
DARK = Theme(
    name="dark",
    canvas="#0d1117",
    subtle="#151b23",
    border="#3d444d",
    fg="#f0f6fc",
    muted="#9198a1",
    faint="#6e7681",
    accents=("#a371f7", "#f778ba", "#e3b341", "#56d4dd", "#3fb950", "#4493f8"),
)

LIGHT = Theme(
    name="light",
    canvas="#ffffff",
    subtle="#f6f8fa",
    border="#d1d9e0",
    fg="#1f2328",
    muted="#59636e",
    faint="#818b98",
    accents=("#8250df", "#bf3989", "#9a6700", "#0e7490", "#1a7f37", "#0969da"),
)

THEMES = (DARK, LIGHT)

# 网格梯度按用途取用，不绑在主题上：一个色相代表一个含义。紫色是主日历，青色和
# 粉色分给两个工具，让分工具视图一眼可辨。绿色留给 GitHub 真正的贡献图。
RAMPS: dict[str, dict[str, tuple[str, str, str, str, str]]] = {
    "violet": {
        "dark": ("#161b22", "#30215f", "#4d2fa0", "#7449d6", "#a78bfa"),
        "light": ("#ebedf0", "#ddd0fb", "#b794f4", "#8250df", "#553098"),
    },
    "cyan": {
        "dark": ("#161b22", "#0c3b45", "#0f6577", "#1a9db5", "#56d4dd"),
        "light": ("#ebedf0", "#c8eaf2", "#7fd0e0", "#2497b4", "#0b6b80"),
    },
    "pink": {
        "dark": ("#161b22", "#4d1533", "#8a1f57", "#c93a84", "#f778ba"),
        "light": ("#ebedf0", "#fbd3e7", "#f19cc8", "#d4459a", "#8c1d5e"),
    },
}

PRIMARY_RAMP = "violet"
TOOL_RAMPS = ("cyan", "pink", "violet")  # 按工具名排序循环取用


def ramp_for(name: str, theme: Theme) -> tuple[str, str, str, str, str]:
    return RAMPS.get(name, RAMPS[PRIMARY_RAMP])[theme.name]


def tool_ramp(tool: str, tools: Sequence[str], theme: Theme) -> tuple[str, ...]:
    index = list(tools).index(tool) if tool in tools else 0
    return ramp_for(TOOL_RAMPS[index % len(TOOL_RAMPS)], theme)

# GitHub 贡献图的方格比例：10px 方块、3px 间距、2px 圆角。
# 这里放大到 12px 以填满 880 宽的卡片，比例保持不变。
CELL, GAP, RADIUS = 12, 3, 2
PITCH = CELL + GAP

CARD_WIDTH = 880
HALF_WIDTH = 440  # 两张并排刚好等于一张整宽，README 里两行才能左右对齐


# ---------------------------------------------------------------- 基础工具


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def compact(value: int) -> str:
    """把大整数压成 7.29B / 48.1K 这类紧凑写法。"""
    for unit, divisor in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if value >= divisor:
            scaled = value / divisor
            if scaled >= 100:
                text = f"{scaled:.0f}"
            elif scaled >= 10:
                text = f"{scaled:.1f}"
            else:
                text = f"{scaled:.2f}"
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text + unit
    return f"{value:,}"


def clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def base_style(theme: Theme) -> str:
    """共用排版与动画。字号跟随 GitHub：正文 14px，辅助 12px，刻度 10px。"""
    return (
        "<style>"
        f"text{{font-family:{FONT}}}"
        f".mono{{font-family:{MONO}}}"
        f".h{{font-size:14px;font-weight:600;fill:{theme.fg}}}"
        f".sub{{font-size:12px;fill:{theme.muted}}}"
        f".tick{{font-size:10px;fill:{theme.muted}}}"
        f".foot{{font-size:11px;fill:{theme.faint}}}"
        f".num{{font-size:22px;font-weight:600;fill:{theme.fg}}}"
        f".num-s{{font-size:15px;font-weight:600;fill:{theme.fg}}}"
        f".lab{{font-size:11px;fill:{theme.muted}}}"
        "@keyframes fu{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}"
        "@keyframes po{from{opacity:0;transform:scale(.5)}to{opacity:1;transform:none}}"
        "@keyframes gw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        "@keyframes fi{from{opacity:0}to{opacity:1}}"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".fu{animation:fu .5s cubic-bezier(.22,1,.36,1) both}"
        ".po{animation:po .4s cubic-bezier(.22,1,.36,1) both;transform-box:fill-box;transform-origin:center}"
        ".gw{animation:gw .8s cubic-bezier(.22,1,.36,1) both;transform-box:fill-box;transform-origin:left center}"
        # 只淡入的容器动画：元素自身的 opacity 属性得以保留，两者相乘
        ".fi{animation:fi .45s ease-out both}"
        ".cur{animation:blink 1.1s step-end infinite}"
        "</style>"
    )


def frame(width: int, height: int, theme: Theme) -> str:
    """卡片外框。照搬 GitHub 内容盒：纯色底 + 1px 边框 + 6px 圆角，不加渐变。"""
    return (
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="6" '
        f'fill="{theme.canvas}" stroke="{theme.border}"/>'
    )


def open_svg(width: int, height: int, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">'
    )


def divider(width: int, y: float, theme: Theme, inset: int = 16) -> str:
    return (
        f'<line x1="{inset}" y1="{y}" x2="{width - inset}" y2="{y}" '
        f'stroke="{theme.border}" stroke-opacity=".7"/>'
    )


def intensity_levels(values: Iterable[int]) -> dict[int, int]:
    """按四分位把数值分到 1-4 级，和 GitHub 的分级口径一致。"""
    positive = sorted(value for value in values if value > 0)
    if not positive:
        return {}
    thresholds = [
        positive[max(0, math.ceil(len(positive) * fraction) - 1)]
        for fraction in (0.25, 0.5, 0.75)
    ]
    return {
        value: min(4, 1 + sum(value > threshold for threshold in thresholds))
        for value in set(positive)
    }


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def legend(x: float, y: float, ramp: Sequence[str]) -> str:
    """GitHub 的 Less □□□□□ More 图例。"""
    parts = [f'<text class="tick" x="{x}" y="{y}">Less</text>']
    for level in range(5):
        parts.append(
            f'<rect x="{x + 28 + level * (CELL + 2)}" y="{y - CELL + 2}" width="{CELL}" '
            f'height="{CELL}" rx="{RADIUS}" fill="{ramp[level]}"/>'
        )
    parts.append(
        f'<text class="tick" x="{x + 28 + 5 * (CELL + 2) + 4}" y="{y}">More</text>'
    )
    return "".join(parts)


def grid_block(values: Sequence[int], start: date, end_date: date, uid: str,
               ramp: Sequence[str], width: int, top: int) -> tuple[str, float, float]:
    """画一整块贡献方格，含月份刻度和 Mon/Wed/Fri 标签。

    返回 (svg, 网格左边界, 网格右边界)，调用方据此对齐脚注和图例。
    """
    columns = math.ceil(len(values) / 7)
    grid_width = columns * PITCH - GAP
    left = max(44, round((width - grid_width) / 2))
    levels = intensity_levels(values)

    # 逐列的入场延迟收进 CSS 类，避免每个方格都带一段 inline style
    delays = "".join(
        f".{uid}d{column}{{animation-delay:{.1 + column * .008:.3f}s}}"
        for column in range(columns)
    )
    parts = [
        f"<style>{delays}</style>"
        f'<defs><rect id="{uid}c" width="{CELL}" height="{CELL}" rx="{RADIUS}"/></defs>'
    ]

    # 月份刻度：先收集所有换月的列，再筛掉画不下的。窗口首尾那两个月往往只占
    # 一两列，直接标就会和邻月挤成「SepOct」。所以一个月至少要占 MIN_MONTH_COLS
    # 列才配拥有标签，且相邻标签之间也要留够间距。
    MIN_MONTH_COLS = 3
    changes: list[tuple[int, int]] = []
    last_month = None
    for column in range(columns):
        day = start + timedelta(days=column * 7)
        if day > end_date:
            break
        if day.month != last_month:
            last_month = day.month
            changes.append((column, day.month))

    placed: list[int] = []
    for index, (column, month) in enumerate(changes):
        span_end = changes[index + 1][0] if index + 1 < len(changes) else columns
        if span_end - column < MIN_MONTH_COLS:
            continue
        if placed and column - placed[-1] < MIN_MONTH_COLS:
            continue
        placed.append(column)
        parts.append(
            f'<text class="tick" x="{left + column * PITCH}" y="{top - 6}">'
            f'{MONTHS[month - 1]}</text>'
        )

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(
            f'<text class="tick" x="{left - 8}" y="{top + row * PITCH + CELL - 2}" '
            f'text-anchor="end">{label}</text>'
        )

    for index, value in enumerate(values):
        column, row = index // 7, index % 7
        parts.append(
            f'<use class="po {uid}d{column}" href="#{uid}c" x="{left + column * PITCH}" '
            f'y="{top + row * PITCH}" fill="{ramp[levels.get(value, 0)]}"/>'
        )
    return "".join(parts), left, left + grid_width


# ---------------------------------------------------------------- 卡片：热力图


def card_heatmap(daily: dict[str, dict[str, Any]], end_date: date, window_days: int,
                 summary: dict[str, Any], theme: Theme, source: str | None = None) -> str:
    """Token 热力图。source 给定时只统计该工具，用于 README 里的分工具折叠区。"""
    uid = f"m{theme.name}{(source or 'all').replace('-', '')}"
    width, height = CARD_WIDTH, 192
    top = 60

    start = end_date - timedelta(days=window_days - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # 对齐到周日
    days = (end_date - start).days + 1

    def value_of(day: str) -> int:
        row = daily.get(day)
        if row is None:
            return 0
        return row["sources"].get(source, 0) if source else row["total_tokens"]

    values = [value_of((start + timedelta(days=i)).isoformat()) for i in range(days)]
    total = sum(values)
    active = sum(1 for value in values if value > 0)
    # 汇总视图用主色（紫）；分工具视图按工具取青/粉，和它们各自的提示日历一致
    tools = sorted(summary.get("sources", {}))
    ramp = tool_ramp(source, tools, theme) if source else ramp_for(PRIMARY_RAMP, theme)

    out = [open_svg(width, height, "Token activity heatmap"), base_style(theme),
           frame(width, height, theme)]
    label = f"{esc(source)} · " if source else ""
    out.append(
        f'<text class="h fu" x="16" y="30">{label}{esc(compact(total))} tokens '
        f'in the last year</text>'
    )
    out.append(
        f'<text class="sub fu" x="{width - 16}" y="30" text-anchor="end">'
        f'{active} active days · peak {esc(compact(max(values) if values else 0))}/day</text>'
    )

    grid, grid_left, grid_right = grid_block(values, start, end_date, uid, ramp, width, top)
    out.append(grid)

    foot_y = top + 7 * PITCH + 22
    out.append(
        f'<text class="foot" x="{grid_left}" y="{foot_y}">'
        f'Reported usage units, not a bill</text>'
    )
    out.append(legend(grid_right - 152, foot_y, ramp))
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：提示日历


def card_calendar(summary: dict[str, Any], end_date: date, theme: Theme,
                  source: str | None = None) -> str:
    """提示日历。覆盖期比 token 热力图长：会话记录被清理后 token 不可考，
    但提示时间戳留着，所以这张能一路回溯到最早的使用记录。

    数的是「你敲了多少条提示」，和哪个模型作答无关 —— 提示历史里没有模型字段。
    标题必须写清覆盖哪些工具，否则读者无从判断这个数是全量还是某一个工具的。
    """
    uid = f"k{theme.name}{(source or 'all').replace('-', '')}"
    width, height = CARD_WIDTH, 192
    top = 60

    if source:
        calendar = (summary.get("prompt_calendar_by_source") or {}).get(source, {})
        scope = source
        ramp = tool_ramp(source, sorted(summary.get("sources", {})), theme)
    else:
        calendar = summary.get("prompt_calendar") or {}
        scope = " + ".join(summary.get("prompt_sources") or {}) or "all tools"
        ramp = ramp_for(PRIMARY_RAMP, theme)
    if not calendar:
        return ""
    start = date.fromisoformat(min(calendar))
    start -= timedelta(days=(start.weekday() + 1) % 7)
    days = (end_date - start).days + 1
    values = [calendar.get((start + timedelta(days=i)).isoformat(), 0) for i in range(days)]
    active = sum(1 for value in values if value > 0)

    out = [open_svg(width, height, "Prompt calendar"), base_style(theme),
           frame(width, height, theme)]
    out.append(
        f'<text class="h fu" x="16" y="30">{sum(calendar.values()):,} prompts '
        f'since {esc(min(calendar))}</text>'
    )
    out.append(
        f'<text class="sub fu" x="{width - 16}" y="30" text-anchor="end">'
        f'{esc(scope)} · {active} active days</text>'
    )

    grid, grid_left, grid_right = grid_block(values, start, end_date, uid, ramp, width, top)
    out.append(grid)

    foot_y = top + 7 * PITCH + 22
    out.append(
        f'<text class="foot" x="{grid_left}" y="{foot_y}">'
        f'Prompts you sent, any model · timestamps only, no content read</text>'
    )
    out.append(legend(grid_right - 152, foot_y, ramp))
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：模型榜


def card_models(summary: dict[str, Any], theme: Theme, source: str | None = None) -> str:
    uid = f"d{theme.name}"
    width, height = HALF_WIDTH, 240
    out = [open_svg(width, height, "Top models"), base_style(theme),
           frame(width, height, theme)]
    heading = f"Models · {source}" if source else "Models used"
    out.append(f'<text class="h fu" x="16" y="30">{esc(heading)}</text>')
    out.append(divider(width, 44, theme))

    if source:
        by_model = (summary.get("models_by_source") or {}).get(source, {})
        ranked = sorted(by_model.items(), key=lambda item: -item[1])
    else:
        ranked = list(summary.get("top_models", []))
    models = ranked[:6]
    if not models:
        out.append(f'<text class="sub" x="16" y="72">No model data yet</text>')
        return "".join(out) + "</svg>"

    peak = max(value for _, value in models)
    grand = sum(value for _, value in ranked) or 1
    top, row_height, bar_left = 68, 27, 16
    bar_width = width - 32

    for index, (name, value) in enumerate(models):
        y = top + index * row_height
        length = max(3.0, bar_width * value / peak)
        out.append(
            f'<g class="fu" style="animation-delay:{.08 + index * .05:.2f}s">'
            f'<text class="lab" x="{bar_left}" y="{y}" fill="{theme.fg}">'
            f'{esc(clip(name, 22))}</text>'
            f'<text class="lab" x="{bar_left + bar_width}" y="{y}" text-anchor="end">'
            f'{esc(compact(value))} · {value / grand * 100:.0f}%</text>'
            f'<rect x="{bar_left}" y="{y + 5}" width="{bar_width}" height="6" rx="3" '
            f'fill="{theme.subtle}"/>'
            f'<rect class="gw" style="animation-delay:{.12 + index * .06:.2f}s" '
            f'x="{bar_left}" y="{y + 5}" width="{length:.1f}" height="6" rx="3" '
            f'fill="{theme.accents[index % len(theme.accents)]}"/></g>'
        )

    out.append(divider(width, height - 30, theme))
    out.append(
        f'<text class="foot" x="16" y="{height - 12}">'
        f'{len(ranked)} distinct models across all sessions</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：终端


def card_terminal(summary: dict[str, Any], theme: Theme, title: str) -> str:
    """终端风格总览。主页现在只靠这张卡承载 token 口径，所以原「工具占比」卡
    （含 cached/output 拆分）和「模型榜」卡的信息都搬了进来，图形条换成字符条，
    保持终端的观感。
    """
    char = 7.35  # 12.5px 等宽字体的近似字宽，用于列对齐
    left, top, line_height = 22, 62, 20
    width = CARD_WIDTH
    bar_cols = 24  # 字符条的格数，工具条和模型条同宽便于横向比较

    tools = sorted(summary.get("sources", {}))
    sources = sorted(summary.get("sources", {}).items(), key=lambda item: -item[1])
    grand = sum(value for _, value in sources) or 1
    models = list(summary.get("top_models", []))[:6]
    model_grand = sum(value for _, value in summary.get("top_models", [])) or 1
    model_peak = max((value for _, value in models), default=0) or 1

    def bar(fraction: float) -> str:
        filled = max(1, round(fraction * bar_cols))
        return "█" * filled + "░" * (bar_cols - filled)

    lines: list[list[tuple[float, str, str]]] = [
        [(0, "$", theme.accents[0]), (2, "profile stats --since ", theme.fg),
         (24, str(summary.get("first_date") or "—"), theme.accents[1])],
        [],
        [(2, "total tokens", theme.muted), (22, compact(summary["total_tokens"]), theme.fg),
         (34, "reported usage units", theme.faint)],
        [(2, "active days", theme.muted), (22, str(summary["active_days"]), theme.fg),
         (34, f"{summary.get('first_date') or '—'} → {summary.get('last_date') or '—'}",
          theme.faint)],
        [(2, "sessions", theme.muted), (22, f"{summary['sessions']:,}", theme.fg),
         (34, f"{compact(summary['turns'])} turns", theme.faint)],
        [(2, "cached in", theme.muted), (22, compact(summary["cache_read_tokens"]), theme.fg),
         (34, f"output {compact(summary['output_tokens'])}", theme.faint)],
        [],
        [(2, "# by tool", theme.faint)],
    ]
    # 工具条用它在分工具热力图里的同一色相，读者在折叠区看到的是同一种颜色
    for name, value in sources[:3]:
        lines.append([
            (2, clip(name, 16), theme.muted),
            (22, compact(value), theme.fg),
            (34, f"{value / grand * 100:5.1f}%", theme.faint),
            (44, bar(value / grand), tool_ramp(name, tools, theme)[4]),
        ])
    lines.append([])
    lines.append([(2, "# top models", theme.faint)])
    for index, (name, value) in enumerate(models):
        lines.append([
            (2, clip(name, 18), theme.muted),
            (22, compact(value), theme.fg),
            (34, f"{value / model_grand * 100:5.1f}%", theme.faint),
            (44, bar(value / model_peak), theme.accents[index % len(theme.accents)]),
        ])
    if not models:
        lines.append([(2, "no model data yet", theme.faint)])
    lines.append([])
    lines.append([(0, "$", theme.accents[0])])

    # 高度随行数走，工具数量变化时底部留白保持一致
    height = top + (len(lines) - 1) * line_height + 24
    out = [open_svg(width, height, "Terminal summary"), base_style(theme),
           frame(width, height, theme)]

    out.append(
        f'<path d="M0 6a6 6 0 0 1 6-6h{width - 12}a6 6 0 0 1 6 6v28H0z" fill="{theme.subtle}"/>'
        f'<line x1="0" y1="34" x2="{width}" y2="34" stroke="{theme.border}"/>'
    )
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{20 + index * 16}" cy="17" r="5" fill="{color}"/>')
    out.append(
        f'<text class="mono" x="{width / 2}" y="21" text-anchor="middle" font-size="11" '
        f'fill="{theme.faint}">{esc(title.lower().replace(" ", "-"))} — zsh</text>'
    )

    for index, segments in enumerate(lines):
        if not segments:
            continue
        y = top + index * line_height
        spans = "".join(
            f'<tspan x="{left + column * char:.1f}" fill="{color}">{esc(text)}</tspan>'
            for column, text, color in segments
        )
        out.append(
            f'<text class="mono fu" style="animation-delay:{.05 + index * .04:.2f}s" '
            f'y="{y}" font-size="12.5" xml:space="preserve">{spans}</text>'
        )
    cursor_y = top + (len(lines) - 1) * line_height
    out.append(
        f'<rect class="cur" x="{left + 2 * char:.1f}" y="{cursor_y - 10}" width="8" '
        f'height="13" fill="{theme.fg}" opacity=".85"/>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- HTML 报告


# 主页图集顺序；stats/models 已并入终端卡，全量热力图只留给本地报告
CARD_ORDER = ("heatmap", "calendar", "terminal")


def report_html(title: str, subtitle: str, cards: dict[str, str],
                summary: dict[str, Any]) -> str:
    """本地交互报告。这里能跑 JS，所以按工具筛选做成真按钮 —— README 里做不到。

    卡片用 <img> 外链而不是内联：SVG 的 <style> 一旦内联进 HTML 就会提升到文档
    作用域，多份同名规则互相覆盖，最后一份主题会赢。
    """
    tools = sorted(summary.get("sources", {}))

    def grid_for(theme: str) -> str:
        blocks = []
        for name in CARD_ORDER:
            if f"{name}-{theme}" in cards:
                blocks.append(
                    f'<figure class="card" data-tool="all">'
                    f'<img src="{name}-{theme}.svg" alt="{esc(name)}"></figure>'
                )
        for tool in tools:
            for name in ("heatmap", "calendar", "models"):
                key = f"{name}-{tool}-{theme}"
                if key in cards:
                    blocks.append(
                        f'<figure class="card" data-tool="{esc(tool)}">'
                        f'<img src="{key}.svg" alt="{esc(name)} {esc(tool)}"></figure>'
                    )
        return "".join(blocks)

    buttons = "".join(
        f'<button data-filter="{esc(tool)}">{esc(tool)}</button>'
        for tool in tools
    )
    model_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{value:,}</td></tr>"
        for name, value in summary.get("top_models", [])
    )
    return f"""<!doctype html>
<html lang="en" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root{{--bg:#010409;--fg:#f0f6fc;--muted:#9198a1;--line:#3d444d;--panel:#0d1117;--accent:#3fb950}}
[data-theme=light]{{--bg:#f6f8fa;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--panel:#fff;--accent:#1a7f37}}
*{{box-sizing:border-box}}
body{{margin:0;padding:40px 24px 72px;background:var(--bg);color:var(--fg);
font-family:{FONT};transition:background .2s,color .2s}}
.wrap{{max-width:940px;margin:0 auto}}
header{{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;
flex-wrap:wrap;margin-bottom:20px}}
h1{{font-size:20px;margin:0 0 4px;font-weight:600}}
p.sub{{margin:0;color:var(--muted);font-size:13px}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:22px}}
button{{background:var(--panel);color:var(--fg);border:1px solid var(--line);
border-radius:6px;padding:6px 12px;font-size:12.5px;font-weight:500;cursor:pointer;
font-family:inherit}}
button:hover{{border-color:var(--muted)}}
button[aria-pressed=true]{{border-color:var(--accent);color:var(--accent)}}
button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.grid{{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}}
.card{{margin:0;line-height:0}}
.card[hidden]{{display:none}}
.card img{{max-width:100%;height:auto;display:block}}
[data-theme=dark] .light-set,[data-theme=light] .dark-set{{display:none}}
table{{border-collapse:collapse;width:100%;margin-top:10px;font-size:13px}}
td,th{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}}
th{{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;
letter-spacing:.06em}}
section{{border:1px solid var(--line);border-radius:6px;padding:18px 20px;margin-top:24px;
background:var(--panel)}}
h2{{font-size:14px;margin:0;font-weight:600}}
@media (prefers-reduced-motion:reduce){{*{{transition-duration:.001ms!important}}}}
</style></head><body><div class="wrap">
<header><div><h1>{esc(title)}</h1><p class="sub">{esc(subtitle)} · {esc(summary.get('first_date') or '—')} → {esc(summary.get('last_date') or '—')}</p></div>
<button id="theme">Toggle theme</button></header>
<div class="bar"><button data-filter="all" aria-pressed="true">All tools</button>{buttons}</div>
<div class="grid dark-set">{grid_for('dark')}</div>
<div class="grid light-set">{grid_for('light')}</div>
<section><h2>Models</h2><table><tr><th>Model</th><th>Tokens</th></tr>{model_rows}</table></section>
</div>
<script>
document.getElementById('theme').onclick = () => {{
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
}};
for (const button of document.querySelectorAll('[data-filter]')) {{
  button.onclick = () => {{
    const want = button.dataset.filter;
    for (const other of document.querySelectorAll('[data-filter]'))
      other.setAttribute('aria-pressed', String(other === button));
    for (const card of document.querySelectorAll('.card'))
      card.hidden = want !== 'all' && card.dataset.tool !== want;
  }};
}}
</script>
</body></html>
"""


# ---------------------------------------------------------------- 编排


# README 只用到宽度；高度记在这里便于查阅（terminal 的高度随行数浮动）
CARD_SIZES = {
    "heatmap": (CARD_WIDTH, 192),
    "calendar": (CARD_WIDTH, 192),
    "models": (HALF_WIDTH, 240),  # 分工具折叠区仍在用
    "terminal": (CARD_WIDTH, 470),
}


def build_cards(daily: dict[str, dict[str, Any]], summary: dict[str, Any],
                title: str, subtitle: str, window_days: int) -> dict[str, str]:
    """为每个主题生成全部卡片，键名形如 `heatmap-dark` / `heatmap-codex-dark`。"""
    end_date = (
        date.fromisoformat(summary["last_date"]) if summary.get("last_date") else date.today()
    )
    tools = sorted(summary.get("sources", {}))

    cards: dict[str, str] = {}
    for theme in THEMES:
        cards[f"heatmap-{theme.name}"] = card_heatmap(
            daily, end_date, window_days, summary, theme
        )
        calendar = card_calendar(summary, end_date, theme)
        if calendar:
            cards[f"calendar-{theme.name}"] = calendar
        cards[f"terminal-{theme.name}"] = card_terminal(summary, theme, title)
        # 分工具变体：README 用 <details> 折叠展示，本地报告用按钮切换
        for tool in tools:
            cards[f"heatmap-{tool}-{theme.name}"] = card_heatmap(
                daily, end_date, window_days, summary, theme, source=tool
            )
            cards[f"models-{tool}-{theme.name}"] = card_models(summary, theme, source=tool)
            tool_calendar = card_calendar(summary, end_date, theme, source=tool)
            if tool_calendar:
                cards[f"calendar-{tool}-{theme.name}"] = tool_calendar
    return cards
