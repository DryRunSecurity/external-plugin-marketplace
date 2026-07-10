# Deepscan Code Findings Remediation Path

## API Call Sequence

### 1. List Repositories

```bash
python3 scripts/dryrun_api.py list-repos --account-id <account_id>
```

Present the repos to the user. Each repo has: `id`, `name`, `provider_repo_id`, `enabled`. Ask the user which repo to use. Store the `repo_id`.

### 2. Get Latest Deepscan

```bash
python3 scripts/dryrun_api.py list-deepscans --account-id <account_id> --repo-id <repo_id>
```

The script automatically picks the latest deepscan and returns:

| Field | Description |
|-------|-------------|
| `id` | Deepscan UUID — used to fetch results |
| `branch` | Branch that was scanned (may be null) |
| `commit_sha` | Commit SHA that was scanned (may be null) |
| `created_at` | When the deepscan was created |
| `type` | Deepscan type |

Store the `deepscan_id` and `branch` for later use.

### 3. Get Deepscan Results

```bash
python3 scripts/dryrun_api.py get-deepscan-results --account-id <account_id> --repo-id <repo_id> --deepscan-id <deepscan_id>
```

Optionally filter by severity:
```bash
python3 scripts/dryrun_api.py get-deepscan-results --account-id <account_id> --repo-id <repo_id> --deepscan-id <deepscan_id> --severity critical,high
```

## Finding Data Shape

Each finding in the response has:

| Field | Description |
|-------|-------------|
| `id` | Finding UUID |
| `dashboard_url` | URL to view in DryRun Security risk register |
| `title` | Finding title |
| `description` | Detailed explanation |
| `severity` | Finding severity (critical, high, medium, low) |
| `technical_details` | Technical details about the vulnerability |
| `impact` | Impact description |
| `remediation` | Suggested remediation (starting point only) |
| `locations` | Array of code locations |
| `created_at` | When the finding was created |

## Key Difference from PR Path

Deepscan findings include `technical_details`, `impact`, and `remediation` fields — richer context than PR findings. Use the `remediation` field as a **starting point** but still:
1. Research authoritative sources (OWASP, framework docs, CWE references)
2. Verify against the actual codebase
3. Apply a fix that matches existing code patterns

Do NOT blindly apply the `remediation` suggestion without verification.

## Branch Context

The latest deepscan has a `branch` field. When creating the fix PR:
- If `branch` is set — branch from that branch
- If `branch` is null — branch from `main` or `master`

This ensures the fix is based on the same code that was scanned.
