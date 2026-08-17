#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"${PYTHON_BIN}" profile.py update --config config.toml

# dist/*.html 已在 .gitignore 中排除，这里可以整目录 add
git add data/daily.jsonl dist README.md docs
if git diff --cached --quiet; then
  echo "No profile changes to publish."
  exit 0
fi

git commit -m "chore: update coding activity profile"
git push

# jsDelivr 的 @main 地址有 12 小时边缘缓存，且【会忽略查询串】——README 里的
# ?v=<digest> 对它不起 cache-bust 作用（实测：push 完再取仍是旧文件）。所以推送后
# 必须显式 purge，否则 profile 页最长半天还在显示上一版的图。
# asset_cdn = "raw" 时 README 里没有 jsdelivr 地址，下面的循环自然什么都不做。
paths="$(grep -oE 'https://cdn\.jsdelivr\.net/gh/[^"?]+' README.md \
         | sed 's|https://cdn\.jsdelivr\.net||' | sort -u)"

if [ -n "${paths}" ]; then
  count="$(printf '%s\n' "${paths}" | wc -l | tr -d ' ')"
  echo "Purging ${count} jsDelivr path(s)…"
  # 官方批量接口：POST / 带 {"path": [...]}。逐个 GET 也行，但容易触发限流。
  body="$(printf '%s\n' "${paths}" \
          | sed 's/.*/"&"/' | paste -sd, - \
          | sed 's/^/{"path":[/; s/$/]}/')"
  if curl -fsS -X POST https://purge.jsdelivr.net/ \
       -H 'Content-Type: application/json' -d "${body}" -o /dev/null; then
    echo "jsDelivr purge requested."
  else
    # purge 失败不该让整次发布算失败：图最终仍会在 12 小时内自动刷新
    echo "WARN: jsDelivr purge failed; cards may serve stale copies for up to 12h." >&2
  fi
fi
