<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-dark.svg?v=8afc1b51"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=1e0b018f"><img alt="Token activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-light.svg?v=1e0b018f" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-dark.svg?v=39403e55"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=ebb0e83a"><img alt="Prompt calendar" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=ebb0e83a" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-dark.svg?v=dbf353f7"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=36e185b3"><img alt="Token split by tool" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/stats-light.svg?v=36e185b3" width="440"></picture><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-dark.svg?v=e62d3b37"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=1921ab82"><img alt="Top models by usage" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-light.svg?v=1921ab82" width="440"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-dark.svg?v=1d79f97a"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=6076bc2d"><img alt="Terminal-style summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=6076bc2d" width="880"></picture></p>

<details>
<summary>&nbsp;<b>claude-code</b> only &nbsp;·&nbsp; 5.31B tokens, 61% of total</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-dark.svg?v=53077b85"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-light.svg?v=c3ab4902"><img alt="claude-code activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-light.svg?v=c3ab4902" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-dark.svg?v=e4596c13"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-light.svg?v=b87fe465"><img alt="claude-code models" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-light.svg?v=b87fe465" width="440"></picture></p>
</details>

<details>
<summary>&nbsp;<b>codex</b> only &nbsp;·&nbsp; 3.39B tokens, 39% of total</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-dark.svg?v=9d4fe3df"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-light.svg?v=ede4d2a5"><img alt="codex activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-light.svg?v=ede4d2a5" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-dark.svg?v=019eb8e6"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-light.svg?v=9c4029e6"><img alt="codex models" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-light.svg?v=9c4029e6" width="440"></picture></p>
</details>
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
