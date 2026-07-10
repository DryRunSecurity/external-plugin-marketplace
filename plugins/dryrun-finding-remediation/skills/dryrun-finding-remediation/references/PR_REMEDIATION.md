# PR Findings Remediation Path

## API Call Sequence

### 1. List Repositories

```bash
python3 scripts/dryrun_api.py list-repos --account-id <account_id>
```

Present the repos to the user. Each repo has: `id`, `name`, `provider_repo_id`, `enabled`, `configuration_id`. Ask the user which repo to use. Store the `repo_id`.

### 2. List PR Scans

```bash
python3 scripts/dryrun_api.py list-scans --account-id <account_id> --repo-id <repo_id>
```

Present the scans to the user. Each scan has:

| Field | Description |
|-------|-------------|
| `scan_id` | UUID — used to get detailed results |
| `dashboard_url` | URL to view in DryRun Security dashboard |
| `pr_number` | Pull request number |
| `pr_title` | Pull request title |
| `pr_status` | Pull request status |
| `scan_date` | When the scan was performed |
| `status` | Scan status |
| `summary` | Developer-facing scan summary |
| `risk_threshold` | Risk level (fail, risk, info) |

Present as:
```
[N] PR #<pr_number>: <pr_title>
    scanned: <scan_date> | risk: <risk_threshold> | status: <status>
```

Ask the user which PR scan to use. Store the `scan_id`.

### 3. Get Detailed Scan Results

```bash
python3 scripts/dryrun_api.py get-scan --account-id <account_id> --repo-id <repo_id> --scan-id <scan_id>
```

Optionally filter by findings result:
```bash
python3 scripts/dryrun_api.py get-scan --account-id <account_id> --repo-id <repo_id> --scan-id <scan_id> --findings-result failing,risky
```

## Finding Data Shape

Each finding in the response has:

| Field | Description |
|-------|-------------|
| `id` | Finding UUID |
| `dashboard_url` | URL to view in DryRun Security risk register |
| `type` | Finding type/title (e.g., "SQL Injection") |
| `label` | Classifier label (e.g., `sqli`, `auth_bypass`, `idor`) |
| `severity` | Finding severity (critical, high, medium, low) |
| `confidence` | Confidence level |
| `description` | Detailed explanation of the vulnerability |
| `filename` | File path where the finding was detected |
| `line_start` | Starting line number |
| `line_end` | Ending line number |
| `meta` | Additional metadata (object, may be null) |

## Presentation Format

Present findings as:
```
[N] [severity] type in filename:line_start-line_end
    description (truncated if long)
```

## Important Note

These are findings from a PR scan — the PR may be merged or still open. The remediation creates a **fresh PR**, not a commit to the existing one. The existing PR is only the source of the finding data.
