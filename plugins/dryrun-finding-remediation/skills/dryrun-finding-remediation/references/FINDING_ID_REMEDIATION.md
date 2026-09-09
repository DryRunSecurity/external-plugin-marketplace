# Remediate Specific Finding IDs

## Resolve the Selection

Use the supplied account ID and deduplicate the requested UUIDs case-insensitively, preserving their order. A UUID identifies a finding, not a scan, repository, or CVE. Do not guess IDs from unrelated UUIDs in surrounding text.

Fetch each requested finding separately:

```bash
python3 scripts/dryrun_api.py get-finding --account-id <account_id> --finding-id <finding_id>
```

The helper calls `GET /v1/accounts/{account_id}/findings/{finding_id}` and returns the canonical finding under `data`. No repository ID, scan ID, or finding type is required. Do not replace an exact lookup with listing the latest scan or searching all accounts.

Honor an explicitly supplied finding type. Otherwise omit the filter and let the endpoint detect it:

```bash
python3 scripts/dryrun_api.py get-finding --account-id <account_id> --finding-id <finding_id> --finding-type sca
```

Only `pullrequest`, `deepscan`, and `sca` are supported. On HTTP 409, ask which of these types the user intended unless already known, then retry with that exact filter. Do not guess or retry every type. Code policy findings are not supported.

Resolve all IDs before editing. Report each failed lookup and stop until the selection is corrected or the user explicitly excludes that finding. Never silently remediate only the successful subset. Distinguish invalid input (400), missing credentials (401), unauthorized account (403), absent/inaccessible/deleted or wrong-type finding (404), ambiguous ID (409), and backend failure (500). A 404 is not permission to use a similar finding.

## Validate Repository and Source

For every response:

- Confirm `data.id` and `data.account_id` match the request and `finding_type` is supported.
- Match `repository_full_name` and, where available, `provider_repo_id` against the intended repository/provider identity. Retain `repository_id`. If identity cannot be established, ask before editing; do not infer it from a filename or short repository name alone.
- Keep one repository and one agreed base branch per remediation PR. Separate cross-repository requests and resolve differing scanned branches with the user before changing files.
- Record `scan_id`, `branch`, `commit_sha`, `pr_number`, and `dashboard_url`. Preserve nulls. Never describe the current checkout or PR head as the scanned revision.
- State when `state` is `resolved` or `dismissed`, or `from_latest_scan` is false. Read `triage` and verify whether the vulnerable behavior still exists on the chosen base. Do not silently discard an explicitly requested finding or manufacture a change if it is already fixed. Do not alter triage.

PR and deepscan code IDs describe their original stored occurrence. Persistent SCA IDs use the newest stored occurrence and all its version occurrences; advisory guidance and triage are current values. Historical IDs remain valid even when absent from newer scans, but deleted/deduplicated IDs have no alias lookup.

## Interpret the Returned Finding

Use `finding_type` to choose the remediation guidance. The finding has already been retrieved: skip the reference's repository/scan-selection and API-listing steps.

| `finding_type` | Details to use | Guidance |
|---|---|---|
| `pullrequest` | `type`, `label`, `description`, `filename`, `line_start`, `line_end`, `meta`, `investigation_details`, `severity_details` | `PR_REMEDIATION.md` |
| `deepscan` | `title`, `description`, `technical_details`, `impact`, `remediation`, `locations` | `DEEPSCAN_REMEDIATION.md` |
| `sca` | `title`, `package_name`, `package_ecosystem`, versions, advisory details, `verification_rationale`, `fixed_version`, `remediation`, `locations`, `references` | `SCA_REMEDIATION.md`, starting at SCA-Specific Remediation Workflow |

For SCA, inspect every `version_occurrences` entry and its `package_version`/`locations`, not just the singular `package_version`. A null singular version can mean multiple affected versions. `package_versions` includes every distinct version in the selected result; `locations` is their union. Empty version arrays and null source metadata can mean no valid occurrence remains, not an unaffected package. Verify the current dependency tree and lockfiles before proposing an upgrade.

`cve_id` may contain a GHSA, OSV, or other advisory identifier. References can be URL strings or legacy objects; extract actual advisory URLs rather than assuming one fixed shape. Location objects retain their stored format, so inspect their path and line fields rather than inventing ranges.

Return to Step 4 of the main skill. Honor supplied branch/base choices and proposal-only requests. The supplied finding IDs are already selected; do not ask the user to select them again.
