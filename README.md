<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-dark.svg?v=5b0297fe"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=e7791cbe"><img alt="Prompt calendar" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=e7791cbe" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-dark.svg?v=1be28555"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=bcafc05a"><img alt="Terminal-style summary" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=bcafc05a" width="880"></picture></p>

<details>
<summary>&nbsp;<b>By tool</b> &nbsp;·&nbsp; <b>claude-code</b> 61% &nbsp;·&nbsp; <b>codex</b> 39%</summary>
<br>
<p align="center"><b>claude-code</b> &nbsp;·&nbsp; 5.39B tokens &nbsp;·&nbsp; 61% of total &nbsp;·&nbsp; 3,112 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-dark.svg?v=603e196b"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=0e0382a2"><img alt="claude-code activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=0e0382a2" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-dark.svg?v=491d6388"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=09189b0c"><img alt="claude-code models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=09189b0c" width="440"></picture></p>
<p align="center"><b>codex</b> &nbsp;·&nbsp; 3.39B tokens &nbsp;·&nbsp; 39% of total &nbsp;·&nbsp; 905 prompts</p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-dark.svg?v=65fd27e3"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=739787cd"><img alt="codex activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=739787cd" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-dark.svg?v=3247c517"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=48a1700d"><img alt="codex models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=48a1700d" width="440"></picture></p>
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
- **Cards** — [`dist/`](https://github.com/FangZhangDev/FangZhangDev/tree/main/dist), the prompt calendar and terminal summary, plus per-tool views under the toggles above
- **Source & setup** — [`docs/README.md`](https://github.com/FangZhangDev/FangZhangDev/blob/main/docs/README.md)

The token heatmap and the prompt calendar cover different spans on purpose. Claude Code prunes
session transcripts after 30 days, so per-day token figures only reach back as far as the
surviving records plus what its aggregate cache retained; prompt timestamps go back further.

</details>
