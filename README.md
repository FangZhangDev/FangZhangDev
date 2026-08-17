<!-- profile:gallery:begin -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-dark.svg?v=63ef946b">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-light.svg?v=d319304c">
    <img alt="AI coding profile summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-light.svg?v=d319304c" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-dark.svg?v=13c936bf">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=5d259a56">
    <img alt="Daily activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=5d259a56" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-dark.svg?v=d6aeec96">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=d0a8dc67">
    <img alt="Prompt calendar" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=d0a8dc67" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-dark.svg?v=9939c5d3">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=621a9357">
    <img alt="Token split by tool" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=621a9357" width="435">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-dark.svg?v=3496adc7">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=21b32133">
    <img alt="Top models by usage" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=21b32133" width="435">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-dark.svg?v=53098009">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-light.svg?v=9716073b">
    <img alt="Hourly coding rhythm" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-light.svg?v=9716073b" width="435">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-dark.svg?v=460338bc">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-light.svg?v=4454dfc4">
    <img alt="Weekday distribution" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-light.svg?v=4454dfc4" width="435">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-dark.svg?v=fc768604">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-light.svg?v=1f7db07a">
    <img alt="Recent 90-day trend" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-light.svg?v=1f7db07a" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-dark.svg?v=b31fa5ce">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=e7419ea2">
    <img alt="Terminal-style summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=e7419ea2" width="880">
  </picture>
</p>
<!-- profile:gallery:end -->

<p align="center">
  <sub>Cards regenerate daily from local Claude Code and Codex metadata — no prompts, paths, credentials, transcripts, or repository names ever leave this machine.</sub>
</p>

<details>
<summary>&nbsp;<b>How this profile is built</b></summary>

<br>

A local collector reads Claude Code and Codex session logs, keeps only aggregated usage counts, and renders them into the cards above. The public ledger is one JSON line per day; everything else stays on the machine that produced it.

- **Ledger** — [`data/daily.jsonl`](https://github.com/FangZhangDev/FangZhangDev/blob/main/data/daily.jsonl), append-only, one row per active day
- **Cards** — [`dist/`](https://github.com/FangZhangDev/FangZhangDev/tree/main/dist), nine SVG views in light and dark variants
- **Source & setup** — [`docs/README.md`](https://github.com/FangZhangDev/FangZhangDev/blob/main/docs/README.md)

The token heatmap and the prompt calendar cover different spans on purpose. Claude Code prunes
session transcripts after 30 days, so per-day token figures only reach back as far as the
surviving records plus what its aggregate cache retained; prompt timestamps go back further.

</details>
