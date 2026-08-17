#!/usr/bin/env python3
"""渲染层：把聚合结果画成多种可嵌入 GitHub README 的 SVG 卡片。

设计约束（GitHub 通过 <img> + camo 代理渲染 SVG）：
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


FONT = "ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,'Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


@dataclass(frozen=True)
class Theme:
    """一套完整配色。dark 为 Nocturne，light 为 Daylight。"""

    name: str
    bg: str  # 卡片底色（渐变起点）
    bg2: str  # 卡片底色（渐变终点）
    panel: str  # 内嵌面板底色
    border: str
    text: str
    dim: str  # 次要文字
    muted: str  # 三级文字 / 刻度
    grid: str  # 网格线、分隔线
    accents: tuple[str, ...]  # 分类色序列
    ramp: tuple[str, str, str, str, str]  # 热力图 0-4 级
    glow: str  # 顶部高光线渐变终点


DARK = Theme(
    name="dark",
    bg="#0b0d13",
    bg2="#131824",
    panel="#0e121b",
    border="#232a3a",
    text="#e8eef9",
    dim="#98a3b8",
    muted="#5f6b80",
    grid="#1d2433",
    accents=("#5ce6c4", "#7cc5ff", "#a78bfa", "#f0a5d0", "#fbbf6b", "#8de08a"),
    ramp=("#161b26", "#0e3f4d", "#116b7a", "#1aa3a3", "#5ce6c4"),
    glow="#a78bfa",
)

LIGHT = Theme(
    name="light",
    bg="#ffffff",
    bg2="#f4f7fb",
    panel="#f7f9fc",
    border="#dde4ee",
    text="#0d1424",
    dim="#57637a",
    muted="#8994a8",
    grid="#e6ebf3",
    accents=("#0f9b86", "#2b7fd4", "#7c5ae0", "#c4459a", "#c2790f", "#3f9a45"),
    ramp=("#eef1f6", "#c2e8de", "#6fcdb8", "#26a68c", "#0d7361"),
    glow="#7c5ae0",
)

THEMES = (DARK, LIGHT)


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


def smooth_path(points: Sequence[tuple[float, float]]) -> str:
    """用简化 Catmull-Rom 转三次贝塞尔，得到平滑折线。"""
    if not points:
        return ""
    if len(points) < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    parts = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for index in range(len(points) - 1):
        p0 = points[max(index - 1, 0)]
        p1 = points[index]
        p2 = points[index + 1]
        p3 = points[min(index + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        parts.append(
            f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        )
    return "".join(parts)


def base_style(theme: Theme) -> str:
    """所有卡片共用的排版与动画规则。"""
    return (
        "<style>"
        f"text{{font-family:{FONT};dominant-baseline:auto}}"
        f".mono{{font-family:{MONO}}}"
        f".h1{{font-size:27px;font-weight:700;fill:{theme.text};letter-spacing:-.6px}}"
        f".h2{{font-size:14px;font-weight:700;fill:{theme.text};letter-spacing:-.1px}}"
        f".eyebrow{{font-size:9.5px;font-weight:700;fill:{theme.muted};letter-spacing:2.2px}}"
        f".sub{{font-size:12px;fill:{theme.dim}}}"
        f".kpi{{font-size:23px;font-weight:700;fill:{theme.text};letter-spacing:-.5px}}"
        f".kpi-s{{font-size:15px;font-weight:700;fill:{theme.text}}}"
        f".lab{{font-size:9.5px;font-weight:600;fill:{theme.muted};letter-spacing:1px}}"
        f".tick{{font-size:9.5px;fill:{theme.muted}}}"
        f".val{{font-size:11px;font-weight:600;fill:{theme.dim}}}"
        "@keyframes fu{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}"
        "@keyframes po{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:none}}"
        "@keyframes gw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        "@keyframes gy{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
        "@keyframes fi{from{opacity:0}to{opacity:1}}"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".fu{animation:fu .6s cubic-bezier(.22,1,.36,1) both}"
        ".po{animation:po .5s cubic-bezier(.22,1,.36,1) both;transform-box:fill-box;transform-origin:center}"
        ".gw{animation:gw .9s cubic-bezier(.22,1,.36,1) both;transform-box:fill-box;transform-origin:left center}"
        ".gy{animation:gy .9s cubic-bezier(.22,1,.36,1) both;transform-box:fill-box;transform-origin:bottom center}"
        # 只淡入的容器动画：元素自身的 opacity 属性得以保留，两者相乘
        ".fi{animation:fi .5s ease-out both}"
        ".cur{animation:blink 1.1s step-end infinite}"
        "</style>"
    )


def frame(uid: str, width: int, height: int, theme: Theme, radius: int = 16) -> str:
    """卡片外框：斜向底色渐变 + 边框 + 顶部一条彩色高光。"""
    return (
        f'<defs><linearGradient id="{uid}bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{theme.bg}"/><stop offset="1" stop-color="{theme.bg2}"/>'
        f"</linearGradient>"
        f'<linearGradient id="{uid}hl" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{theme.accents[0]}" stop-opacity="0"/>'
        f'<stop offset=".35" stop-color="{theme.accents[0]}"/>'
        f'<stop offset=".7" stop-color="{theme.glow}"/>'
        f'<stop offset="1" stop-color="{theme.glow}" stop-opacity="0"/>'
        f"</linearGradient></defs>"
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="{radius}" '
        f'fill="url(#{uid}bg)" stroke="{theme.border}"/>'
        f'<rect x="{radius}" y="0" width="{width - radius * 2}" height="1.5" '
        f'fill="url(#{uid}hl)" opacity=".9"/>'
    )


def open_svg(width: int, height: int, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">'
    )


def eyebrow(x: float, y: float, text: str, theme: Theme, accent: int = 0) -> str:
    """小标签：一个圆点 + 全大写字距文字。"""
    return (
        f'<circle cx="{x + 3}" cy="{y - 3.5}" r="3" fill="{theme.accents[accent]}"/>'
        f'<text class="eyebrow" x="{x + 13}" y="{y}">{esc(text.upper())}</text>'
    )


# ---------------------------------------------------------------- 卡片：Hero


def card_hero(summary: dict[str, Any], series: list[tuple[str, int]], theme: Theme,
              title: str, subtitle: str) -> str:
    uid = f"h{theme.name}"
    width, height = 880, 218
    out = [open_svg(width, height, title), base_style(theme), frame(uid, width, height, theme)]

    values = [value for _, value in series[-120:]]
    peak = max(values) if values else 1

    # 底部波形基座：用最近 120 天活跃度画平滑面积图，纯装饰
    if values:
        # 振幅压到 44，让波形停在标签条下方，不和文字打架
        left, right, base_y, amp = 1, width - 1, height - 1, 44
        step = (right - left) / max(len(values) - 1, 1)
        points = [
            (left + index * step, base_y - (value / peak) * amp)
            for index, value in enumerate(values)
        ]
        area = smooth_path(points) + f" L{right},{base_y} L{left},{base_y} Z"
        out.append(
            f'<defs><linearGradient id="{uid}wave" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{theme.accents[0]}" stop-opacity=".26"/>'
            f'<stop offset="1" stop-color="{theme.accents[0]}" stop-opacity="0"/>'
            f"</linearGradient>"
            f'<clipPath id="{uid}clip"><rect x="1" y="1" width="{width - 2}" '
            f'height="{height - 2}" rx="15"/></clipPath></defs>'
            f'<g clip-path="url(#{uid}clip)" class="fu" style="animation-delay:.25s">'
            f'<path d="{area}" fill="url(#{uid}wave)"/>'
            f'<path d="{smooth_path(points)}" fill="none" stroke="{theme.accents[0]}" '
            f'stroke-width="1.6" stroke-opacity=".55" stroke-linecap="round"/></g>'
        )

    out.append('<g class="fu">')
    out.append(eyebrow(30, 40, "ai coding profile", theme))
    out.append(f'<text class="h1" x="30" y="76">{esc(title)}</text>')
    span = f"{summary.get('first_date') or '—'}  →  {summary.get('last_date') or '—'}"
    out.append(f'<text class="sub" x="30" y="98">{esc(subtitle)}</text>')
    out.append(f'<text class="sub mono" x="30" y="117" fill="{theme.muted}">{esc(span)}</text>')
    out.append("</g>")

    # 右上四个 KPI，等距排布
    kpis = [
        (compact(summary["total_tokens"]), "TOKENS"),
        (str(summary["active_days"]), "ACTIVE DAYS"),
        (str(summary["sessions"]), "SESSIONS"),
        (compact(summary["turns"]), "TURNS"),
    ]
    x0, gap = 402, 118
    for index, (value, label) in enumerate(kpis):
        x = x0 + index * gap
        out.append(
            f'<g class="fu" style="animation-delay:{.08 + index * .07:.2f}s">'
            f'<text class="kpi" x="{x}" y="76">{esc(value)}</text>'
            f'<text class="lab" x="{x}" y="94">{esc(label)}</text>'
            f'<rect x="{x}" y="103" width="26" height="2" rx="1" '
            f'fill="{theme.accents[index % len(theme.accents)]}" opacity=".8"/></g>'
        )

    # 底部标签条：说明数据来源与隐私边界，不用一句完整句子占位
    chips = ["Claude Code", "Codex", "local-only collector", "no prompts · no paths"]
    x = 30
    for index, chip in enumerate(chips):
        chip_width = len(chip) * 6.4 + 22
        out.append(
            f'<g class="fu" style="animation-delay:{.3 + index * .06:.2f}s">'
            f'<rect x="{x}" y="140" width="{chip_width:.0f}" height="24" rx="12" '
            f'fill="{theme.panel}" stroke="{theme.border}"/>'
            f'<circle cx="{x + 11}" cy="152" r="2.5" '
            f'fill="{theme.accents[index % len(theme.accents)]}"/>'
            f'<text class="val" x="{x + 19}" y="156">{esc(chip)}</text></g>'
        )
        x += chip_width + 8

    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：热力图


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def intensity_levels(values: Iterable[int]) -> dict[int, int]:
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


def card_heatmap(daily: dict[str, dict[str, Any]], end_date: date, window_days: int,
                 summary: dict[str, Any], theme: Theme) -> str:
    uid = f"m{theme.name}"
    width, height = 880, 200
    cell, gap = 11, 3
    pitch = cell + gap

    start = end_date - timedelta(days=window_days - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # 对齐到周日
    days = (end_date - start).days + 1
    columns = math.ceil(days / 7)

    # 网格在卡片内水平居中；星期标签落在左侧留白里
    grid_width = columns * pitch - gap
    left = max(46, round((width - grid_width) / 2))
    top = 74

    values = [
        daily.get((start + timedelta(days=index)).isoformat(), {}).get("total_tokens", 0)
        for index in range(days)
    ]
    levels = intensity_levels(values)

    out = [open_svg(width, height, "Coding activity heatmap"), base_style(theme),
           frame(uid, width, height, theme)]
    # 格子共用一个 <use> 模板，逐列的入场延迟收进 CSS 类里。
    # 直接给 371 个 <rect> 各写一遍尺寸和 inline style 会让文件涨到 44KB。
    delays = "".join(
        f".{uid}d{column}{{animation-delay:{.15 + column * .009:.3f}s}}"
        for column in range(columns)
    )
    out.append(
        f"<style>.{uid}hi{{stroke:{theme.accents[0]};stroke-opacity:.35}}{delays}</style>"
        f'<defs><rect id="{uid}c" width="{cell}" height="{cell}" rx="2.5"/></defs>'
    )
    out.append('<g class="fu">')
    out.append(eyebrow(30, 40, "activity heatmap", theme, 1))
    active = summary["active_days"]
    out.append(
        f'<text class="sub" x="{width - 30}" y="40" text-anchor="end">'
        f'{active} active days · peak {compact(max(values) if values else 0)} tokens/day</text>'
    )
    out.append("</g>")

    # 月份刻度：只在某列的首日跨入新月份时打标
    last_month = None
    for column in range(columns):
        day = start + timedelta(days=column * 7)
        if day > end_date:
            break
        if day.month != last_month:
            last_month = day.month
            x = left + column * pitch
            if x < left + grid_width - 16:
                out.append(f'<text class="tick" x="{x}" y="{top - 8}">{MONTHS[day.month - 1]}</text>')

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        out.append(
            f'<text class="tick" x="{left - 10}" y="{top + row * pitch + 9}" '
            f'text-anchor="end">{label}</text>'
        )

    for index, value in enumerate(values):
        column, row = index // 7, index % 7
        level = levels.get(value, 0)
        classes = f"po {uid}d{column}" + (f" {uid}hi" if level == 4 else "")
        out.append(
            f'<use class="{classes}" href="#{uid}c" x="{left + column * pitch}" '
            f'y="{top + row * pitch}" fill="{theme.ramp[level]}"/>'
        )

    # 右下图例
    legend_x = left + grid_width - 118
    legend_y = top + 7 * pitch + 14
    out.append(f'<text class="tick" x="{legend_x}" y="{legend_y}">Less</text>')
    for level in range(5):
        out.append(
            f'<rect x="{legend_x + 30 + level * 14}" y="{legend_y - 9}" width="11" '
            f'height="11" rx="2.5" fill="{theme.ramp[level]}"/>'
        )
    out.append(f'<text class="tick" x="{legend_x + 105}" y="{legend_y}">More</text>')

    return "".join(out) + "</svg>"


def card_calendar(summary: dict[str, Any], end_date: date, theme: Theme) -> str:
    """提示日历：覆盖期比 token 热力图长得多，指标单一（每日提示条数）。

    Claude Code 删掉会话记录后 token 就不可考了，但提示历史留着，所以这张卡能
    一路回溯到最早的使用记录。刻意和 token 热力图分开，避免一张图混两种口径。
    """
    uid = f"k{theme.name}"
    width, height = 880, 200
    cell, gap = 11, 3
    pitch = cell + gap

    calendar = summary.get("prompt_calendar") or {}
    if not calendar:
        return ""
    start = date.fromisoformat(min(calendar))
    start -= timedelta(days=(start.weekday() + 1) % 7)  # 对齐到周日
    days = (end_date - start).days + 1
    columns = math.ceil(days / 7)

    grid_width = columns * pitch - gap
    left = max(46, round((width - grid_width) / 2))
    top = 74

    values = [
        calendar.get((start + timedelta(days=index)).isoformat(), 0) for index in range(days)
    ]
    levels = intensity_levels(values)

    out = [open_svg(width, height, "Prompt calendar"), base_style(theme),
           frame(uid, width, height, theme)]
    delays = "".join(
        f".{uid}d{column}{{animation-delay:{.15 + column * .008:.3f}s}}"
        for column in range(columns)
    )
    out.append(
        f"<style>{delays}</style>"
        f'<defs><rect id="{uid}c" width="{cell}" height="{cell}" rx="2.5"/></defs>'
    )
    out.append('<g class="fu">')
    out.append(eyebrow(30, 40, "prompt calendar", theme, 3))
    active = sum(1 for value in values if value > 0)
    out.append(
        f'<text class="sub" x="{width - 30}" y="40" text-anchor="end">'
        f'{esc(compact(summary.get("prompt_total", 0)))} prompts · {active} active days '
        f'since {esc(min(calendar))}</text>'
    )
    out.append("</g>")

    last_month = None
    for column in range(columns):
        day = start + timedelta(days=column * 7)
        if day > end_date:
            break
        if day.month != last_month:
            last_month = day.month
            x = left + column * pitch
            if x < left + grid_width - 16:
                out.append(f'<text class="tick" x="{x}" y="{top - 8}">{MONTHS[day.month - 1]}</text>')

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        out.append(
            f'<text class="tick" x="{left - 10}" y="{top + row * pitch + 9}" '
            f'text-anchor="end">{label}</text>'
        )

    for index, value in enumerate(values):
        column, row = index // 7, index % 7
        out.append(
            f'<use class="po {uid}d{column}" href="#{uid}c" x="{left + column * pitch}" '
            f'y="{top + row * pitch}" fill="{theme.ramp[levels.get(value, 0)]}"/>'
        )

    out.append(
        f'<text class="tick" x="{left}" y="{top + 7 * pitch + 14}">'
        f'Prompts submitted to Claude Code · timestamps only, no content read</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：概览环


def card_stats(summary: dict[str, Any], theme: Theme) -> str:
    uid = f"s{theme.name}"
    width, height = 435, 252
    out = [open_svg(width, height, "Usage split"), base_style(theme),
           frame(uid, width, height, theme)]
    out.append('<g class="fu">' + eyebrow(24, 36, "split by tool", theme, 2) + "</g>")

    sources = sorted(summary.get("sources", {}).items(), key=lambda item: -item[1])
    total = sum(value for _, value in sources) or 1

    # 左侧环形图：各工具 token 占比
    cx, cy, radius, thickness = 106, 140, 52, 15
    circumference = 2 * math.pi * radius
    out.append(
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
        f'stroke="{theme.grid}" stroke-width="{thickness}"/>'
    )
    offset = 0.0
    for index, (name, value) in enumerate(sources):
        fraction = value / total
        length = circumference * fraction
        color = theme.accents[index % len(theme.accents)]
        # dashoffset 用于给扇段定位，所以动画只能加在外层 <g> 上，不能碰弧本身
        out.append(
            f'<g class="fi" style="animation-delay:{.15 + index * .12:.2f}s">'
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
            f'stroke="{color}" stroke-width="{thickness}" stroke-linecap="butt" '
            f'stroke-dasharray="{length - 2.5:.1f} {circumference - length + 2.5:.1f}" '
            f'stroke-dashoffset="{-offset:.1f}" transform="rotate(-90 {cx} {cy})"/></g>'
        )
        offset += length
    out.append(
        f'<text class="kpi" x="{cx}" y="{cy + 2}" text-anchor="middle">'
        f'{esc(compact(summary["total_tokens"]))}</text>'
        f'<text class="lab" x="{cx}" y="{cy + 19}" text-anchor="middle">TOKENS</text>'
    )

    # 右侧图例 + 补充 KPI
    legend_x, legend_y = 196, 74
    for index, (name, value) in enumerate(sources):
        y = legend_y + index * 34
        color = theme.accents[index % len(theme.accents)]
        out.append(
            f'<g class="fu" style="animation-delay:{.2 + index * .08:.2f}s">'
            f'<rect x="{legend_x}" y="{y - 10}" width="4" height="26" rx="2" fill="{color}"/>'
            f'<text class="h2" x="{legend_x + 14}" y="{y}">{esc(clip(name, 20))}</text>'
            f'<text class="val" x="{legend_x + 14}" y="{y + 15}" fill="{theme.muted}">'
            f'{esc(compact(value))} · {value / total * 100:.0f}%</text></g>'
        )

    rows = [
        ("Sessions", str(summary["sessions"])),
        ("Turns", compact(summary["turns"])),
        ("Output", compact(summary["output_tokens"])),
        ("Cached in", compact(summary["cache_read_tokens"])),
    ]
    base_y = legend_y + len(sources) * 34 + 8
    for index, (label, value) in enumerate(rows):
        column, row = index % 2, index // 2
        x = legend_x + column * 108
        y = base_y + row * 34
        out.append(
            f'<g class="fu" style="animation-delay:{.34 + index * .05:.2f}s">'
            f'<text class="kpi-s" x="{x}" y="{y}">{esc(value)}</text>'
            f'<text class="lab" x="{x}" y="{y + 14}">{esc(label.upper())}</text></g>'
        )

    out.append(
        f'<line x1="24" y1="{height - 34}" x2="{width - 24}" y2="{height - 34}" '
        f'stroke="{theme.grid}"/>'
        f'<text class="tick" x="24" y="{height - 16}">Cached input counted separately</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：模型榜


def card_models(summary: dict[str, Any], theme: Theme) -> str:
    uid = f"d{theme.name}"
    width, height = 435, 252
    out = [open_svg(width, height, "Top models"), base_style(theme),
           frame(uid, width, height, theme)]
    out.append('<g class="fu">' + eyebrow(24, 36, "models used", theme, 3) + "</g>")

    models = summary.get("top_models", [])[:6]
    if not models:
        out.append(f'<text class="sub" x="24" y="80">No model data yet</text>')
        return "".join(out) + "</svg>"

    peak = max(value for _, value in models)
    grand = sum(value for _, value in summary.get("top_models", [])) or 1
    top, row_height, bar_left = 62, 27, 24
    bar_width = width - 48

    for index, (name, value) in enumerate(models):
        y = top + index * row_height
        color = theme.accents[index % len(theme.accents)]
        length = max(3.0, bar_width * value / peak)
        out.append(
            f'<g class="fu" style="animation-delay:{.1 + index * .06:.2f}s">'
            f'<text class="val" x="{bar_left}" y="{y}" fill="{theme.text}">'
            f'{esc(clip(name, 22))}</text>'
            f'<text class="val" x="{bar_left + bar_width}" y="{y}" text-anchor="end" '
            f'fill="{theme.muted}">{esc(compact(value))} · {value / grand * 100:.0f}%</text>'
            f'<rect x="{bar_left}" y="{y + 6}" width="{bar_width}" height="7" rx="3.5" '
            f'fill="{theme.grid}"/>'
            f'<rect class="gw" style="animation-delay:{.16 + index * .07:.2f}s" '
            f'x="{bar_left}" y="{y + 6}" width="{length:.1f}" height="7" rx="3.5" '
            f'fill="{color}"/></g>'
        )

    out.append(
        f'<line x1="24" y1="{height - 34}" x2="{width - 24}" y2="{height - 34}" '
        f'stroke="{theme.grid}"/>'
        f'<text class="tick" x="24" y="{height - 16}">'
        f'{len(summary.get("top_models", []))} distinct models across all sessions</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：24h 节律


def card_clock(summary: dict[str, Any], theme: Theme) -> str:
    uid = f"c{theme.name}"
    width, height = 435, 252
    out = [open_svg(width, height, "Hourly coding rhythm"), base_style(theme),
           frame(uid, width, height, theme)]
    out.append('<g class="fu">' + eyebrow(24, 36, "daily rhythm", theme, 4) + "</g>")

    hours = list(summary.get("hours") or [0] * 24)
    peak = max(hours) or 1
    # 圆心上移、半径收窄，好让 12 点方向的刻度停在脚注分隔线以上
    cx, cy = 118, 126
    inner, outer, label_radius = 26, 62, 78

    out.append(
        f'<circle cx="{cx}" cy="{cy}" r="{inner - 4}" fill="none" stroke="{theme.grid}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{outer + 6}" fill="none" stroke="{theme.grid}" '
        f'stroke-dasharray="2 4" opacity=".7"/>'
    )
    # 24 根径向柱，长度按该小时的对话轮数；淡入放在 <g> 上以保留各自的 opacity
    for hour, value in enumerate(hours):
        angle = math.radians(hour * 15 - 90)
        length = inner + (outer - inner) * (value / peak)
        x1, y1 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
        x2, y2 = cx + length * math.cos(angle), cy + length * math.sin(angle)
        ratio = value / peak
        color = theme.accents[0] if ratio > 0.66 else (
            theme.accents[1] if ratio > 0.33 else theme.accents[2]
        )
        out.append(
            f'<g class="fi" style="animation-delay:{.12 + hour * .018:.3f}s">'
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="6" stroke-linecap="round" opacity="{0.25 + 0.75 * ratio:.2f}"/></g>'
        )
    for hour, label in ((0, "00"), (6, "06"), (12, "12"), (18, "18")):
        angle = math.radians(hour * 15 - 90)
        x, y = cx + label_radius * math.cos(angle), cy + label_radius * math.sin(angle)
        out.append(
            f'<text class="tick" x="{x:.1f}" y="{y + 3.5:.1f}" text-anchor="middle">{label}</text>'
        )

    busiest = max(range(24), key=lambda hour: hours[hour]) if any(hours) else 0
    night = sum(hours[0:7]) + sum(hours[22:24])
    share = night / (sum(hours) or 1) * 100
    facts = [
        (f"{busiest:02d}:00", "PEAK HOUR"),
        (f"{share:.0f}%", "AFTER HOURS"),
        (compact(sum(hours)), "TURNS PLOTTED"),
    ]
    for index, (value, label) in enumerate(facts):
        y = 88 + index * 46
        out.append(
            f'<g class="fu" style="animation-delay:{.28 + index * .07:.2f}s">'
            f'<text class="kpi-s" x="232" y="{y}">{esc(value)}</text>'
            f'<text class="lab" x="232" y="{y + 14}">{esc(label)}</text></g>'
        )

    out.append(
        f'<line x1="24" y1="{height - 34}" x2="{width - 24}" y2="{height - 34}" '
        f'stroke="{theme.grid}"/>'
        f'<text class="tick" x="24" y="{height - 16}">Turns by local hour (Asia/Shanghai)</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：周节奏


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def card_weekdays(summary: dict[str, Any], theme: Theme) -> str:
    uid = f"w{theme.name}"
    width, height = 435, 252
    out = [open_svg(width, height, "Weekday distribution"), base_style(theme),
           frame(uid, width, height, theme)]
    out.append('<g class="fu">' + eyebrow(24, 36, "weekly shape", theme, 5) + "</g>")

    weekdays = list(summary.get("weekdays") or [0] * 7)
    peak = max(weekdays) or 1
    total = sum(weekdays) or 1
    # 最高柱顶留在 106，标题那两行文字才不会被顶到
    base_y, max_height = 186, 80
    slot = (width - 56) / 7

    out.append(
        f'<line x1="24" y1="{base_y}" x2="{width - 24}" y2="{base_y}" stroke="{theme.grid}"/>'
    )
    for index, value in enumerate(weekdays):
        bar_height = max(2.0, max_height * value / peak)
        x = 28 + index * slot + slot * 0.18
        bar_width = slot * 0.64
        color = theme.accents[0] if value == peak else theme.accents[1]
        opacity = "1" if value == peak else ".55"
        out.append(
            f'<g class="fu" style="animation-delay:{.1 + index * .06:.2f}s">'
            f'<rect class="gy" style="animation-delay:{.14 + index * .07:.2f}s" '
            f'x="{x:.1f}" y="{base_y - bar_height:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" rx="5" fill="{color}" opacity="{opacity}"/>'
            f'<text class="tick" x="{x + bar_width / 2:.1f}" y="{base_y - bar_height - 8:.1f}" '
            f'text-anchor="middle">{value / total * 100:.0f}%</text>'
            f'<text class="tick" x="{x + bar_width / 2:.1f}" y="{base_y + 16}" '
            f'text-anchor="middle" fill="{theme.dim}">{WEEKDAYS[index]}</text></g>'
        )

    weekend = weekdays[5] + weekdays[6]
    busiest = WEEKDAYS[max(range(7), key=lambda index: weekdays[index])]
    out.append(
        f'<text class="h2" x="24" y="70">{esc(busiest)} is the heaviest day</text>'
        f'<text class="val" x="24" y="88" fill="{theme.muted}">'
        f'{weekend / total * 100:.0f}% of turns happen on weekends</text>'
    )
    out.append(
        f'<line x1="24" y1="{height - 34}" x2="{width - 24}" y2="{height - 34}" '
        f'stroke="{theme.grid}"/>'
        f'<text class="tick" x="24" y="{height - 16}">Share of all turns by weekday</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：趋势


def card_trend(series: list[tuple[str, int]], theme: Theme, window: int = 90) -> str:
    uid = f"t{theme.name}"
    width, height = 880, 190
    out = [open_svg(width, height, "Recent activity trend"), base_style(theme),
           frame(uid, width, height, theme)]
    out.append('<g class="fu">' + eyebrow(30, 38, f"last {window} days", theme, 1) + "</g>")

    recent = series[-window:]
    if not recent:
        return "".join(out) + "</svg>"
    peak = max(value for _, value in recent) or 1
    left, right = 34, width - 34
    base_y, max_height = 152, 84
    slot = (right - left) / max(len(recent), 1)
    bar_width = max(2.0, slot * 0.7)

    for fraction in (0.5, 1.0):
        y = base_y - max_height * fraction
        out.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{theme.grid}" '
            f'stroke-dasharray="2 5"/>'
            f'<text class="tick" x="{right + 2}" y="{y + 3.5:.1f}" text-anchor="end" '
            f'opacity=".8">{esc(compact(int(peak * fraction)))}</text>'
        )

    out.append(
        f'<defs><linearGradient id="{uid}bar" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{theme.accents[0]}"/>'
        f'<stop offset="1" stop-color="{theme.accents[2]}" stop-opacity=".55"/>'
        f"</linearGradient></defs>"
    )
    for index, (day, value) in enumerate(recent):
        bar_height = max_height * value / peak
        x = left + index * slot + (slot - bar_width) / 2
        if value <= 0:
            out.append(
                f'<rect x="{x:.1f}" y="{base_y - 2}" width="{bar_width:.1f}" height="2" '
                f'rx="1" fill="{theme.grid}"/>'
            )
            continue
        out.append(
            f'<rect class="gy" style="animation-delay:{.1 + index * .006:.3f}s" '
            f'x="{x:.1f}" y="{base_y - bar_height:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" rx="{min(bar_width / 2, 2.5):.1f}" '
            f'fill="url(#{uid}bar)"/>'
        )

    out.append(f'<line x1="{left}" y1="{base_y}" x2="{right}" y2="{base_y}" stroke="{theme.border}"/>')
    # 只在首、中、末打日期刻度，避免拥挤
    for position, index in ((left, 0), ((left + right) / 2, len(recent) // 2), (right, len(recent) - 1)):
        anchor = "start" if index == 0 else ("end" if index == len(recent) - 1 else "middle")
        out.append(
            f'<text class="tick" x="{position:.1f}" y="{base_y + 17}" '
            f'text-anchor="{anchor}">{esc(recent[index][0])}</text>'
        )

    total = sum(value for _, value in recent)
    active = sum(1 for _, value in recent if value > 0)
    out.append(
        f'<text class="sub" x="{width - 30}" y="38" text-anchor="end">'
        f'{esc(compact(total))} tokens · {active}/{len(recent)} days active</text>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- 卡片：终端


def card_terminal(summary: dict[str, Any], theme: Theme, title: str) -> str:
    uid = f"x{theme.name}"
    char = 7.35  # 12.5px 等宽字体的近似字宽，用于列对齐
    left, top, line_height = 26, 64, 20

    sources = sorted(summary.get("sources", {}).items(), key=lambda item: -item[1])
    grand = sum(value for _, value in sources) or 1

    lines: list[list[tuple[float, str, str]]] = [
        [(0, "$", theme.accents[0]), (2, "profile stats --since ", theme.text),
         (24, str(summary.get("first_date") or "—"), theme.accents[1])],
        [],
        [(2, "total tokens", theme.dim), (20, compact(summary["total_tokens"]), theme.text),
         (32, "reported usage units", theme.muted)],
        [(2, "active days", theme.dim), (20, str(summary["active_days"]), theme.text),
         (32, f"{summary.get('first_date') or '—'} → {summary.get('last_date') or '—'}", theme.muted)],
        [(2, "sessions", theme.dim), (20, str(summary["sessions"]), theme.text),
         (32, f"{compact(summary['turns'])} turns", theme.muted)],
        [],
    ]
    for name, value in sources[:3]:
        share = value / grand
        filled = round(share * 22)
        lines.append([
            (2, clip(name, 16), theme.dim),
            (20, compact(value), theme.text),
            (32, f"{share * 100:5.1f}%", theme.muted),
            (40, "█" * filled + "░" * (22 - filled), theme.accents[0]),
        ])
    lines.append([])
    lines.append([(0, "$", theme.accents[0])])

    # 高度随行数走，工具数量变化时底部留白保持一致
    width = 880
    height = top + (len(lines) - 1) * line_height + 26
    out = [open_svg(width, height, "Terminal summary"), base_style(theme),
           frame(uid, width, height, theme)]

    # 标题栏
    out.append(
        f'<path d="M0 16a16 16 0 0 1 16-16h{width - 32}a16 16 0 0 1 16 16v20H0z" '
        f'fill="{theme.panel}"/>'
        f'<line x1="0" y1="36" x2="{width}" y2="36" stroke="{theme.border}"/>'
    )
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{22 + index * 17}" cy="18.5" r="5.5" fill="{color}"/>')
    out.append(
        f'<text class="mono" x="{width / 2}" y="23" text-anchor="middle" font-size="11.5" '
        f'fill="{theme.muted}">{esc(title.lower().replace(" ", "-"))} — zsh</text>'
    )

    def row(index: int, segments: list[tuple[float, str, str]]) -> str:
        """按字符列绘制一行，segments 为 (列号, 文本, 颜色)。"""
        y = top + index * line_height
        spans = "".join(
            f'<tspan x="{left + column * char:.1f}" fill="{color}">{esc(text)}</tspan>'
            for column, text, color in segments
        )
        return (
            f'<text class="mono fu" style="animation-delay:{.06 + index * .05:.2f}s" '
            f'y="{y}" font-size="12.5" xml:space="preserve">{spans}</text>'
        )

    for index, segments in enumerate(lines):
        if segments:
            out.append(row(index, segments))
    cursor_y = top + (len(lines) - 1) * line_height
    out.append(
        f'<rect class="cur" x="{left + 2 * char:.1f}" y="{cursor_y - 10}" width="8" '
        f'height="13" fill="{theme.text}" opacity=".85"/>'
    )
    return "".join(out) + "</svg>"


# ---------------------------------------------------------------- HTML 报告


CARD_ORDER = ("hero", "heatmap", "calendar", "stats", "models", "clock", "weekdays",
              "trend", "terminal")


def report_html(title: str, subtitle: str, cards: dict[str, str],
                summary: dict[str, Any]) -> str:
    """本地交互报告：同一套卡片放进一个可切换主题的页面。

    卡片用 <img> 外链而不是内联。SVG 里的 <style> 一旦内联进 HTML 就会提升到文档
    作用域，16 份同名规则互相覆盖，最后一份主题会赢；外链能天然隔离，顺带把页面
    从 200KB 缩到几 KB。
    """
    dark_svgs = "".join(
        f'<figure class="card"><img src="{name}-dark.svg" alt="{esc(name)}"></figure>'
        for name in CARD_ORDER if f"{name}-dark" in cards
    )
    light_svgs = "".join(
        f'<figure class="card"><img src="{name}-light.svg" alt="{esc(name)}"></figure>'
        for name in CARD_ORDER if f"{name}-light" in cards
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
:root{{--bg:#07090e;--fg:#e8eef9;--dim:#98a3b8;--line:#232a3a;--panel:#0e121b}}
[data-theme=light]{{--bg:#f4f7fb;--fg:#0d1424;--dim:#57637a;--line:#dde4ee;--panel:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;padding:40px 24px 72px;background:var(--bg);color:var(--fg);
font-family:{FONT};transition:background .25s,color .25s}}
.wrap{{max-width:940px;margin:0 auto}}
header{{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:28px}}
h1{{font-size:22px;margin:0 0 4px;letter-spacing:-.4px}}
p.sub{{margin:0;color:var(--dim);font-size:13px}}
button{{background:var(--panel);color:var(--fg);border:1px solid var(--line);
border-radius:9px;padding:8px 14px;font-size:12.5px;font-weight:600;cursor:pointer}}
button:hover{{border-color:var(--dim)}}
.grid{{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}}
.card{{margin:0;line-height:0}}
.card img{{max-width:100%;height:auto;display:block}}
[data-theme=dark] .light-set,[data-theme=light] .dark-set{{display:none}}
table{{border-collapse:collapse;width:100%;margin-top:12px;font-size:13px}}
td,th{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left}}
th{{color:var(--dim);font-weight:600;font-size:11px;letter-spacing:1px;text-transform:uppercase}}
section{{border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin-top:24px;
background:var(--panel)}}
h2{{font-size:14px;margin:0;letter-spacing:-.2px}}
</style></head><body><div class="wrap">
<header><div><h1>{esc(title)}</h1><p class="sub">{esc(subtitle)} · {esc(summary.get('first_date') or '—')} → {esc(summary.get('last_date') or '—')}</p></div>
<button onclick="var r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'">Toggle theme</button></header>
<div class="grid dark-set">{dark_svgs}</div>
<div class="grid light-set">{light_svgs}</div>
<section><h2>Models</h2><table><tr><th>Model</th><th>Tokens</th></tr>{model_rows}</table></section>
</div></body></html>
"""


# ---------------------------------------------------------------- 编排


# README 里只用到宽度；高度记在这里便于查阅（terminal 的高度随行数浮动）
CARD_SIZES = {
    "hero": (880, 218),
    "heatmap": (880, 200),
    "calendar": (880, 200),
    "stats": (435, 252),
    "models": (435, 252),
    "clock": (435, 252),
    "weekdays": (435, 252),
    "trend": (880, 190),
    "terminal": (880, 270),
}


def build_cards(daily: dict[str, dict[str, Any]], summary: dict[str, Any],
                title: str, subtitle: str, window_days: int) -> dict[str, str]:
    """为每个主题生成全部卡片，键名形如 `hero-dark`。"""
    end_date = (
        date.fromisoformat(summary["last_date"]) if summary.get("last_date") else date.today()
    )
    # 连续日序列（含空白日），趋势图和波形都基于它
    start = end_date - timedelta(days=window_days - 1)
    series = [
        ((start + timedelta(days=index)).isoformat(),
         daily.get((start + timedelta(days=index)).isoformat(), {}).get("total_tokens", 0))
        for index in range((end_date - start).days + 1)
    ]

    cards: dict[str, str] = {}
    for theme in THEMES:
        cards[f"hero-{theme.name}"] = card_hero(summary, series, theme, title, subtitle)
        cards[f"heatmap-{theme.name}"] = card_heatmap(daily, end_date, window_days, summary, theme)
        calendar = card_calendar(summary, end_date, theme)
        if calendar:
            cards[f"calendar-{theme.name}"] = calendar
        cards[f"stats-{theme.name}"] = card_stats(summary, theme)
        cards[f"models-{theme.name}"] = card_models(summary, theme)
        cards[f"clock-{theme.name}"] = card_clock(summary, theme)
        cards[f"weekdays-{theme.name}"] = card_weekdays(summary, theme)
        cards[f"trend-{theme.name}"] = card_trend(series, theme)
        cards[f"terminal-{theme.name}"] = card_terminal(summary, theme, title)
    return cards
