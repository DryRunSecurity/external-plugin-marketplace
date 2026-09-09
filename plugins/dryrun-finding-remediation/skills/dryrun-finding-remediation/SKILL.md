---
name: dryrun-finding-remediation
description: >-
  Retrieve and remediate DryRunSecurity findings, including one or multiple
  specific finding IDs. Use when the user asks to fix or propose fixes for
  PR scan findings, deepscan code findings, or SCA dependency findings.
  Resolve supplied finding IDs directly, or guide finding selection when
  IDs are unknown. Apply contextual fixes and create a fresh remediation PR
  when requested.
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

Pull DryRunSecurity findings via the API and apply contextual fixes. Unlike the `remediation` skill (which works on an already-open PR's comments), this skill retrieves findings by ID or scan and can create a fresh remediation PR.

Honor the requested delivery: for proposed fixes only, do not edit files, create a branch, commit, push, or open a PR. If edits are requested without commits, make the requested edits but do not commit, push, or open a PR. Honor any instruction to stay on the current branch. Do not repeat questions already answered in the request.

**Prerequisite:** The `DRYRUN_API_KEY` environment variable must be set. If missing, tell the user: "Set your API key with `export DRYRUN_API_KEY=your-key`." Never print its value.

## Script Usage

The `scripts/dryrun_api.py` script uses Python 3 stdlib only. Resolve it relative to this installed skill directory, not the repository being remediated. Examples below use skill-relative paths.

```bash
python3 scripts/dryrun_api.py <command> [flags]
```

Default API origin: `https://simple-api.dryrun.security`. Honor `DRYRUN_API_BASE_URL` when supplied, for example `https://simple-api.sb.dryrun.security`. It must be an HTTPS origin without credentials, a path, query, or fragment; redirects are not followed.

| Command | Required Flags | Optional Flags | Purpose |
|---------|---------------|----------------|---------|
| `list-accounts` | (none) | (none) | List accessible accounts |
| `get-finding` | `--account-id`, `--finding-id` | `--finding-type` | Get one exact finding, including source metadata |
| `list-repos` | `--account-id` | `--page`, `--per-page` | List repos for an account |
| `list-scans` | `--account-id`, `--repo-id` | `--page`, `--per-page`, `--severity`, `--pr-number`, `--date-from`, `--date-to` | List PR scans for a repo |
| `get-scan` | `--account-id`, `--repo-id`, `--scan-id` | `--findings-result`, `--page`, `--per-page` | Get detailed scan findings |
| `list-deepscans` | `--account-id`, `--repo-id` | (none) | Get latest deepscan for a repo |
| `get-deepscan-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get deepscan code findings |
| `get-sca-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get SCA findings |

Successful commands output JSON to stdout. `get-finding` returns `{ "data": { ... } }` without removing null fields. HTTP/connection failures return JSON and exit nonzero; invalid CLI arguments are rejected before a request. Never treat an error as an empty finding list.

## Workflow

### Step 0: Determine Account ID

All commands except `list-accounts` require an `account_id`.

- Use the account ID already supplied in the request or conversation.
- Otherwise run `list-accounts`. Use the sole accessible account when unambiguous; if there are multiple, present `account_id`, `org_name`, `provider_type`, and `active` and ask which to use.

### Specific Finding IDs

When the user supplies one or multiple finding IDs, read [Finding ID Remediation](references/FINDING_ID_REMEDIATION.md). Deduplicate the IDs and call `get-finding` for each. These IDs are already the user's selection: skip Steps 1–3, including repository/scan selection and asking which findings to fix. Resolve every requested ID and validate repository/source metadata before continuing to Step 4.

### Step 1: Ask Which Finding Source

If IDs were not supplied, use the known source or ask:

> Would you like to remediate **PR findings** or **Deepscan findings**?

- **PR findings** → read `references/PR_REMEDIATION.md` and follow that path
- **Deepscan findings** → use the known type or ask:

  > Would you like to remediate **SCA (dependency) findings** or **code findings**?
  - **SCA** → read `references/SCA_REMEDIATION.md` and follow that path
  - **Code** → read `references/DEEPSCAN_REMEDIATION.md` and follow that path

### Step 2: Pull Findings

Follow the API call sequence in the chosen reference file. Each file documents the exact `dryrun_api.py` commands to run and the finding data shape for that path.

### Step 3: List Findings & User Selects

Present findings as a numbered list with ID, severity, type, file/line range, and a short description. For SCA findings also show package name, affected versions, advisory ID, and fixed version. Ask which findings to fix unless the user has already selected them.

### Step 4: Prepare the Remediation Branch

For proposals only, keep the current checkout and skip branch creation.

Otherwise honor the supplied branch name and base branch. Ask only for missing decisions; suggest `fix/<finding-type>-<short-description>` for the new branch. If no base was supplied, use the scanned branch when available or the repository's default branch. Resolve conflicting source branches before combining findings.

Verify the intended repository and current worktree before switching. Preserve unrelated changes. Create the requested fresh branch from the agreed base **before editing**, or reuse it if it is already the explicitly selected remediation branch. Do not substitute an unrelated current feature branch. Treat the scanned SHA as provenance, not a requirement to branch from an old commit.

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

Use the finding's evidence and verify whether the vulnerable behavior still exists on the chosen base, especially for historical, resolved, or dismissed findings. Explain already-fixed findings rather than manufacturing changes. See `references/DRYRUN_FILTERING.md` for code-finding filtering; SCA uses dependency-specific guidance.

#### 5c: Research the Authoritative Fix

Use WebFetch to look up official documentation. Do NOT rely on memorized examples.

Research sources:
1. **Official framework docs** — "[framework] [vulnerability] prevention" (Django, Rails, GORM, Prisma, Express)
2. **OWASP Cheat Sheets** — General vulnerability guidance
3. **CWE references** — See `references/VULNERABILITY_TYPES.md`

Use docs for their specific framework version — security APIs change between versions.

#### 5d: Apply a Contextual Fix

For proposals only, describe the minimal patch without editing. Otherwise use Edit to make the minimal change necessary.

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

Skip this step for proposals only or when commits/PR creation were not authorized. Otherwise read `references/PR_WORKFLOW.md` and follow the PR creation workflow:
- Platform detection (GitHub vs GitLab)
- Verify the remediation branch already prepared in Step 4; do not switch bases after editing
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
