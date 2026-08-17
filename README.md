<h1 align="center">Vibe Coding Activity</h1>

<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/calendar-dark.svg?v=64c5440e"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/calendar-light.svg?v=58e4d1ac"><img alt="Prompt calendar" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/calendar-light.svg?v=58e4d1ac" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/terminal-dark.svg?v=9834b7f5"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/terminal-light.svg?v=40b8ece6"><img alt="Terminal-style summary" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/terminal-light.svg?v=40b8ece6" width="880"></picture></p>

<details>
<summary>&nbsp;<b>By tool</b> &nbsp;·&nbsp; <b>claude-code</b> 62% &nbsp;·&nbsp; <b>codex</b> 38%</summary>
<br>
<p align="center"><b>claude-code</b> &nbsp;·&nbsp; 5.49B tokens &nbsp;·&nbsp; 62% of total &nbsp;·&nbsp; 3,152 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-claude-code-dark.svg?v=c0142b90"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-claude-code-light.svg?v=7589f9f8"><img alt="claude-code activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-claude-code-light.svg?v=7589f9f8" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-claude-code-dark.svg?v=2155ccec"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-claude-code-light.svg?v=9def172f"><img alt="claude-code models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-claude-code-light.svg?v=9def172f" width="440"></picture></p>
<p align="center"><b>codex</b> &nbsp;·&nbsp; 3.4B tokens &nbsp;·&nbsp; 38% of total &nbsp;·&nbsp; 907 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-codex-dark.svg?v=0fe9db59"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-codex-light.svg?v=8554afdf"><img alt="codex activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/heatmap-codex-light.svg?v=8554afdf" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-codex-dark.svg?v=05050a03"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-codex-light.svg?v=e4983504"><img alt="codex models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@ffb06aa6e116e8850c1cd8536a695195249f200e/dist/models-codex-light.svg?v=e4983504" width="440"></picture></p>
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
