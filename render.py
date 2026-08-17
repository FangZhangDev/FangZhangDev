#!/usr/bin/env python3
"""渲染层：把聚合结果画成可嵌入 GitHub README 的 SVG 卡片。

卡片是贴在 GitHub 页面上的，所以底色、边框、圆角、字号、方格几何、月份刻度和
Less/More 图例都跟随 GitHub Primer，免得看起来像外来物。但色相另选：这里量的
是 token 和提示数而不是 commit，沿用贡献图的绿会让人误读成提交量。

渲染约束（GitHub 通过 <img> + camo 代理渲染 SVG）：
- 不执行 JavaScript，不加载外部字体，只能用系统字体栈；
- <title> 提示框不生效，所有信息必须画在图上；
- 不做入场动画：卡片会被反复滚动到，每次重放淡入只会碍事，且 GitHub 的 camo
  代理下动画时机本就不可控。唯一的动态是终端卡光标，且尊重 prefers-reduced-motion；
- 等宽字体在各平台字宽不同（SF Mono 0.6em / Consolas 0.55em），所以占比条一律
  用 <rect> 画，绝不用 █░ 字符拼——字符条在 Windows 上会错位；
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
    accents: tuple[str, ...]  # 终端卡的提示符与日期，取自 Tailwind Violet / Purple


# 方格的几何、月份刻度、Less/More 图例都照搬 GitHub，但色相刻意避开贡献图的绿：
# 这里量的是 token 和提示数，不是 commit，撞色只会让人误读。
DARK = Theme(
    name="dark",
    canvas="#0d1117",
    subtle="#151b23",
    border="#3d444d",
    fg="#f0f6fc",
    muted="#9198a1",
    faint="#6e7681",
    # 终端卡的提示符和日期。也收进紫色系，否则一屏紫里冒出一句蓝色的日期很跳
    accents=("#a78bfa", "#c4b5fd"),  # violet-400 / 300
)

LIGHT = Theme(
    name="light",
    canvas="#ffffff",
    subtle="#f6f8fa",
    border="#d1d9e0",
    fg="#1f2328",
    muted="#59636e",
    faint="#818b98",
    accents=("#7c3aed", "#9333ea"),  # violet-600 / purple-600
)

THEMES = (DARK, LIGHT)

# 整套分类色收进 Tailwind 的 Violet / Purple 色阶，不再一个工具一个色相。工具之间
# 靠明度拉开（claude-code 深、codex 浅），而不是靠冷暖对立，这样同一页上不会出现
# 青配粉这种互不相干的组合。绿色仍然留给 GitHub 真正的贡献图，不参与分配。
#
# 亮色主题不能直接用暗色那一档：#c084fc 铺在白底上对比度只有 2.6:1，达不到图形
# 元素 3:1 的下限，条会糊掉。所以每个色相在亮色侧统一往深处挪一到两级，明暗关系
# （谁深谁浅）保持不变。
HUES: dict[str, tuple[str, str]] = {  # 名称 -> (暗色主题, 亮色主题)
    "violet": ("#8b5cf6", "#7c3aed"),   # violet-500 / 600
    "purple": ("#c084fc", "#a855f7"),   # purple-400 / 500
    "indigo": ("#818cf8", "#6366f1"),   # indigo-400 / 500
    "fuchsia": ("#e879f9", "#c026d3"),  # fuchsia-400 / 600
    "plum": ("#a78bfa", "#8b5cf6"),     # violet-400 / 500
    "orchid": ("#d8b4fe", "#9333ea"),   # purple-300 / 600
}

# 网格最低一级用 GitHub 贡献图的空格底色，往上向纯色相插值，节奏和贡献图一致：
# 低强度很淡、高强度饱和。四个刻度的插值位置照搬 Primer 的观感。
GRID_BASE = {"dark": "#161b22", "light": "#ebedf0"}
RAMP_STOPS = (0.35, 0.55, 0.75, 1.0)

PRIMARY_RAMP = "violet"
# 分工具色相按工具名排序依次取用：claude-code 在前拿 violet（深紫），codex 拿
# purple（浅紫）。后面几个留给以后接入的 agent，都在同一片紫里，加进来不会突兀。
TOOL_RAMPS = ("violet", "purple", "indigo", "fuchsia", "plum", "orchid")

# 模型榜的排名梯度，沿 Tailwind Violet 色阶铺开。亮色主题按字面来：第一名最深，
# 往下依次变浅。暗色主题必须反过来 —— 深紫压在 #0d1117 上几乎看不见，第一名反而
# 成了最不显眼的一行。两边的实际效果一致：排名越靠前，和背景的对比越强。
#
# 两端不能取满色阶。图形元素的可读下限是 3:1，实测在 #0d1117 上只有 violet-200
# 到 600 达标，在 #ffffff 上只有 500 到 900 达标；越界的话末几名的条会糊进背景。
# 所以每个主题各取自己那段安全区的两头。
MODEL_RANK = {
    "dark": ("#c4b5fd", "#7c3aed"),   # violet-300 → 600
    "light": ("#6d28d9", "#8b5cf6"),  # violet-700 → 500
}

# 终端卡的模型条按名次逐行取色，不再是单色相的明暗渐变 ——「薰衣草与玫瑰」：
# 薰衣草 → 品红 → 玫红 → 淡品红 → 淡紫 → 玫瑰 → 银 → 灰蓝。
#
# 前半段留在头像那条紫色阶里，中段转暖到品红/玫瑰拉开单调，末两名淡出成中性银灰。
# 关键是让「淡出」由彩度承担而不是继续堆紫：八行全是同一个色相的明暗变化，读起来
# 就是一片紫，这是原先那版的问题。
#
# 亮色那一列不是暗色的复制。实测只有 Tailwind 的 500/600 两档在黑白两种底色上都
# 安全：300/400 在白底跌破 3:1（#cbd5e1 只剩 1.5:1，等于白底上的白），700 在近黑
# 底也跌破。所以两个主题各配一档，名次顺序和冷暖走向保持一致。
# #7c8ba1 是 slate-400 与 500 之间的自定值，白底 3.5:1 —— 整套里最低的一处。
TERMINAL_MODEL_COLORS = {
    "dark": ("#a78bfa", "#c084fc", "#e879f9", "#f0abfc",
             "#c4b5fd", "#fda4af", "#cbd5e1", "#94a3b8"),
    "light": ("#7c3aed", "#9333ea", "#c026d3", "#d946ef",
              "#8b5cf6", "#e11d48", "#64748b", "#7c8ba1"),
}


def ramp_for(name: str, theme: Theme) -> tuple[str, ...]:
    """按色相名生成五级梯度。改成算出来而不是手写死值，加新色相只要往 HUES 里
    添一行 —— 每接入一个新 agent 就要多一个可辨认的色相。"""
    hue = HUES.get(name, HUES[PRIMARY_RAMP])
    target = hue[0] if theme.name == "dark" else hue[1]
    base = GRID_BASE[theme.name]
    return (base,) + tuple(lerp_hex(base, target, stop) for stop in RAMP_STOPS)


def tool_ramp(tool: str, tools: Sequence[str], theme: Theme) -> tuple[str, ...]:
    index = list(tools).index(tool) if tool in tools else 0
    return ramp_for(TOOL_RAMPS[index % len(TOOL_RAMPS)], theme)


def lerp_hex(start: str, end: str, fraction: float) -> str:
    """两色之间做线性插值，用于给排名条生成同族渐变。"""
    a = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
    mixed = [round(x + (y - x) * fraction) for x, y in zip(a, b)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def rank_colors(theme: Theme, count: int) -> list[str]:
    """排名条的渐变色，沿 Tailwind Violet 色阶铺开，第 1 名对比最强。

    排名是有序数据，用同一色相的明度渐变比每行换一个色相耐看得多，也不会让读者
    误以为颜色编码了别的含义。两端见 MODEL_RANK。
    """
    start, end = MODEL_RANK[theme.name]
    if count <= 1:
        return [start]
    return [lerp_hex(start, end, index / (count - 1)) for index in range(count)]

# GitHub 贡献图的方格比例：10px 方块、3px 间距、2px 圆角。
# 这里放大到 12px 以填满 880 宽的卡片，比例保持不变。
CELL, GAP, RADIUS = 12, 3, 2
PITCH = CELL + GAP

CARD_WIDTH = 880
HALF_WIDTH = 440  # 两张并排刚好等于一张整宽，README 里两行才能左右对齐

# 终端卡的模型行数上限。这张卡在主页，行数不设限的话模型攒多了会把它拉得老长；
# 折叠区的模型卡则不限，能上榜的都列出来。
TERMINAL_MODEL_ROWS = 8


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
    """共用排版。字号跟随 GitHub：正文 14px，辅助 12px，刻度 10px。

    卡片不做入场动画：这些图会被嵌进 README 和报告里反复浏览，每次滚动到都重放
    一遍淡入/拉伸只会碍事。唯一保留的动态是终端卡的光标闪烁，且在系统开启
    prefers-reduced-motion 时也会停下。
    """
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
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".cur{animation:blink 1.1s step-end infinite}"
        "@media (prefers-reduced-motion:reduce){.cur{animation:none}}"
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


# ---------------------------------------------------------------- 占比条


# 一个格子的宽度，沿用当初 █░ 字符条在 12.5px 等宽字体下的字宽
BAR_CELL = 7.35
BAR_COLS = 24  # 格数也照搬字符条
BAR_HEIGHT = 11


def meter(uid: str, x: float, y: float, fraction: float, color: str, faint: str,
          cols: int = BAR_COLS, height: float = BAR_HEIGHT) -> str:
    """█████░░░░░░ 形态的占比条，但用 <rect> + <pattern> 画。

    字符条的长度由浏览器实际选中的等宽字体决定（Mac 命中 SF Mono，字宽 0.6em；
    Windows 命中 Consolas，0.55em），24 格累积下来差十几像素；Windows 还会把 █ 和
    ░ 拆成两个 shaping run 各自做像素对齐，接缝处肉眼可见地错开。这里两段都按算
    出来的坐标画：实心段是一个矩形，点阵段是一个填了 pattern 的矩形，严丝合缝，
    任何平台上都是同一个像素结果。

    uid 必须在同一份 SVG 内唯一 —— pattern 是靠 id 引用的。
    """
    width = cols * BAR_CELL
    filled = max(1, round(fraction * cols))  # 再小的占比也点亮一格，否则看着像没画
    lit = width * filled / cols
    return (
        f'<defs><pattern id="{uid}" width="3" height="3" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.5" cy="1.5" r=".75" fill="{faint}"/></pattern></defs>'
        f'<rect x="{x:.2f}" y="{y}" width="{lit:.2f}" height="{height}" fill="{color}"/>'
        f'<rect x="{x + lit:.2f}" y="{y}" width="{width - lit:.2f}" '
        f'height="{height}" fill="url(#{uid})"/>'
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

    parts = [
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
            f'<use href="#{uid}c" x="{left + column * PITCH}" '
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
        f'<text class="h" x="16" y="30">{label}{esc(compact(total))} tokens '
        f'in the last year</text>'
    )
    out.append(
        f'<text class="sub" x="{width - 16}" y="30" text-anchor="end">'
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


def profile_years(first: date, last: date) -> list[tuple[date, date]]:
    """把使用历史切成以首个提示日为锚的「档案年」，最早的在前。

    锚点用首个提示日而不是自然年 1 月 1 日：这样第一段一定是满的，不会开局就是
    半张残缺的格子。每段是 [锚点, 下一个锚点)，跨闰年也正好一年。

    为什么必须切段：网格宽度 = 列数 × 15px，而「从头铺到今天」的列数每周 +1、
    没有上限，880 宽的卡片撑到第 56 列就画到视口外面去了。按年切之后每段恒定
    53 列、右边界 836，和 token 热力图一样，永远画得下。
    """
    spans: list[tuple[date, date]] = []
    start = first
    while start <= last:
        try:
            nxt = start.replace(year=start.year + 1)
        except ValueError:  # 2 月 29 日锚点，退到 2 月 28 日
            nxt = start.replace(year=start.year + 1, day=28)
        spans.append((start, min(nxt - timedelta(days=1), last)))
        start = nxt
    return spans


def calendar_key(start: date) -> str:
    """往年日历卡的文件名，如 calendar-2025-09。同一锚点每年只会有一张。"""
    return f"calendar-{start.year}-{start.month:02d}"


def card_calendar(summary: dict[str, Any], end_date: date, theme: Theme,
                  window: tuple[date, date] | None = None) -> str:
    """提示日历。覆盖期比 token 热力图长：会话记录被清理后 token 不可考，
    但提示时间戳留着，所以这张能一路回溯到最早的使用记录。

    数的是「你敲了多少条提示」，和哪个模型作答无关 —— 提示历史里没有模型字段。
    标题必须写清覆盖哪些工具和哪段日期，否则读者无从判断这个数是全量、某个工具，
    还是某一个档案年的。

    window 给定时只画这一段（用于往年那几张）；不给就画包含 end_date 的当前段。
    """
    calendar = summary.get("prompt_calendar") or {}
    if not calendar:
        return ""

    scope = " + ".join(summary.get("prompt_sources") or {}) or "all tools"
    ramp = ramp_for(PRIMARY_RAMP, theme)
    span_start, span_end = window or profile_years(
        date.fromisoformat(min(calendar)), end_date
    )[-1]

    uid = f"k{theme.name}{span_start.year}{span_start.month:02d}"
    width, height = CARD_WIDTH, 192
    top = 60

    start = span_start - timedelta(days=(span_start.weekday() + 1) % 7)  # 对齐到周日
    days = (span_end - start).days + 1
    values = [calendar.get((start + timedelta(days=i)).isoformat(), 0) for i in range(days)]
    # 统计只算档案年区间内的日子，别把周日对齐补进来的那几天算进去
    inside = [v for d, v in ((start + timedelta(days=i), values[i]) for i in range(days))
              if d >= span_start]
    total, active = sum(inside), sum(1 for value in inside if value > 0)

    out = [open_svg(width, height, "Prompt calendar"), base_style(theme),
           frame(width, height, theme)]
    out.append(
        f'<text class="h" x="16" y="30">{total:,} prompts '
        f'&#183; {esc(span_start.isoformat())} → {esc(span_end.isoformat())}</text>'
    )
    out.append(
        f'<text class="sub" x="{width - 16}" y="30" text-anchor="end">'
        f'{esc(scope)} · {active} active days</text>'
    )

    grid, grid_left, grid_right = grid_block(values, start, span_end, uid, ramp, width, top)
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
    """模型榜。这张卡在折叠区里，不封顶行数 —— 能上榜的都列出来，卡片跟着长高。

    高度必须算出来而不是写死：原先固定 240 高、脚注分隔线钉在 height-30，六行时
    最后一条占 y 208–214，分隔线正好落在 210，从条中间穿过去。行数一放开只会更糟。
    """
    width, bar_left = HALF_WIDTH, 16
    bar_width = width - 32
    top, row_height = 68, 27
    heading = f"Models · {source}" if source else "Models used"

    if source:
        by_model = (summary.get("models_by_source") or {}).get(source, {})
        ranked = sorted(by_model.items(), key=lambda item: -item[1])
    else:
        ranked = list(summary.get("top_models", []))

    if not ranked:
        height = 110
        return "".join([
            open_svg(width, height, "Top models"), base_style(theme),
            frame(width, height, theme),
            f'<text class="h" x="16" y="30">{esc(heading)}</text>',
            divider(width, 44, theme),
            '<text class="sub" x="16" y="72">No model data yet</text>',
        ]) + "</svg>"

    # 最后一行的条底 + 留白 → 分隔线 → 脚注 → 下边距
    bottom = top + (len(ranked) - 1) * row_height + 11
    divider_y = bottom + 16
    foot_y = divider_y + 18
    height = foot_y + 12

    out = [open_svg(width, height, "Top models"), base_style(theme),
           frame(width, height, theme),
           f'<text class="h" x="16" y="30">{esc(heading)}</text>',
           divider(width, 44, theme)]

    # 条长和标签用同一个分母（全部模型的 token 总和），否则第一名总是画满，
    # 和它旁边写的 36% 对不上，读者只能猜条代表什么。
    grand = sum(value for _, value in ranked) or 1
    bars = rank_colors(theme, len(ranked))

    # 这里用干净的圆角条，不用终端卡那种点阵条：█░ 的颗粒感是终端的语言，
    # 放到图表卡上只是噪点。同一份数据在两处各说各的话，反而更清楚。
    for index, (name, value) in enumerate(ranked):
        y = top + index * row_height
        length = max(2.0, bar_width * value / grand)
        out.append(
            f'<text class="lab" x="{bar_left}" y="{y}" fill="{theme.fg}">'
            f'{esc(clip(name, 22))}</text>'
            f'<text class="lab" x="{bar_left + bar_width}" y="{y}" text-anchor="end">'
            f'{esc(compact(value))} · {value / grand * 100:.0f}%</text>'
            f'<rect x="{bar_left}" y="{y + 5}" width="{bar_width}" height="6" rx="3" '
            f'fill="{theme.subtle}"/>'
            f'<rect x="{bar_left}" y="{y + 5}" width="{length:.1f}" height="6" rx="3" '
            f'fill="{bars[index]}"/>'
        )

    out.append(divider(width, divider_y, theme))
    out.append(
        f'<text class="foot" x="16" y="{foot_y}">'
        f'{len(ranked)} distinct models · bar length = share of all model tokens</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：终端


def card_terminal(summary: dict[str, Any], theme: Theme, title: str) -> str:
    """终端风格总览。主页现在只靠这张卡承载 token 口径，所以原「工具占比」卡
    （含 cached/output 拆分）和「模型榜」卡的信息都搬了进来。

    两组的表现方式是有意不同的：

    - # by tool 只有两三行，是「整体怎么分」的问题，占比条最直观，所以保留；
    - # top models 有八行，八条并排会把这张卡压得很满。这里改成给模型名上色、
      不画条，量级交给右边的数字和百分比。颜色在这一组只负责区分名次，不编码大小。

    占比条见 meter()：形态还是 █████░░░░░░，但用 rect + pattern 画，格数和格宽
    都照搬当初的字符条（24 格 × 7.35px），所以观感一致而不受字体影响。
    """
    char = BAR_CELL  # 12.5px 等宽字体的近似字宽，只用于文字列的起始位置
    left, top, line_height = 22, 62, 20
    width = CARD_WIDTH
    bar_x = left + 44 * char  # 占比条从第 44 列起，占 24 格，和原来的字符条同宽

    tools = sorted(summary.get("sources", {}))
    sources = sorted(summary.get("sources", {}).items(), key=lambda item: -item[1])
    grand = sum(value for _, value in sources) or 1
    # 终端卡封顶 10 行：这张卡在主页上，模型攒多了会把它拉得很长。分母仍然是全部
    # 模型的总和，所以百分比是「占全部用量」，落榜的那些只是不显示，不影响读数。
    ranked_models = list(summary.get("top_models", []))
    models = ranked_models[:TERMINAL_MODEL_ROWS]
    model_grand = sum(value for _, value in ranked_models) or 1

    # 行号 -> (占比, 颜色)。两组条都以「占各自总量的比例」为长度，和同一行写的
    # 百分比是同一个数，避免出现「36% 却画满格」这种要靠猜的读法。
    bars: dict[int, tuple[float, str]] = {}

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
        bars[len(lines)] = (value / grand, tool_ramp(name, tools, theme)[4])
        lines.append([
            (2, clip(name, 16), theme.muted),
            (22, compact(value), theme.fg),
            (34, f"{value / grand * 100:5.1f}%", theme.faint),
        ])
    lines.append([])
    lines.append([(2, "# top models", theme.faint)])
    # 名次配色落在模型名上，不画条。折叠区的模型卡仍用 rank_colors 的单色相渐变
    palette = TERMINAL_MODEL_COLORS[theme.name]
    for index, (name, value) in enumerate(models):
        lines.append([
            (2, clip(name, 18), palette[index]),
            (22, compact(value), theme.fg),
            (34, f"{value / model_grand * 100:5.1f}%", theme.faint),
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
            f'<text class="mono" y="{y}" font-size="12.5" '
            f'xml:space="preserve">{spans}</text>'
        )
        if index in bars:
            fraction, color = bars[index]
            out.append(meter(f"t{theme.name}{index}", bar_x, y - 9, fraction,
                             color, theme.faint))
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
            for name in ("heatmap", "models"):
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
:root{{--bg:#010409;--fg:#f0f6fc;--muted:#9198a1;--line:#3d444d;--panel:#0d1117;--accent:#cba6f7}}
[data-theme=light]{{--bg:#f6f8fa;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--panel:#fff;--accent:#8839ef}}
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

    # 提示日历按「档案年」切段：当前段上主页，往年的进 README 的折叠区。
    # 不切的话网格每周多一列，880 宽的卡片撑到第 56 列就画到视口外面去了。
    calendar_days = summary.get("prompt_calendar") or {}
    spans = (profile_years(date.fromisoformat(min(calendar_days)), end_date)
             if calendar_days else [])
    summary["calendar_spans"] = [
        {"key": calendar_key(start), "start": start.isoformat(), "end": end.isoformat()}
        for start, end in spans
    ]

    cards: dict[str, str] = {}
    for theme in THEMES:
        cards[f"heatmap-{theme.name}"] = card_heatmap(
            daily, end_date, window_days, summary, theme
        )
        for index, span in enumerate(spans):
            # 最后一段是「当前档案年」，占主页那张 calendar；其余按年份命名
            name = "calendar" if index == len(spans) - 1 else calendar_key(span[0])
            cards[f"{name}-{theme.name}"] = card_calendar(
                summary, end_date, theme, window=span
            )
        cards[f"terminal-{theme.name}"] = card_terminal(summary, theme, title)
        # 分工具变体：README 用 <details> 折叠展示，本地报告用按钮切换
        for tool in tools:
            cards[f"heatmap-{tool}-{theme.name}"] = card_heatmap(
                daily, end_date, window_days, summary, theme, source=tool
            )
            cards[f"models-{tool}-{theme.name}"] = card_models(summary, theme, source=tool)
    return cards
