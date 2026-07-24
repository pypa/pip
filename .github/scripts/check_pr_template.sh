#!/usr/bin/env bash
set -euo pipefail

require() {
    if ! grep -qE -- "$1" <<< "$PR_BODY"; then
        echo "::error::$2"
        exit 1
    fi
}

if [ "$PR_USER_LOGIN" = "dependabot[bot]" ]; then
  echo "Skipping dependabot PR."
  exit 0
fi

if [ "$PR_NUMBER" -le 14068 ]; then
  echo "Skipping old PR."
  exit 0
fi

require "^[[:space:]]*- \[" \
"Could not find the pip PR checklist in the pull request body. This probably means you've used a tool to submit your PR rather than the GitHub UI. Please add the required checklist from CONTRIBUTING.md."

require "^[[:space:]]*- \[\s*[xX]\s*\] I agree to follow the \[PSF Code of Conduct\]" \
"The 'PSF Code of Conduct' checkbox in the PR checklist must be checked."

require "^[[:space:]]*- \[\s*[xX]\s*\] I have read and have followed the \[CONTRIBUTING\.md\]" \
"The 'CONTRIBUTING.md' checkbox in the PR checklist must be checked."

require "^[[:space:]]*- \[\s*[xX]\s*\] I have added a news file fragment" \
"The 'news file fragment' checkbox in the PR checklist must be checked. If this PR does not need a news fragment, check the box anyway to confirm you have considered it."

require "^[[:space:]]*- \[\s*[xX]\s*\] I have read and followed the \[AI_POLICY\.md\]" \
"The 'AI_POLICY.md' checkbox in the PR checklist must be checked."

if grep -qE -- "^[[:space:]]*(-\s+)?Assisted-by:[[:space:]]*\S" <<< "$PR_BODY"; then
    # Assisted-by is present and non-empty — no further action needed
    true
elif grep -qE -- "^[[:space:]]*(-\s+)?Assisted-by:" <<< "$PR_BODY"; then
    echo "::error::An 'Assisted-by:' line was found but no tool was specified. Please add the tool name, e.g. 'Assisted-by: Claude'."
    exit 1
fi

echo "PR Checklist verification passed."
