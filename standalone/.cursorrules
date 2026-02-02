# DryRunSecurity Vulnerability Remediation
# Version: 1.0.0
# https://github.com/DryRunSecurity/external-plugin-marketplace

When helping fix security vulnerabilities identified by DryRunSecurity (from GitHub PRs or GitLab MRs), follow this process to provide fixes grounded in authoritative sources and contextually relevant to the user's codebase.

## What DryRunSecurity Flags (Trust the Finding)

DryRunSecurity focuses on **real, exploitable code vulnerabilities**. It filters out:
- Dependency/CVE issues (use dependency scanners)
- Language/runtime version issues
- False positives (chained vulns, context-inappropriate findings, theoretical risks)
- Logging of non-sensitive data (IDs, timestamps, errors without secrets)
- Test/debug code issues
- Code style nitpicks without security impact

**If DryRunSecurity flagged it, it's real.** The finding passed rigorous multi-stage filtering. Trust it and focus on fixing it correctly.

## Process

### 1. Parse the Finding

DryRunSecurity findings follow this format:
```
<details>
<summary>[emoji] Vulnerability Title in <code>path/to/file.ext</code></summary>

| **Vulnerability** | Vulnerability Name |
|:---|:---|
| **Description** | Detailed explanation... |

<Permalink to affected lines>
</details>
```

Extract:
- **Vulnerability type**: From table row (e.g., "Prompt Injection", "Cross-Site Scripting")
- **File path**: From the `<code>` tag in summary
- **Line numbers**: From permalink (e.g., `#L231-L232`)
- **Description**: The WHY - attack scenario and what makes it vulnerable
- **Severity**: `:yellow_circle:` = needs attention, no emoji = blocking

### 2. Gather Codebase Context

Before proposing ANY fix, systematically gather context in these five areas:

#### 2.1 Configuration Files
Search for config files to identify the tech stack:
- Environment: `.env`, `.env.*`
- Package manifests: `package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml`
- App configs: `config.json`, `settings.py`, `application.rb`
- Framework configs: `next.config.js`, `vite.config.ts`

**Goal**: Identify exact frameworks, libraries, and versions.

#### 2.2 Authentication Patterns
Search for how the app verifies user identity:
- What auth frameworks/libraries are used?
- How are tokens/credentials validated?
- Look for: `auth.py`, `authentication.rb`, `passport.js`, `jwt.go`

**Goal**: Understand how users prove identity.

#### 2.3 Authorization Patterns
Search for access control and permissions:
- What authorization frameworks are used?
- How are permissions enforced?
- Is there RBAC (Role-Based Access Control)?

**Goal**: Understand how the app decides what users can do.

#### 2.4 Authorization Decorators/Middleware
Search for existing protection patterns:
- `@login_required`, `@authenticated`, `@requires_auth`
- `@role_required`, `@has_permission`, `@admin_only`
- Middleware: `requireAuth()`, `checkPermission()`, `isAdmin()`

**Goal**: Find existing patterns for protecting routes.

#### 2.5 Similar Code Patterns
Search for how the codebase handles similar operations:
- SQL injection: How do other files construct queries?
- XSS: How do other templates handle user input?
- Auth bypass: How do other routes check permissions?

**Goal**: Find existing secure patterns to follow.

### 3. Research the Authoritative Fix

For the specific vulnerability and stack:
1. **Official framework docs** - "[framework] [vulnerability] prevention"
2. **OWASP Cheat Sheets** - Vulnerability-specific guidance
3. **CWE references** - CWE-89 (SQLi), CWE-79 (XSS), CWE-918 (SSRF), etc.

**Important**: Use docs for their specific framework version.

### 4. Apply a Contextual Fix

Your fix should:
- **Match existing patterns** - Follow the style used elsewhere
- **Use existing utilities** - Use their helpers, middleware, validators
- **Use existing decorators** - Don't invent new protection patterns
- **Be minimal** - Fix the vulnerability, don't refactor
- **Preserve functionality** - Code should still work
- **Be framework-idiomatic** - Use recommended approach

### 5. Explain and Verify

After the fix:
- Explain why original code was vulnerable (what could attacker do?)
- Explain why fix works (reference authoritative source)
- Show how it matches existing patterns ("same as `user_controller.py:45`")
- Suggest verification steps
- Note related code to check

## Key Principles

### Context is King
DryRunSecurity understands your codebase to find real vulnerabilities. Remediation does the same - understand the codebase to provide real, contextual fixes.

### Systematic Context Gathering
1. Configuration files → Tech stack
2. Authentication patterns → How identity works
3. Authorization patterns → How permissions work
4. Decorators/middleware → Existing protection patterns
5. Similar code → Existing secure patterns

### Don't Assume - Research
The correct fix varies by language, framework, version, and existing patterns.

### Authoritative Sources Over Examples
Look up current official guidance for their specific stack.

### Minimal, Focused Changes
- Change only what's necessary
- Don't introduce inconsistent patterns
- Don't add unnecessary dependencies

## Committing the Fix

Suggest a commit message with DryRunSecurity as co-author:

```
fix: <brief description of the security fix>

Co-authored-by: DryRunSecurity <noreply@dryrunsecurity.com>
```

## What NOT to Do

- Don't skip context gathering
- Don't provide generic examples without checking the codebase
- Don't assume framework/version - check dependencies
- Don't invent new patterns - use existing decorators/middleware
- Don't over-engineer
- Don't skip research
