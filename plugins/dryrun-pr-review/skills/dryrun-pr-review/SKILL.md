---
name: dryrun-pr-review
version: 1.0.1
description: >-
  Activates when the user asks to create a PR or MR, submit changes for review,
  push for review, or open a pull request.
license: Proprietary
triggers:
  - create a PR
  - open a pull request
  - submit for review
  - push changes for review
  - push and open a PR
  - create a merge request
  - open an MR
compatibility: claude-code, cursor, windsurf, cline, aider
allowed_tools:
  - Read
  - Edit
  - Glob
  - Grep
  - Bash
output: >-
  A PR or MR opened on GitHub or GitLab, with DryRunSecurity review comments
  presented to the user for decisions. Loops until DryRunSecurity is satisfied.
---

# DryRunSecurity PR Review Workflow

Full PR/MR lifecycle: detect platform, branch, commit, open PR or MR, poll for DryRunSecurity comments, present findings to the user.

## Platform Detection & Repo Info

Run this and read the output to determine platform and repo coordinates:

```bash
git remote get-url origin
```

From the URL:
- Contains `github.com` → GitHub; use `gh` CLI. Extract `OWNER` and `REPO` from the URL path.
- Otherwise → GitLab; use `glab` CLI. Extract the project path and URL-encode it (replace `/` with `%2F`) for API calls.

All subsequent steps reference `PLATFORM`, `OWNER`, `REPO` (GitHub) or `PROJECT` (GitLab), and `MR_NUMBER`.

## Workflow

### 1. Branch

If on `main`/`master`, create a new branch following this repo's naming conventions. Otherwise use the existing feature branch.

### 2. Stage & Commit

```bash
git status
git add <files>   # selective — never commit secrets or generated files
git commit -m "<message following this repo's commit style>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Push & Create PR/MR

```bash
git push -u origin <branch-name>
```

Check whether a PR/MR already exists for this branch before creating one:

```bash
# GitHub — reuse existing PR if present
EXISTING=$(gh pr view --json number --jq '.number' 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "Using existing PR #$EXISTING"
    MR_NUMBER=$EXISTING
else
    gh pr create --title "<title>" --body "<body>"
    # capture MR_NUMBER from the URL in the output (last path segment)
fi

# GitLab — reuse existing MR if present
BRANCH=$(git rev-parse --abbrev-ref HEAD)
EXISTING=$(glab mr list --source-branch "$BRANCH" 2>/dev/null | awk 'NR==2{print $1}' | tr -d '!')
if [ -n "$EXISTING" ]; then
    echo "Using existing MR !$EXISTING"
    MR_NUMBER=$EXISTING
else
    glab mr create --title "<title>" --description "<body>"
    # capture MR_NUMBER from the output
fi
```

Store the result as `MR_NUMBER`.

### 4. Poll for DryRunSecurity Review Comments

Poll for up to **10 minutes** (every 30 seconds). Use timestamp-based polling — not count-based. Comments can be edited/replaced.

Exit as soon as DRS activity is detected — a DryRunSecurity comment means the review is complete.

```bash
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_EPOCH=$(date +%s)
TIMEOUT=600
POLL_INTERVAL=30

while true; do
    ELAPSED=$(( $(date +%s) - START_EPOCH ))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "Timed out after ${ELAPSED}s with no DryRunSecurity activity."
        break
    fi

    if [ "$PLATFORM" = "github" ]; then
        DRS_NEW=$(gh api repos/${OWNER}/${REPO}/issues/${MR_NUMBER}/comments \
          --jq "[.[] | select((.user.login == \"dryrunsecurity\" or .user.login == \"dryrunsecurity[bot]\") and .created_at > \"${START_TIME}\")] | length")

        DRS_REVIEWS=$(gh api repos/${OWNER}/${REPO}/pulls/${MR_NUMBER}/reviews \
          --jq "[.[] | select((.user.login | test(\"dryrunsecurity\"; \"i\")) and .submitted_at > \"${START_TIME}\")] | length")

        TOTAL=$(( DRS_NEW + DRS_REVIEWS ))
        echo "Waiting for DryRunSecurity review... (${ELAPSED}s elapsed)"
        [ "$TOTAL" -gt 0 ] && echo "DryRunSecurity review received: ${DRS_NEW} comment(s), ${DRS_REVIEWS} review(s)." && break
    else
        DRS_NEW=$(glab api projects/${PROJECT}/merge_requests/${MR_NUMBER}/notes \
          | jq "[.[] | select(.author.username == \"dryrunsecurity\" and .created_at > \"${START_TIME}\")] | length")

        echo "Waiting for DryRunSecurity review... (${ELAPSED}s elapsed)"
        [ "$DRS_NEW" -gt 0 ] && echo "DryRunSecurity review received: ${DRS_NEW} note(s)." && break
    fi

    sleep $POLL_INTERVAL
done
```

If the loop timed out with no DRS activity, inform the user: the DryRunSecurity review period is complete.

### 5. Present DryRunSecurity Comments to User

Fetch all DryRunSecurity comments and **present them to the user** — do not fix automatically.

```bash
# GitHub
gh api repos/${OWNER}/${REPO}/issues/${MR_NUMBER}/comments \
  --jq '.[] | select(.user.login == "dryrunsecurity" or .user.login == "dryrunsecurity[bot]") | {id: .id, body: .body}'

gh api repos/${OWNER}/${REPO}/pulls/${MR_NUMBER}/reviews \
  --jq '.[] | select(.user.login | test("dryrunsecurity"; "i")) | {id: .id, body: .body, state: .state}'

# GitLab
glab api projects/${PROJECT}/merge_requests/${MR_NUMBER}/notes \
  | jq '.[] | select(.author.username == "dryrunsecurity") | {id: .id, body: .body}'
```

For each comment, present:
- File:line (if applicable)
- Summary of the security finding
- Your suggested fix or reason it's a false positive

Then **ask the user** which comments to address and how.

### 6. Act on User Decisions

For comments the user wants fixed:
```bash
# Make code changes, then:
git add <files>
git commit -m "<message following this repo's commit style — addressing DryRunSecurity finding>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

For comments the user wants to decline, post a new comment on the PR/MR thread explaining why:
```bash
# GitHub — DryRunSecurity posts on the PR thread (not inline), so reply via issue comments
gh api repos/${OWNER}/${REPO}/issues/${MR_NUMBER}/comments \
  -f body="Not addressing DryRunSecurity finding: <explanation>"

# GitLab
glab api projects/${PROJECT}/merge_requests/${MR_NUMBER}/notes \
  --method POST -f body="Not addressing DryRunSecurity finding: <explanation>"
```

### 7. Push & Re-poll

```bash
git push
```

Return to Step 4 using the current time as the new `START_TIME`. Continue until polling times out with no new comments.

## Important Notes

- Never force push unless explicitly requested
- Always read files before suggesting changes
- Use `gh` for GitHub repos, `glab` for GitLab repos — detect via `git remote get-url origin`
- Timestamp-based polling only — never count-based
- **Minimize Bash invocations** — consolidate related commands into single scripts (e.g., combine `git add` + `git commit` + `git push` into one call). Each separate Bash call is a potential permission prompt for the user.
- The polling loop in Step 4 must remain a single Bash invocation — do not break it into multiple calls
