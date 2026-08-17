<h1 align="center">Vibe Coding Activity</h1>

<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/calendar-dark.svg?v=ae0266ba"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/calendar-light.svg?v=6b91d0b5"><img alt="Prompt calendar" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/calendar-light.svg?v=6b91d0b5" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/terminal-dark.svg?v=3c8861bb"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/terminal-light.svg?v=f6567829"><img alt="Terminal-style summary" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/terminal-light.svg?v=f6567829" width="880"></picture></p>

<details>
<summary>&nbsp;<b>By tool</b> &nbsp;·&nbsp; <b>claude-code</b> 62% &nbsp;·&nbsp; <b>codex</b> 38%</summary>
<br>
<p align="center"><b>claude-code</b> &nbsp;·&nbsp; 5.44B tokens &nbsp;·&nbsp; 62% of total &nbsp;·&nbsp; 3,135 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-claude-code-dark.svg?v=618e8039"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-claude-code-light.svg?v=c34d6e2b"><img alt="claude-code activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-claude-code-light.svg?v=c34d6e2b" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-claude-code-dark.svg?v=daedf01e"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-claude-code-light.svg?v=8d3d76e4"><img alt="claude-code models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-claude-code-light.svg?v=8d3d76e4" width="440"></picture></p>
<p align="center"><b>codex</b> &nbsp;·&nbsp; 3.39B tokens &nbsp;·&nbsp; 38% of total &nbsp;·&nbsp; 905 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-codex-dark.svg?v=6d17442a"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-codex-light.svg?v=b5d2ce2a"><img alt="codex activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/heatmap-codex-light.svg?v=b5d2ce2a" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-codex-dark.svg?v=b5e05da2"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-codex-light.svg?v=6594eb4e"><img alt="codex models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@4405fb8e547683ee95228ee07c95d0eaa72cb4c2/dist/models-codex-light.svg?v=6594eb4e" width="440"></picture></p>
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
