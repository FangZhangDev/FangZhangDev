<!-- profile:gallery:begin -->
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-dark.svg?v=8fd36e8a"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=97c95416"><img alt="Prompt calendar" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/calendar-light.svg?v=97c95416" width="880"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-dark.svg?v=99ae3f97"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=e97e291e"><img alt="Terminal-style summary" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/terminal-light.svg?v=e97e291e" width="880"></picture></p>

<details>
<summary>&nbsp;<b>claude-code</b> only &nbsp;·&nbsp; 5.34B tokens, 61% of total &nbsp;·&nbsp; 3,098 prompts</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-dark.svg?v=095c7d37"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-light.svg?v=ae33c6a7"><img alt="claude-code activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-claude-code-light.svg?v=ae33c6a7" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-dark.svg?v=077a9c8e"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-light.svg?v=a6a91655"><img alt="claude-code models" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-claude-code-light.svg?v=a6a91655" width="440"></picture></p>
</details>

<details>
<summary>&nbsp;<b>codex</b> only &nbsp;·&nbsp; 3.39B tokens, 39% of total &nbsp;·&nbsp; 899 prompts</summary>
<br>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-dark.svg?v=9ac1ead6"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-light.svg?v=e13bc3ff"><img alt="codex activity heatmap" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/heatmap-codex-light.svg?v=e13bc3ff" width="880"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-dark.svg?v=0357adbc"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-light.svg?v=547623e5"><img alt="codex models" src="https://raw.githubusercontent.com/FangZhangDev/FangZhangDev/main/dist/models-codex-light.svg?v=547623e5" width="440"></picture></p>
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
