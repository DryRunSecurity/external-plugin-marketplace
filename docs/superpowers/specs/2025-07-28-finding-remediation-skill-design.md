# DryRun Finding Remediation Skill — Design Spec

## Overview

A new self-contained Claude Code plugin that pulls DryRunSecurity findings via the API and remediates them on a fresh branch with a new PR. Supports two paths: PR scan findings and deepscan findings (code + SCA). Unlike the existing `remediation` skill (which works on an already-open PR's comments), this skill pulls findings from the API and creates a brand-new PR with the fixes.

## Plugin Structure

```
plugins/dryrun-finding-remediation/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── dryrun-finding-remediation/
        ├── SKILL.md                         # Core workflow + branching + shared remediation steps
        ├── scripts/
        │   └── dryrun_api.py                # Python 3 API helper (stdlib only)
        └── references/
            ├── PR_REMEDIATION.md            # PR path: API flow + finding data shape
            ├── DEEPSCAN_REMEDIATION.md      # Deepscan path: API flow + finding data shape
            ├── SCA_REMEDIATION.md           # SCA path: API flow + advisory research + escalating verification
            ├── PR_WORKFLOW.md               # Inlined PR creation workflow (from dryrun-pr-review)
            ├── VULNERABILITY_TYPES.md       # CWE references + supported categories (duplicated from remediation skill)
            └── DRYRUN_FILTERING.md          # What DRS flags/doesn't flag (duplicated from remediation skill)
```

### Self-Contained Design

The plugin must work standalone — no dependency on `dryrun-remediation` or `dryrun-pr-review` being installed. Content from both existing skills is duplicated into this plugin:

- **From `remediation` skill**: 5-step remediation process (inlined into SKILL.md body), VULNERABILITY_TYPES.md, DRYRUN_FILTERING.md
- **From `dryrun-pr-review` skill**: Full PR creation workflow (inlined into references/PR_WORKFLOW.md)
- **Not duplicated**: FINDING_FORMAT.md (describes GitHub comment format — not applicable since we pull from API, not comments)

## plugin.json

```json
{
  "name": "dryrun-finding-remediation",
  "description": "Pull DryRunSecurity findings via API and remediate them on a fresh branch with a new PR. Supports PR scan findings, deepscan code findings, and SCA advisory findings.",
  "version": "1.0.0",
  "author": { "name": "DryRunSecurity" },
  "keywords": ["security", "remediation", "findings", "sca", "deepscan", "dryrunsecurity", "api"]
}
```

## SKILL.md Frontmatter

- `name`: `dryrun-finding-remediation`
- `description`: Trigger when user wants to remediate DryRun Deepscan findings or merged pull request findings. Activates when the user asks to fix findings from a deepscan or from a pull request that has already been scanned, and wants to open a fresh PR with the fixes. Covers both code vulnerabilities (deepscan + PR) and SCA advisory findings (deepscan only).
- `license`: Proprietary
- `compatibility`: claude-code, cursor, windsurf, cline, aider
- `allowed_tools`: Read, Edit, Write, Glob, Grep, Bash, WebFetch

## SKILL.md Body — Core Workflow

### Step 0: Determine Account ID

The API requires an `account_id` for all endpoints.

- If the account_id is known from conversation context, use it directly.
- Otherwise: run `python3 dryrun_api.py list-accounts` → present the list (account_id, org_name, provider_type, active) → user picks the account.
- Hold the `account_id` in context for the rest of the session.

### Step 1: Ask Which Finding Source

Ask the user:

> Would you like to remediate **PR findings** or **Deepscan findings**?

- **PR findings** → proceed to PR path (see `references/PR_REMEDIATION.md`)
- **Deepscan findings** → ask sub-question:

  > Would you like to remediate **SCA (dependency) findings** or **code findings**?
  - **SCA** → proceed to SCA path (see `references/SCA_REMEDIATION.md`)
  - **Code** → proceed to deepscan code path (see `references/DEEPSCAN_REMEDIATION.md`)

### Step 2: Pull Findings (Path-Specific)

Each path's reference file documents the exact API call sequence and finding data shape. The agent runs `dryrun_api.py` with the appropriate commands.

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

For deepscan findings, the latest deepscan includes a `branch` field — the agent should branch from that branch (or main if null).

### Step 5: Remediate (Inlined 5-Step Process)

Adapted from the existing `remediation` skill:

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

Follow the workflow in `references/PR_WORKFLOW.md` for:
- Platform detection (GitHub vs GitLab)
- Branch creation
- Stage & commit
- Push & open PR
- Poll for DryRunSecurity review comments
- Present findings to user for decisions

### Commit Format

```
fix: <description>

Co-authored-by: DryRunSecurity <noreply@dryrun.security>
```

### Script Usage Summary

The `scripts/dryrun_api.py` script is the interface to the DryRunSecurity API. It reads the API key from the `DRYRUN_API_KEY` environment variable.

| Command | Required Flags | Optional Flags | Purpose |
|---------|---------------|----------------|---------|
| `list-accounts` | (none) | (none) | List accessible accounts |
| `list-repos` | `--account-id` | `--page`, `--per-page` | List repos for an account |
| `list-scans` | `--account-id`, `--repo-id` | `--page`, `--per-page`, `--severity`, `--pr-number` | List PR scans for a repo |
| `get-scan` | `--account-id`, `--repo-id`, `--scan-id` | `--page`, `--per-page`, `--findings-result` | Get detailed scan findings |
| `list-deepscans` | `--account-id`, `--repo-id` | (none) | List deepscans (auto-picks latest) |
| `get-deepscan-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get deepscan code findings |
| `get-sca-results` | `--account-id`, `--repo-id`, `--deepscan-id` | `--severity`, `--page`, `--per-page` | Get SCA findings |

## Python API Script (`scripts/dryrun_api.py`)

### Design

- **Language**: Python 3, stdlib only (`urllib`, `json`, `argparse`, `sys`, `os`)
- **No pip dependencies**
- **API key**: Read from `DRYRUN_API_KEY` environment variable
- **Base URL**: `https://simple-api.dryrun.security`
- **Auth**: Bearer token (`Authorization: Bearer <key>`)
- **Output**: JSON to stdout, `json.dumps(indent=2)`
- **Error handling**: Missing env var → clear error + exit 1. HTTP errors → status code + response body. 404 → "not found" guidance.

### Commands

#### `list-accounts`
- Endpoint: `GET /v1/accounts`
- Returns: array of `{ account_id, org_id, org_name, provider_type, active, created_at }`

#### `list-repos --account-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories`
- Returns: array of `{ id, name, provider_repo_id, configuration_id, enabled, created_at }`
- Flags: `--page` (default 1), `--per-page` (default 50, max 100)

#### `list-scans --account-id <id> --repo-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories/{repo_id}/scans`
- Returns: array of `{ scan_id, dashboard_url, pr_number, pr_title, pr_status, scan_date, status, summary, risk_threshold }`
- Flags: `--page`, `--per-page`, `--severity` (comma-separated: critical,high,medium,low), `--pr-number` (filter by PR number)

#### `get-scan --account-id <id> --repo-id <id> --scan-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories/{repo_id}/scans/{scan_id}`
- Returns: `{ scan_id, pr_number, pr_title, findings: [...], findings_count }` where each finding is `{ id, dashboard_url, type, label, severity, confidence, description, filename, line_start, line_end, meta }`
- Flags: `--findings-result` (comma-separated: failing,risky,info), `--page`, `--per-page`

#### `list-deepscans --account-id <id> --repo-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories/{repo_id}/deepscans`
- Returns: only the latest deepscan `{ id, branch, commit_sha, created_at }` (sorted by created_at desc, first result only)
- No pagination needed — just returns the latest.

#### `get-deepscan-results --account-id <id> --repo-id <id> --deepscan-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories/{repo_id}/deepscans/{deepscan_id}/results`
- Returns: `{ dashboard_url, data: [...] }` where each finding is `{ id, dashboard_url, title, description, severity, technical_details, impact, remediation, locations, created_at }`
- Flags: `--severity` (comma-separated), `--page`, `--per-page`

#### `get-sca-results --account-id <id> --repo-id <id> --deepscan-id <id>`
- Endpoint: `GET /v1/accounts/{id}/repositories/{repo_id}/deepscans/{deepscan_id}/sca_results`
- Returns: `{ dashboard_url, data: [...] }` where each finding is `{ id, dashboard_url, title, description, severity, package_name, package_version, package_ecosystem, cve_id, cvss_score, cvss_vector, fixed_version, remediation, references, locations, created_at }`
- Flags: `--severity` (comma-separated), `--page`, `--per-page`

### Pagination

All list commands support `--page` (default 1) and `--per-page` (default 50, max 100). When the API returns pagination info (`total`, `page`, `per_page`, `total_pages`), the script prints it alongside the data so the agent knows if more pages exist.

## Reference Files

### `references/PR_REMEDIATION.md`

1. **API call sequence:**
   - `list-repos --account-id <id>` → present repos (name, id, enabled), user picks
   - `list-scans --account-id <id> --repo-id <id>` → present PR list (pr_number, pr_title, scan_date, risk_threshold), user picks
   - `get-scan --account-id <id> --repo-id <id> --scan-id <id>` → get findings array

2. **Finding data shape:** `id`, `dashboard_url`, `type`, `label`, `severity`, `confidence`, `description`, `filename`, `line_start`, `line_end`, `meta`

3. **Presentation format:**
   ```
   [N] [severity] type in filename:line_start-line_end
       description (truncated if long)
   ```

4. **Note:** These are findings from a PR scan (the PR may be merged or still open). The remediation creates a *fresh* PR, not a commit to the existing one.

### `references/DEEPSCAN_REMEDIATION.md`

1. **API call sequence:**
   - `list-repos --account-id <id>` → present repos, user picks
   - `list-deepscans --account-id <id> --repo-id <id>` → script auto-returns latest deepscan (id + branch)
   - `get-deepscan-results --account-id <id> --repo-id <id> --deepscan-id <id>` → get findings array

2. **Finding data shape:** `id`, `dashboard_url`, `title`, `description`, `severity`, `technical_details`, `impact`, `remediation`, `locations`, `created_at`

3. **Key difference from PR path:** Deepscan findings include `technical_details`, `impact`, and `remediation` fields — richer context. The agent should use `remediation` as a starting point but still research authoritative sources and verify against the codebase.

4. **Branch context:** The latest deepscan has a `branch` field — the agent should branch from that same branch (or main if null) when creating the fix PR.

### `references/SCA_REMEDIATION.md`

1. **API call sequence:**
   - `list-repos --account-id <id>` → present repos, user picks
   - `list-deepscans --account-id <id> --repo-id <id>` → script auto-returns latest deepscan
   - `get-sca-results --account-id <id> --repo-id <id> --deepscan-id <id>` → get SCA findings array

2. **Finding data shape:** `id`, `dashboard_url`, `title`, `description`, `severity`, `package_name`, `package_version`, `package_ecosystem`, `cve_id`, `cvss_score`, `cvss_vector`, `fixed_version`, `remediation`, `references`, `locations`, `created_at`

3. **SCA-specific remediation workflow (escalating verification):**

   **Step 1: Verify the package is actually used**
   - Grep for the package name in import/require statements across the codebase
   - If not found → flag as potential false positive, ask user

   **Step 2: Check for vulnerable function usage (if advisory names specifics)**
   - Fetch the advisory/CVE details (use `references` array URLs from the finding, or WebFetch the CVE)
   - Look for specific vulnerable functions/APIs/patterns mentioned in the advisory
   - Grep the codebase for those function names
   - If vulnerable function not used → lower priority, inform user it may not be exploitable

   **Step 3: Determine remediation approach**
   - **Option A: Upgrade the dependency** — if `fixed_version` is available, update the lockfile/manifest (package.json, requirements.txt, go.mod, etc.) to the fixed version. Run the package manager to update.
   - **Option B: Add code mitigation** — if no fixed version available, or upgrading is risky (breaking changes), add code to mitigate: avoid the vulnerable function, add input validation, wrap with a safe alternative, etc.
   - Present both options to the user when applicable, with trade-offs

   **Step 4: Verify the fix**
   - If upgraded: confirm lockfile updated, run install to verify resolution
   - If mitigated: confirm the vulnerable code path is no longer reachable

4. **Ecosystem-specific dependency update guidance:**
   - npm: `npm install package@fixed_version`
   - pip: `pip install package==fixed_version` (or update requirements.txt)
   - go: `go get package@fixed_version`
   - gem: `bundle update package` (or update Gemfile)
   - maven: update version in pom.xml

### `references/PR_WORKFLOW.md`

Inlined from the `dryrun-pr-review` skill. Contains:

1. **Platform detection** — `git remote get-url origin` → GitHub (gh) or GitLab (glab)
2. **Branch creation** — from main/master create new branch, or use existing feature branch
3. **Stage & commit** — selective add, commit with Co-Authored-By
4. **Push & open PR** — push, check for existing PR, create if needed (gh/glab commands)
5. **Poll for DRS review comments** — timestamp-based, up to 10 minutes, 30s interval
6. **Present findings to user** — fetch DRS comments, present for decisions
7. **Act on user decisions** — fix or decline with explanation comment

### `references/VULNERABILITY_TYPES.md`

Duplicated from the existing `remediation` skill. Contains:
- CWE reference table (SQLi=CWE-89, XSS=CWE-79, SSRF=CWE-918, etc.)
- Supported vulnerability categories (web vulns, API security, modern concerns, language-specific, concurrency, crypto)

### `references/DRYRUN_FILTERING.md`

Duplicated from the existing `remediation` skill. Contains:
- What gets filtered out (non-code issues, false positives, sensitive logging FPs, dev/test context, non-security nitpicks)
- What does get reported (real vulnerabilities, exploitable issues, code-change-requiring fixes)
- Trust the finding principle

## Workflow Flowchart

```
Step 0: Determine account_id
  (list-accounts if not known)
         |
         v
Step 1: Ask PR findings or Deepscan findings?
  |                    |
  | PR                 | Deepscan
  v                    v
Step 2a: PR path     Step 2b: Ask SCA or Code?
  |                    |          |
  |                    | SCA      | Code
  |                    v          v
  |               SCA path    Deepscan code path
  |                    |          |
  v                    v          v
Step 3: List findings → user picks which to fix
         |
         v
Step 4: Ask branch name
         |
         v
Step 5: Remediate (gather context → research → apply fix → explain)
         |
         v
Step 6: Create PR (PR_WORKFLOW.md)
```
