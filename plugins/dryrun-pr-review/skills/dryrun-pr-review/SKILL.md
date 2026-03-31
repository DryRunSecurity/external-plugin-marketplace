---
name: dryrun-pr-review
description: Use when the user asks to create a PR, open a pull request, submit for review, or push changes for review
---

# DryRunSecurity PR Review Workflow

Full PR/MR lifecycle: detect platform, branch, commit, open PR or MR, poll for DryRunSecurity comments, present findings to the user.

## Platform Detection

Run this first. All subsequent steps reference `$PLATFORM`, `$MR_NUMBER`, and `$PROJECT`.

```bash
REMOTE_URL=$(git remote get-url origin)

if echo "$REMOTE_URL" | grep -q "github.com"; then
  PLATFORM="github"
else
  PLATFORM="gitlab"
fi
```

## Getting Repo Info

```bash
# GitHub
OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')
OWNER=$(echo "$OWNER_REPO" | cut -d'/' -f1)
REPO=$(echo "$OWNER_REPO" | cut -d'/' -f2)

# GitLab — parse and URL-encode the project path for API calls
PROJECT=$(git remote get-url origin \
  | sed -E 's|.*[:/]([^/]+/[^/]+?)(\.git)?$|\1|' \
  | sed 's|/|%2F|g')
```

## Branch Naming

Format: `{user}/{type}/{descriptive-name}`

- **user**: Infer from `git branch -r | grep -oE 'origin/([a-z]+)/' | sort -u | head -5`, or from `git config user.name`/`git config user.email`
- **type**: `feat`, `fix`, or `chore`
- **name**: kebab-case description

Example: `petek/feat/add-user-authentication`

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`

## Workflow

### 1. Branch

If on `main`/`master`, create a new branch. Otherwise use the existing feature branch.

```bash
git branch -r | grep -oE 'origin/([a-z]+)/' | sort -u | head -5
git config user.name && git config user.email
```

### 2. Stage & Commit

```bash
git status
git add <files>   # selective — never commit secrets or generated files
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 3. Push & Create PR/MR

```bash
git push -u origin <branch-name>
```

```bash
# GitHub
gh pr create --title "<type>(<scope>): <description>" --body "$(cat <<'EOF'
## Summary
<bullet points>

## Test plan
<how to verify>

EOF
)"

# GitLab
glab mr create --title "<type>(<scope>): <description>" --description "$(cat <<'EOF'
## Summary
<bullet points>

## Test plan
<how to verify>

EOF
)"
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
git commit -m "fix: address DryRunSecurity finding - <description>"
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
