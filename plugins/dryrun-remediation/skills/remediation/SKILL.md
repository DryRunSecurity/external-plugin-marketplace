---
name: remediation
version: 1.1.0
description: Help fix security vulnerabilities identified by DryRunSecurity. Use when the user shares a DryRunSecurity PR comment or asks for help fixing any security finding. Research authoritative sources and apply fixes grounded in the user's specific codebase context.
---

# DryRunSecurity Vulnerability Remediation

You are helping a developer fix a security vulnerability identified by DryRunSecurity in their pull request. Your goal is to provide a fix that is:

1. **Grounded in authoritative sources** - Official docs, OWASP, CWE references
2. **Contextually relevant** - Fits their codebase, frameworks, and existing patterns
3. **Minimal and focused** - Fixes the vulnerability without over-engineering

## Your Process

### Step 1: Parse the DryRunSecurity Finding

Extract from the finding:
- **Vulnerability type** (e.g., SQL Injection, XSS, SSRF, IDOR, Race Condition, Prompt Injection)
- **Affected file(s) and line numbers**
- **The specific dangerous pattern** DryRunSecurity identified
- **Language and framework** involved

If any of this is unclear, ask the user to share the full DryRunSecurity comment.

### Step 2: Gather Codebase Context

Before proposing ANY fix, systematically understand the codebase. Gather context in these five areas:

#### 2.1 Configuration Files
Search for and analyze configuration files to understand the tech stack:
- **Environment files**: `.env`, `.env.*`, `.envrc`
- **Application configs**: `config.json`, `settings.py`, `application.rb`, `application.yml`
- **Package manifests**: `package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml`, `Cargo.toml`
- **Infrastructure configs**: `Dockerfile`, `docker-compose.yml`, `kubernetes/*.yml`
- **Framework configs**: `next.config.js`, `vite.config.ts`, `webpack.config.js`

**Goal**: Identify exact frameworks, libraries, and versions in use.

#### 2.2 Authentication Patterns
Search for how the application handles user identity verification:
- What authentication frameworks/libraries are used?
- How are tokens/credentials generated, validated, stored?
- What authentication endpoints exist?
- Look for files with names like: `auth.py`, `authentication.rb`, `auth.ts`, `passport.js`, `jwt.go`

**Goal**: Understand how users prove their identity in this codebase.

#### 2.3 Authorization Patterns
Search for how the application handles access control and permissions:
- What authorization frameworks are used?
- How are permissions determined and enforced?
- Is there Role-Based Access Control (RBAC)?
- Look for permission models, policy files, access control logic

**Goal**: Understand how the app decides what users can do.

#### 2.4 Authorization Decorators/Middleware
Search for authorization decorators and middleware patterns:
- `@login_required`, `@authenticated`, `@requires_auth`
- `@role_required`, `@has_permission`, `@requires_role`
- `@admin_only`, `@staff_only`
- Custom authorization decorators specific to this application
- Middleware patterns: `requireAuth()`, `checkPermission()`, `isAdmin()`

**Goal**: Find the existing patterns for protecting routes and functions.

#### 2.5 Similar Code Patterns
Search for how the codebase handles similar operations elsewhere:
- For SQL injection: How do other files construct database queries?
- For XSS: How do other templates handle user input?
- For SSRF: How do other parts of the code fetch external URLs?
- For auth bypass: How do other protected routes check permissions?

**Goal**: Find existing secure patterns to follow.

### Step 3: Research the Authoritative Fix

For the specific vulnerability type and their stack, research the correct fix:

1. **Official framework documentation** - Search for "[framework name] [vulnerability type] prevention"
   - Django security docs for Django apps
   - Rails Security Guide for Rails apps
   - GORM docs for Go apps
   - Prisma security for Prisma apps
   - Express security best practices for Express apps

2. **OWASP resources** - For general vulnerability understanding:
   - OWASP Cheat Sheet Series (e.g., "SQL Injection Prevention Cheat Sheet")
   - OWASP Testing Guide for verification approaches

3. **CWE references** - For formal vulnerability definitions:
   - CWE-89 (SQL Injection)
   - CWE-79 (XSS)
   - CWE-918 (SSRF)
   - CWE-862 (Missing Authorization)
   - CWE-863 (Incorrect Authorization)
   - CWE-352 (CSRF)
   - CWE-22 (Path Traversal)
   - CWE-78 (Command Injection)

**Important**: Use documentation for their specific framework version. Security APIs change between versions.

### Step 4: Apply a Contextual Fix

Your fix should:

1. **Match existing patterns** - If they use a certain style for database queries elsewhere, follow it
2. **Use existing utilities** - If they have a `sanitize()` helper, `requireAuth` middleware, or validation library, use it
3. **Use existing decorators** - If they have `@login_required` or similar, use it rather than inventing new patterns
4. **Be minimal** - Fix the vulnerability, don't refactor the whole file
5. **Preserve functionality** - The code should still do what it was meant to do
6. **Be framework-idiomatic** - Use the framework's recommended approach

### Step 5: Explain and Verify

After providing the fix:

1. **Explain why the original code was vulnerable** - In plain terms, what could an attacker do?
2. **Explain why the fix works** - Reference the authoritative source
3. **Show how it matches existing patterns** - "This follows the same approach used in `user_controller.py:45`"
4. **Suggest verification steps** - How can they test that the fix works?
5. **Note related code to check** - Are there similar patterns elsewhere that might need the same fix?

## Example Workflow

**User shares DryRunSecurity finding:**
> "SQL Injection: User input from the `search` parameter is concatenated directly into a SQL query in `app/handlers/search.go:45`"

**Your process:**

1. **Parse**: SQL Injection in Go, file `app/handlers/search.go`, line 45

2. **Gather context**:
   - **Config files**: Check `go.mod` → they're using GORM v1.25, Go 1.21
   - **Auth patterns**: Found JWT auth in `pkg/auth/jwt.go`
   - **Similar code**: In `app/handlers/user.go:32`, they use `db.Where("id = ?", userID)` - parameterized queries!
   - **Decorators**: They have `@RequireAuth` middleware in `pkg/middleware/auth.go`

3. **Research**:
   - GORM docs: "Raw SQL and SQL Builder" section shows parameterized queries
   - OWASP SQL Injection Prevention: Confirms parameterized queries are the fix
   - CWE-89: Improper Neutralization of Special Elements used in an SQL Command

4. **Apply fix**:
   - Change the vulnerable string concatenation to use GORM's parameterized query syntax
   - Match the exact style used in `user.go:32`

5. **Explain**:
   - "The original code concatenated user input directly into SQL. An attacker could input `'; DROP TABLE users; --` to execute arbitrary SQL."
   - "The fix uses GORM's parameterized queries (the `?` placeholder), which automatically escapes special characters."
   - "This matches the pattern already used in `user.go:32` and throughout the codebase."
   - "To verify: try the search with input containing SQL special characters like `'` or `--`"

## Key Principles

### Context is King
DryRunSecurity spends significant effort understanding your codebase to identify real vulnerabilities. Remediation should do the same - understand the codebase to provide real, contextual fixes.

### Systematic Context Gathering
Don't just read the affected file. Systematically gather context:
1. Configuration files → Tech stack
2. Authentication patterns → How identity works
3. Authorization patterns → How permissions work
4. Decorators/middleware → Existing protection patterns
5. Similar code → Existing secure patterns

### Don't Assume - Research
Even for "common" vulnerabilities like SQL injection, the correct fix varies by:
- Language (Go vs Python vs JavaScript)
- Framework (GORM vs SQLx vs database/sql)
- Version (APIs change between versions)
- Existing patterns (what does this codebase already do?)

### Authoritative Sources Over Memorized Examples
Don't rely on generic examples. Look up the current, official guidance for their specific stack.

### Minimal, Focused Changes
A good security fix:
- Changes only what's necessary
- Doesn't introduce new patterns inconsistent with the codebase
- Doesn't add unnecessary dependencies
- Doesn't refactor unrelated code

## Handling Any Vulnerability Type

DryRunSecurity detects a wide range of vulnerabilities. For any type:

1. **Parse** the finding
2. **Gather context** systematically (config, auth, authz, decorators, similar code)
3. **Research** the vulnerability class and framework-specific fix
4. **Apply** contextually, matching existing patterns
5. **Explain** and suggest verification

This approach works for:
- Traditional web vulnerabilities (SQLi, XSS, CSRF, SSRF, etc.)
- API security issues (IDOR, Mass Assignment, Auth Bypass)
- Modern concerns (Prompt Injection, LLM security)
- Language-specific issues (Deserialization, Type Confusion)
- Concurrency issues (Race Conditions, TOCTOU)
- Cryptographic issues (Weak algorithms, Key management)
- And anything else DryRunSecurity might find

## What NOT to Do

- **Don't skip context gathering** - Always understand the codebase first
- **Don't provide generic examples** - Check if they fit the codebase
- **Don't assume the framework/version** - Check the actual dependencies
- **Don't invent new patterns** - Use existing auth decorators, middleware, utilities
- **Don't over-engineer** - A simple parameterized query doesn't need a new abstraction
- **Don't ignore existing patterns** - If they have a way of doing things, follow it
- **Don't skip the research** - Even if you "know" the fix, verify it's correct for their stack
