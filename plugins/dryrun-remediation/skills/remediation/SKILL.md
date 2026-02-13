---
name: remediation
version: 1.0.1
description: >-
  Helps fix security vulnerabilities identified by DryRunSecurity. Activates when
  the user shares a DryRunSecurity comment (from a GitHub PR or GitLab MR) or asks
  for help fixing any security finding including SQL injection, XSS, CSRF, SSRF,
  path traversal, command injection, authentication bypass, authorization flaws,
  and prompt injection. Researches authoritative sources and applies fixes
  grounded in the user's specific codebase context.
license: Proprietary
triggers:
  - DryRunSecurity comment
  - DryRunSecurity finding
  - security vulnerability
  - fix vulnerability
  - SQL injection
  - XSS
  - cross-site scripting
  - CSRF
  - SSRF
  - path traversal
  - command injection
  - authentication bypass
  - authorization flaw
  - prompt injection
  - security fix
  - remediate
  - CVE fix
  - OWASP
compatibility: claude-code, cursor, windsurf, cline, aider
allowed_tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - WebFetch
  - Bash
output: >-
  A minimal, contextual code fix for the identified vulnerability with explanation
  of why the original code was vulnerable, why the fix works, and verification steps.
---

# DryRunSecurity Vulnerability Remediation

You are helping a developer fix a security vulnerability identified by DryRunSecurity in their pull request (GitHub) or merge request (GitLab). Your goal is to provide a fix that is:

1. **Grounded in authoritative sources** - Official docs, OWASP, CWE references
2. **Contextually relevant** - Fits their codebase, frameworks, and existing patterns
3. **Minimal and focused** - Fixes the vulnerability without over-engineering

**Trust the finding** - DryRunSecurity rigorously filters false positives. See [DRYRUN_FILTERING.md](./DRYRUN_FILTERING.md) for details.

## Your Process

Follow these steps in order. Each step includes specific actions to take.

### Step 1: Parse the DryRunSecurity Finding

**Action:** Extract vulnerability type, file path, line numbers, and description from the comment.

See [FINDING_FORMAT.md](./FINDING_FORMAT.md) for the full format reference.

If the user only shares part of the finding, ask for the full DryRunSecurity comment.

### Step 2: Gather Codebase Context

**Action:** Use Glob and Grep to search, Read to examine. Do NOT propose a fix until complete.

Gather context in these areas:

| Area | Search For |
|------|------------|
| **Config files** | `.env`, `package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml` |
| **Auth patterns** | `auth.py`, `authentication.rb`, `jwt.go`, `passport.js` |
| **Authz patterns** | Permission models, RBAC, policy files |
| **Decorators** | `@login_required`, `@requires_auth`, `requireAuth()`, `checkPermission()` |
| **Similar code** | How does this codebase handle similar operations securely? |

### Step 3: Research the Authoritative Fix

**Action:** Use WebFetch to look up official documentation. Do NOT rely on memorized examples.

Research sources:
1. **Official framework docs** - "[framework] [vulnerability] prevention" (Django, Rails, GORM, Prisma, Express)
2. **OWASP Cheat Sheets** - General vulnerability guidance
3. **CWE references** - See [VULNERABILITY_TYPES.md](./VULNERABILITY_TYPES.md)

Use docs for their specific framework version - security APIs change between versions.

### Step 4: Apply a Contextual Fix

**Action:** Use Edit to make the minimal change necessary.

Requirements:
- Match existing patterns in the codebase
- Use existing utilities, decorators, and middleware
- Preserve functionality
- Be framework-idiomatic

### Step 5: Explain and Verify

**Action:** Explain the fix and suggest verification.

Include:
1. Why the original code was vulnerable (attack scenario)
2. Why the fix works (reference authoritative source)
3. How it matches existing patterns
4. Verification steps
5. Related code that may need similar fixes

## Example

**Finding:** "SQL Injection in `app/handlers/search.go:45`"

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

## Commit Format

```
fix: <description>

Co-authored-by: DryRunSecurity <noreply@dryrunsecurity.com>
```
