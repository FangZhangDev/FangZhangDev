#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"${PYTHON_BIN}" profile.py update --config config.toml

# dist/*.html 和 data/*.sqlite 都在 .gitignore 里，这里可以整目录 add。
# data/ 整个进来是有意的：两份账本都是只增不减的长期归档，必须进版本库。
git add data dist README.md docs
if git diff --cached --quiet; then
  echo "No profile changes to publish."
  exit 0
fi

# 第一步：先把卡片本身提交，拿到一个确定包含这批 SVG 的 commit。
git commit -m "chore: update coding activity profile"
CARDS_SHA="$(git rev-parse HEAD)"

# 第二步：把 README 的图片地址钉到那个 SHA 上，单独再提交一次。
#
# 为什么非要钉 SHA：jsDelivr 的 @branch 地址在边缘缓存 12 小时，而且忽略查询串，
# 所以 README 里的 ?v=<digest> 对它不起作用 —— 实测 push 完再 purge，接口报
# finished，仍有多个边缘节点在发上一版的文件。@<sha> 是不可变资源，回源立刻就是
# 对的，缓存头还是 max-age=31536000, immutable（一年），根本不需要 purge。
#
# 注意这里不能用 git commit --amend：amend 会改写 SHA，README 就会指向一个不存在
# 的 commit。必须是第二个 commit，第一个留在历史里给 jsDelivr 取。
if "${PYTHON_BIN}" profile.py pin --config config.toml --ref "${CARDS_SHA}"; then
  git add README.md
  git diff --cached --quiet || git commit -m "chore: pin card URLs to ${CARDS_SHA:0:8}"
fi

git push
echo "Published. Cards live at commit ${CARDS_SHA:0:8}."
