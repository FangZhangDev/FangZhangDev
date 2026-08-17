<h1 align="center">Vibe Coding Activity</h1>

<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-dark.svg?v=8e2ae04b"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=257516ee"><img alt="Prompt calendar" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=257516ee" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-dark.svg?v=e50b7636"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=2f6de42d"><img alt="Terminal-style summary" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=2f6de42d" width="880"></picture></p>

<details>
<summary>&nbsp;<b>By tool</b> &nbsp;·&nbsp; <b>claude-code</b> 62% &nbsp;·&nbsp; <b>codex</b> 38%</summary>
<br>
<p align="center"><b>claude-code</b> &nbsp;·&nbsp; 5.46B tokens &nbsp;·&nbsp; 62% of total &nbsp;·&nbsp; 3,137 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-dark.svg?v=9ee7e280"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=71c2dd09"><img alt="claude-code activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=71c2dd09" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-dark.svg?v=60de4ce5"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=72836238"><img alt="claude-code models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=72836238" width="440"></picture></p>
<p align="center"><b>codex</b> &nbsp;·&nbsp; 3.39B tokens &nbsp;·&nbsp; 38% of total &nbsp;·&nbsp; 905 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-dark.svg?v=6d17442a"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=b5d2ce2a"><img alt="codex activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=b5d2ce2a" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-dark.svg?v=0aa6163c"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=84445764"><img alt="codex models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=84445764" width="440"></picture></p>
</details>
<!-- profile:gallery:end -->

<details>
<summary>&nbsp;<b>How this profile is built</b></summary>

<br>

A local collector reads Claude Code and Codex session logs, keeps only aggregated usage counts, and renders them into the cards above. The public ledger is one JSON line per day; everything else stays on the machine that produced it.

- **Ledgers** — [`data/daily.jsonl`](https://github.com/FangZhangDev/FangZhangDev/blob/main/data/daily.jsonl) for tokens and [`data/prompts.jsonl`](https://github.com/FangZhangDev/FangZhangDev/blob/main/data/prompts.jsonl) for prompt counts, both append-only, one row per active day
- **Cards** — [`dist/`](https://github.com/FangZhangDev/FangZhangDev/tree/main/dist), the prompt calendar and terminal summary, plus per-tool views under the toggles above
- **Source & setup** — [`docs/README.md`](https://github.com/FangZhangDev/FangZhangDev/blob/main/docs/README.md)

The token heatmap and the prompt calendar cover different spans on purpose. Claude Code prunes
session transcripts after 30 days, so per-day token figures only reach back as far as the
surviving records plus what its aggregate cache retained; prompt timestamps go back further.

</details>
