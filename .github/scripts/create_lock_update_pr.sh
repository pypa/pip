#!/usr/bin/env bash
set -euo pipefail

lock_files=(
  build-project/pylock.toml
  pylock.dev.toml
  tools/pylock.update-rtd-redirects.toml
)

if git diff --quiet -- "${lock_files[@]}"; then
  echo "Lock files are already up to date."
  exit 0
fi

branch="update-build-project-lock"
base="${GITHUB_REF_NAME:?GITHUB_REF_NAME must name the target branch}"
remote_ref="refs/heads/${branch}"
old_head=$(git ls-remote --heads origin "${remote_ref}" | cut -f1)
open_prs=$(gh pr list --base "${base}" --head "${branch}" --state open --json number --jq length)

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git switch -c "${branch}"
git add "${lock_files[@]}"
git commit -m "Update lock files"
git push --force-with-lease="${remote_ref}:${old_head}" origin "${branch}"

if ((open_prs > 0)); then
  echo "An open pull request already exists; its branch was updated."
else
  gh pr create \
    --base "${base}" \
    --head "${branch}" \
    --title "Update lock files" \
    --body 'Update the build-project, development and redirect-script locks with pip and Nab.'
fi
