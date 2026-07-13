# SCA (Software Composition Analysis) Findings Remediation Path

## API Call Sequence

### 1. List Repositories

```bash
python3 scripts/dryrun_api.py list-repos --account-id <account_id>
```

Present the repos to the user. Ask the user which repo to use. Store the `repo_id`.

### 2. Get Latest Deepscan

```bash
python3 scripts/dryrun_api.py list-deepscans --account-id <account_id> --repo-id <repo_id>
```

The script automatically picks the latest deepscan and returns the `id` and `branch`. Store the `deepscan_id`.

### 3. Get SCA Results

```bash
python3 scripts/dryrun_api.py get-sca-results --account-id <account_id> --repo-id <repo_id> --deepscan-id <deepscan_id>
```

Optionally filter by severity:
```bash
python3 scripts/dryrun_api.py get-sca-results --account-id <account_id> --repo-id <repo_id> --deepscan-id <deepscan_id> --severity critical,high
```

## Finding Data Shape

Each SCA finding in the response has:

| Field | Description |
|-------|-------------|
| `id` | Finding UUID |
| `dashboard_url` | URL to view in DryRun Security risk register |
| `title` | Finding title |
| `description` | Detailed description |
| `severity` | Finding severity (critical, high, medium, low) |
| `package_name` | Vulnerable package name |
| `package_version` | Installed version |
| `package_ecosystem` | Package ecosystem (npm, pip, go, gem, maven, etc.) |
| `cve_id` | CVE identifier (may be null) |
| `cvss_score` | CVSS score (may be null) |
| `cvss_vector` | CVSS vector string (may be null) |
| `fixed_version` | Version that fixes the vulnerability (may be null) |
| `remediation` | Suggested remediation text (may be null) |
| `references` | Array of reference URLs (advisory pages, CVE details) |
| `locations` | Array of code locations where the package is used |
| `created_at` | When the finding was created |

## SCA-Specific Remediation Workflow

SCA remediation differs from code vulnerability remediation. Follow this escalating verification process:

### Step 1: Verify the Package Is Actually Used

- Grep for the package name in import/require/use statements across the codebase
- Check the `locations` array from the finding — it may already point to where the package is used
- If the package is **not found** in the codebase:
  - Flag as potential false positive (could be a transitive dependency no longer in use)
  - Inform the user and ask whether to proceed

### Step 2: Check for Vulnerable Function Usage

Many advisories only affect specific functions or code paths within a package. Verify actual exploitability:

1. **Fetch the advisory details** — use the `references` array URLs from the finding, or WebFetch the CVE page (e.g., `https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXX`)
2. **Identify vulnerable functions/APIs** — look for specific function names, API endpoints, or usage patterns mentioned in the advisory
3. **Grep the codebase** for those specific function names or patterns
4. **Assess the result:**
   - If the vulnerable function **is used** → the finding is exploitable, high priority
   - If the vulnerable function **is not used** → lower priority, inform the user it may not be exploitable in this codebase
   - If the advisory does not name specific functions → assume the entire package is vulnerable

### Step 3: Determine Remediation Approach

Present the user with available options:

**Option A: Upgrade the dependency**
- If `fixed_version` is available, update the dependency to that version
- Update the manifest/lockfile for the package ecosystem (see below)
- Run the package manager to verify the update resolves cleanly
- Trade-off: may introduce breaking changes — check the changelog

**Option B: Add code mitigation**
- If no `fixed_version` is available, or upgrading is too risky (breaking changes)
- Add code to avoid the vulnerable function, add input validation, or wrap with a safe alternative
- Trade-off: more work, may not cover all attack vectors

**Present both options when applicable.** If only one is viable, explain why.

### Step 4: Verify the Fix

- **If upgraded:** confirm the lockfile/manifest is updated, run `npm install` / `pip install` / equivalent to verify resolution, confirm the package version in the lockfile matches the fixed version
- **If mitigated:** confirm the vulnerable code path is no longer reachable, verify existing tests still pass

## Ecosystem-Specific Dependency Update Commands

| Ecosystem | Manifest File | Update Command |
|-----------|--------------|----------------|
| npm | `package.json` / `package-lock.json` | `npm install package@fixed_version` |
| pip | `requirements.txt` / `Pipfile` | `pip install package==fixed_version` (or update requirements.txt) |
| go | `go.mod` / `go.sum` | `go get package@fixed_version` |
| gem | `Gemfile` / `Gemfile.lock` | `bundle update package` (or update Gemfile) |
| maven | `pom.xml` | Update `<version>` in the `<dependency>` block in pom.xml |

After updating, run the appropriate install command to regenerate lockfiles and verify resolution.
