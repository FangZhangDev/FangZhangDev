<!-- profile:gallery:begin -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-dark.svg?v=20e01e91">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-light.svg?v=59b06b6d">
    <img alt="AI coding profile summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/hero-light.svg?v=59b06b6d" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-dark.svg?v=f4151d7c">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=3f3206a8">
    <img alt="Daily activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=3f3206a8" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-dark.svg?v=25a590d9">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=3643c2b5">
    <img alt="Token split by tool" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=3643c2b5" width="435">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-dark.svg?v=ea5648f0">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=b07d6d32">
    <img alt="Top models by usage" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=b07d6d32" width="435">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-dark.svg?v=6e51a8de">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-light.svg?v=c783584a">
    <img alt="Hourly coding rhythm" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/clock-light.svg?v=c783584a" width="435">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-dark.svg?v=77c8275e">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-light.svg?v=edf785cd">
    <img alt="Weekday distribution" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/weekdays-light.svg?v=edf785cd" width="435">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-dark.svg?v=a0e667fe">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-light.svg?v=8a36f887">
    <img alt="Recent 90-day trend" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/trend-light.svg?v=8a36f887" width="880">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-dark.svg?v=77595977">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=42010f01">
    <img alt="Terminal-style summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=42010f01" width="880">
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
- **Cards** — [`dist/`](https://github.com/FangZhangDev/FangZhangDev/tree/main/dist), eight SVG views in light and dark variants
- **Source & setup** — [`docs/README.md`](https://github.com/FangZhangDev/FangZhangDev/blob/main/docs/README.md)

</details>
