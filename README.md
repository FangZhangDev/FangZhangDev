<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-dark.svg?v=2446ebeb"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=6d505a7b"><img alt="Prompt calendar" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/calendar-light.svg?v=6d505a7b" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-dark.svg?v=415c9647"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=f6327f7a"><img alt="Terminal-style summary" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/terminal-light.svg?v=f6327f7a" width="880"></picture></p>

<details>
<summary>&nbsp;<b>claude-code</b> only &nbsp;·&nbsp; 5.35B tokens, 61% of total &nbsp;·&nbsp; 3,107 prompts</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-dark.svg?v=17c979bd"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=1ad74e7c"><img alt="claude-code activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-claude-code-light.svg?v=1ad74e7c" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-dark.svg?v=7b7782c2"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=a393c99e"><img alt="claude-code models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-claude-code-light.svg?v=a393c99e" width="440"></picture></p>
</details>

<details>
<summary>&nbsp;<b>codex</b> only &nbsp;·&nbsp; 3.39B tokens, 39% of total &nbsp;·&nbsp; 905 prompts</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-dark.svg?v=65fd27e3"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=739787cd"><img alt="codex activity heatmap" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/heatmap-codex-light.svg?v=739787cd" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-dark.svg?v=308ead95"><source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=36dd851a"><img alt="codex models" src="https://cdn.jsdelivr.net/gh/FangZhangDev/FangZhangDev@main/dist/models-codex-light.svg?v=36dd851a" width="440"></picture></p>
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
