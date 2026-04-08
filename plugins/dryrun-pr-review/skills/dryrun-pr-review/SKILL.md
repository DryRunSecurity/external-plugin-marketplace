---
name: dryrun-pr-review
version: 1.0.0
description: >-
  Manages the full PR/MR lifecycle for DryRunSecurity users. Activates when
  the user asks to create a PR or MR, submit changes for review, push for review,
  or open a pull request. Detects GitHub vs GitLab automatically, discovers repo
  conventions, then branches, commits, pushes, opens the PR/MR, and polls for
  DryRunSecurity review comments.
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
  - Write
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

Run this first as a single script. All subsequent steps reference `$PLATFORM`, `$OWNER`, `$REPO`, `$PROJECT`, `$MR_NUMBER`.

```bash
REMOTE_URL=$(git remote get-url origin)

if echo "$REMOTE_URL" | grep -q "github.com"; then
  PLATFORM="github"
  OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')
  OWNER=$(echo "$OWNER_REPO" | cut -d'/' -f1)
  REPO=$(echo "$OWNER_REPO" | cut -d'/' -f2)
else
  PLATFORM="gitlab"
  PROJECT=$(git remote get-url origin \
    | sed -E 's|.*[:/]([^/]+/[^/]+?)(\.git)?$|\1|' \
    | sed 's|/|%2F|g')
fi
```

## Convention Discovery

First, check for a saved conventions file:

```bash
cat .claude/pr-conventions.md 2>/dev/null
```

**If the file exists**, read it and use those conventions — skip the rest of this section.

**If the file does not exist**, discover conventions from the repo in a single script:

```bash
echo "=== Recent branches ===" && git branch -r | grep -v HEAD | tail -20
echo "=== Recent commits ===" && git log --oneline -20
echo "=== Git identity ===" && git config user.name && git config user.email

# Existing PR/MR title and body patterns (platform-specific)
if [ "$PLATFORM" = "github" ]; then
  echo "=== Recent PRs ===" && gh pr list --state all --limit 5 --json number,title,body
else
  echo "=== Recent MRs ===" && glab mr list --state all --limit 5
fi
```

From this, determine:
- **Branch name**: match the pattern already in use (e.g., `user/type/name`, `type/description`, `feature/ticket-123`)
- **Commit message format**: match what's in `git log` (Conventional Commits, imperative sentence, ticket prefix, etc.)
- **PR/MR title and body structure**: match existing PRs/MRs — sections used, level of detail, any templates

If the repo has no established conventions, use sensible defaults: `type/short-description` for branches, short imperative sentences for commits.

**After discovering conventions**, summarize what you found and ask the user:

> "I've detected the following conventions for this repo:
> - **Branches**: `<pattern>`
> - **Commits**: `<format>`
> - **PR/MR body**: `<structure>`
>
> Would you like me to save these to `.claude/pr-conventions.md` so I don't need to re-detect them next time? You can edit the file at any time to override."

If the user agrees, write the file:

```bash
mkdir -p .claude
# Write .claude/pr-conventions.md with the discovered conventions
```

The file format should be human-readable so the user can edit it directly. Example:

```markdown
# PR/MR Conventions
# Auto-detected by dryrun-pr-review. Edit to override.

## Branch naming
<detected pattern and example>

## Commit messages
<detected format and example>

## PR/MR body
<detected structure>
```

Always append to commits:
```
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Workflow

### 1. Branch

If on `main`/`master`, create a new branch following the discovered naming convention. Otherwise use the existing feature branch.

### 2. Stage & Commit

```bash
git status
git add <files>   # selective — never commit secrets or generated files
git commit -m "<message following discovered convention>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Push & Create PR/MR

```bash
git push -u origin <branch-name>
```

Create the PR/MR with a title and body that match the style of existing PRs/MRs in this repo:

```bash
# GitHub
gh pr create --title "<title>" --body "<body>"

# GitLab
glab mr create --title "<title>" --description "<body>"
```

Capture the PR/MR number from output and store as `MR_NUMBER`.

### 4. Poll for DryRunSecurity Review Comments

Poll for up to **10 minutes** (every 30 seconds). Use timestamp-based polling — not count-based. Comments can be edited/replaced.

```bash
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_EPOCH=$(date +%s)
TIMEOUT=600
POLL_INTERVAL=30

while true; do
    ELAPSED=$(( $(date +%s) - START_EPOCH ))
    [ $ELAPSED -ge $TIMEOUT ] && echo "Timeout." && break

    if [ "$PLATFORM" = "github" ]; then
        DRS_NEW=$(gh api repos/${OWNER}/${REPO}/issues/${MR_NUMBER}/comments \
          --jq "[.[] | select((.user.login == \"dryrunsecurity\" or .user.login == \"dryrunsecurity[bot]\") and .created_at > \"${START_TIME}\")] | length")

        DRS_REVIEWS=$(gh api repos/${OWNER}/${REPO}/pulls/${MR_NUMBER}/reviews \
          --jq "[.[] | select((.user.login | test(\"dryrunsecurity\"; \"i\")) and .submitted_at > \"${START_TIME}\")] | length")

        echo "DRS comments: $DRS_NEW, DRS reviews: $DRS_REVIEWS (${ELAPSED}s elapsed)"
    else
        DRS_NEW=$(glab api projects/${PROJECT}/merge_requests/${MR_NUMBER}/notes \
          --jq "[.[] | select((.author.username == \"dryrunsecurity\") and .created_at > \"${START_TIME}\")] | length")

        echo "DRS notes: $DRS_NEW (${ELAPSED}s elapsed)"
    fi

    sleep $POLL_INTERVAL
done
```

Timeout with no new comments = review complete, proceed.

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
  --jq '.[] | select(.author.username == "dryrunsecurity") | {id: .id, body: .body}'
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
git commit -m "<message following discovered convention — addressing DryRunSecurity finding>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

For comments the user wants to decline:
```bash
# GitHub
gh api repos/${OWNER}/${REPO}/pulls/${MR_NUMBER}/comments/${COMMENT_ID}/replies \
  -f body="Not addressing: <explanation>"

# GitLab
glab api projects/${PROJECT}/merge_requests/${MR_NUMBER}/notes \
  -f body="Not addressing: <explanation>"
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
