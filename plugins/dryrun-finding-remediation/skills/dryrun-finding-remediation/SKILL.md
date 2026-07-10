---
name: dryrun-finding-remediation
description: >-
  Trigger when user wants to remediate DryRun Deepscan findings or merged pull
  request findings. Activates when the user asks to fix findings from a
  deepscan or from a pull request that has already been scanned, and wants to
  open a fresh PR with the fixes. Covers both code vulnerabilities (deepscan +
  PR) and SCA advisory findings (deepscan only). Use when the user mentions
  remediation, fixing, or addressing DryRunSecurity findings, deepscan findings,
  SCA findings, or PR scan results.
license: Proprietary
compatibility: claude-code, cursor, windsurf, cline, aider
allowed-tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - WebFetch
  - Bash
---

# DryRunSecurity Finding Remediation

Pull DryRunSecurity findings via the API and remediate them on a fresh branch with a new PR. Unlike the `remediation` skill (which works on an already-open PR's comments), this skill pulls findings from the API and creates a brand-new PR with the fixes.

**Prerequisite:** The `DRYRUN_API_KEY` environment variable must be set. If missing, tell the user: "Set your API key with `export DRYRUN_API_KEY=your-key`."

## Script Usage

The `scripts/dryrun_api.py` script is the interface to the DryRunSecurity API. It uses Python 3 stdlib only — no pip dependencies.

```bash
python3 scripts/dryrun_api.py <command> [flags]
```

| Command | Required Flags | Optional Flags | Purpose |
|---------|---------------|----------------|---------|
| `list-accounts` | (none) | (none) | List accessible accounts |
| `list-repos` | `--account-id` | `--page`, `--per-page` | List repos for an account |
| `list-scans` | `--account-id`, `--repo-id` | `--page`, `--per-page`, `--severity`, `--pr-number`, `--date-from`, `--date-to` | List PR scans for a repo |
| `get-scan` | `--account-id`, `--repo-id`, `--scan-id` | `--findings-result`, `--page`, `--per-page` | Get detailed scan findings |
| `list-deepscans` | `--account-id`, `--repo-id` | (none) | Get latest deepscan for a repo |
| `get-deepscan-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get deepscan code findings |
| `get-sca-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get SCA findings |

All commands output JSON to stdout. Pagination info is included when the API returns it (`total`, `page`, `per_page`, `total_pages`).

## Workflow

### Step 0: Determine Account ID

The API requires an `account_id` for all endpoints.

- If the account_id is known from conversation context, use it directly.
- Otherwise: run `python3 scripts/dryrun_api.py list-accounts` and present the list to the user. Each account shows `account_id`, `org_name`, `provider_type`, and `active` status.
- Ask the user which account to use. Hold the `account_id` in context for the rest of the session.

### Step 1: Ask Which Finding Source

Ask the user:

> Would you like to remediate **PR findings** or **Deepscan findings**?

- **PR findings** → read `references/PR_REMEDIATION.md` and follow that path
- **Deepscan findings** → ask the sub-question:

  > Would you like to remediate **SCA (dependency) findings** or **code findings**?
  - **SCA** → read `references/SCA_REMEDIATION.md` and follow that path
  - **Code** → read `references/DEEPSCAN_REMEDIATION.md` and follow that path

### Step 2: Pull Findings

Follow the API call sequence in the chosen reference file. Each file documents the exact `dryrun_api.py` commands to run and the finding data shape for that path.

### Step 3: List Findings & User Selects

Present findings as a numbered list:

```
[N] [severity] type in filename:line_start-line_end
    description (truncated if long)
```

For SCA findings, also show package name, version, CVE, and fixed version:

```
[N] [severity] CVE-XXXX in package@version (ecosystem)
    fixed version: X.Y.Z
    description (truncated if long)
```

Ask the user which findings to fix. The user may select one or multiple.

### Step 4: Ask Branch Name

Ask the user what the branch name should be. Default suggestion: `fix/<finding-type>-<short-description>`.

For deepscan findings, the latest deepscan includes a `branch` field — branch from that branch (or main if null) when creating the fix.

### Step 5: Remediate

For each finding the user selected, follow this process:

#### 5a: Parse the Finding

Extract vulnerability type, file path, line numbers, and description from the API response. Each path's reference file documents the available fields.

#### 5b: Gather Codebase Context

Use Glob and Grep to search, Read to examine. Do NOT propose a fix until complete.

| Area | Search For |
|------|------------|
| **Config files** | `.env`, `package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml` |
| **Auth patterns** | `auth.py`, `authentication.rb`, `jwt.go`, `passport.js` |
| **Authz patterns** | Permission models, RBAC, policy files |
| **Decorators** | `@login_required`, `@requires_auth`, `requireAuth()`, `checkPermission()` |
| **Similar code** | How does this codebase handle similar operations securely? |

**Trust the finding** — DryRunSecurity rigorously filters false positives. See `references/DRYRUN_FILTERING.md` for details.

#### 5c: Research the Authoritative Fix

Use WebFetch to look up official documentation. Do NOT rely on memorized examples.

Research sources:
1. **Official framework docs** — "[framework] [vulnerability] prevention" (Django, Rails, GORM, Prisma, Express)
2. **OWASP Cheat Sheets** — General vulnerability guidance
3. **CWE references** — See `references/VULNERABILITY_TYPES.md`

Use docs for their specific framework version — security APIs change between versions.

#### 5d: Apply a Contextual Fix

Use Edit to make the minimal change necessary.

Requirements:
- Match existing patterns in the codebase
- Use existing utilities, decorators, and middleware
- Preserve functionality
- Be framework-idiomatic

#### 5e: Explain and Verify

Include:
1. Why the original code was vulnerable (attack scenario)
2. Why the fix works (reference authoritative source)
3. How it matches existing patterns
4. Verification steps
5. Related code that may need similar fixes

### Step 6: Create PR

Read `references/PR_WORKFLOW.md` and follow the full PR creation workflow:
- Platform detection (GitHub vs GitLab)
- Branch creation (from the branch identified in Step 4)
- Stage & commit
- Push & open PR
- Poll for DryRunSecurity review comments
- Present findings to user for decisions

### Commit Format

```
fix: <description>

Co-authored-by: DryRunSecurity <noreply@dryrun.security>
```

## Example

**Finding from API:** "SQL Injection in `app/handlers/search.go:45`"

**Before (vulnerable):**
```go
db.Raw("SELECT * FROM users WHERE name = '" + input + "'")
```

**After (fixed):**
```go
db.Where("name = ?", input).Find(&users)
```

**Research URLs:**
- `https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html`
- `https://gorm.io/docs/security.html`
