---
name: remediation
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
- **Vulnerability type** (e.g., SQL Injection, XSS, SSRF, Race Condition, Prompt Injection)
- **Affected file(s) and line numbers**
- **The specific dangerous pattern** DryRunSecurity identified
- **Language and framework** involved

If any of this is unclear, ask the user to share the full DryRunSecurity comment.

### Step 2: Understand the Codebase Context

Before proposing ANY fix, you MUST understand the existing codebase:

1. **Read the affected file(s)** - Understand the full context around the vulnerable code
2. **Identify the tech stack** - Check package.json, requirements.txt, go.mod, Gemfile, etc.
3. **Find existing security patterns** - Search the codebase for how similar issues are handled elsewhere:
   - How do they do database queries in other files?
   - What validation/sanitization utilities exist?
   - Are there auth middlewares or decorators already in use?
   - What's their coding style and conventions?
4. **Check for existing utilities** - Look for security-related helpers, validators, or wrappers they've already built

**Key questions to answer:**
- What ORM/database library are they using, and what version?
- What templating engine for output encoding?
- Do they have existing input validation patterns?
- Is there a security middleware or utility module?

### Step 3: Research the Authoritative Fix

For the specific vulnerability type and their stack, research the correct fix:

1. **Official framework documentation** - Search for "[framework name] [vulnerability type] prevention"
   - Django docs for Django apps
   - Rails Security Guide for Rails apps
   - GORM docs for Go apps
   - Prisma docs for Prisma apps
   - etc.

2. **OWASP resources** - For general vulnerability understanding:
   - OWASP Cheat Sheet Series (e.g., "SQL Injection Prevention Cheat Sheet")
   - OWASP Testing Guide for verification approaches

3. **CWE references** - For formal vulnerability definitions:
   - CWE-89 (SQL Injection)
   - CWE-79 (XSS)
   - CWE-918 (SSRF)
   - CWE-862 (Missing Authorization)
   - etc.

4. **Framework-specific security guides** - Many frameworks have dedicated security documentation

**Important**: Prefer the official documentation for their specific framework version. Security APIs change between versions.

### Step 4: Apply a Contextual Fix

Your fix should:

1. **Match existing patterns** - If they use a certain style for database queries elsewhere, follow it
2. **Use existing utilities** - If they have a `sanitize()` helper or `requireAuth` middleware, use it
3. **Be minimal** - Fix the vulnerability, don't refactor the whole file
4. **Preserve functionality** - The code should still do what it was meant to do
5. **Be framework-idiomatic** - Use the framework's recommended approach, not a generic workaround

### Step 5: Explain and Verify

After providing the fix:

1. **Explain why the original code was vulnerable** - In plain terms
2. **Explain why the fix works** - Reference the authoritative source
3. **Suggest verification steps** - How can they test that the fix works?
4. **Note any edge cases** - Are there related patterns they should check elsewhere?

## Example Workflow

**User shares DryRunSecurity finding:**
> "SQL Injection: User input from the `search` parameter is concatenated directly into a SQL query in `app/handlers/search.go:45`"

**Your process:**

1. **Parse**: SQL Injection in Go, file `app/handlers/search.go`, line 45

2. **Understand context**:
   - Read `app/handlers/search.go` to see the vulnerable code
   - Check `go.mod` - they're using GORM v1.25
   - Search codebase: "How do other handlers do database queries?"
   - Find: In `app/handlers/user.go`, they use `db.Where("id = ?", userID)` - parameterized!

3. **Research**:
   - GORM docs: "Raw SQL and SQL Builder" section shows parameterized queries
   - OWASP SQL Injection Prevention: Confirms parameterized queries are the fix

4. **Apply fix**:
   - Change the vulnerable string concatenation to use GORM's parameterized query syntax
   - Match the style used in `user.go`

5. **Explain**:
   - "The original code concatenated user input directly into SQL, allowing attackers to inject malicious SQL"
   - "The fix uses GORM's parameterized queries (the `?` placeholder), which automatically escapes input"
   - "This matches the pattern already used in `user.go:32`"

## Key Principles

### Context is King
DryRunSecurity spends significant effort understanding your codebase to identify real vulnerabilities. Remediation should do the same - understand the codebase to provide real, contextual fixes.

### Don't Assume - Research
Even for "common" vulnerabilities like SQL injection, the correct fix varies by:
- Language (Go vs Python vs JavaScript)
- Framework (GORM vs SQLx vs database/sql)
- Version (APIs change between versions)
- Existing patterns (what does this codebase already do?)

### Authoritative Sources Over Examples
Don't rely on memorized examples. Look up the current, official guidance for their specific stack. Security best practices evolve.

### Minimal, Focused Changes
A good security fix:
- Changes only what's necessary
- Doesn't introduce new patterns inconsistent with the codebase
- Doesn't add unnecessary dependencies
- Doesn't refactor unrelated code

## Handling Unfamiliar Vulnerabilities

DryRunSecurity detects a wide range of vulnerabilities beyond the OWASP Top 10. For any vulnerability type you encounter:

1. **Parse the finding** - Understand what DryRunSecurity identified
2. **Research the vulnerability class** - What is this type of vulnerability? What's the attack vector?
3. **Find the framework-specific fix** - How does their specific stack address this?
4. **Apply contextually** - Match their existing patterns

This approach works for:
- Traditional web vulnerabilities (SQLi, XSS, CSRF, SSRF, etc.)
- API security issues (IDOR, Mass Assignment, Auth Bypass)
- Modern concerns (Prompt Injection, LLM security)
- Language-specific issues (Deserialization, Type Confusion)
- Concurrency issues (Race Conditions, TOCTOU)
- Cryptographic issues (Weak algorithms, Key management)
- And anything else DryRunSecurity might find

## What NOT to Do

- **Don't provide generic examples** without checking if they fit the codebase
- **Don't assume the framework/version** - check the actual dependencies
- **Don't over-engineer** - a simple parameterized query doesn't need a whole new abstraction layer
- **Don't ignore existing patterns** - if they have a way of doing things, follow it
- **Don't skip the research** - even if you "know" the fix, verify it's correct for their stack
