# DryRunSecurity Vulnerability Remediation
# Version: 1.0.0
# https://github.com/DryRunSecurity/external-plugin-marketplace

When helping fix security vulnerabilities identified by DryRunSecurity, follow this process to provide fixes that are grounded in authoritative sources and contextually relevant to the user's specific codebase.

## Process

### 1. Parse the Finding
Extract from the DryRunSecurity comment:
- Vulnerability type (SQL Injection, XSS, SSRF, Race Condition, Prompt Injection, etc.)
- Affected file(s) and line numbers
- The specific dangerous pattern identified
- Language and framework involved

### 2. Understand the Codebase Context

Before proposing ANY fix:

1. **Read the affected file(s)** - Understand the full context around the vulnerable code
2. **Identify the tech stack** - Check package.json, requirements.txt, go.mod, Gemfile, pom.xml, etc.
3. **Find existing security patterns** - Search the codebase:
   - How do other files handle similar operations (database queries, user input, auth)?
   - What validation/sanitization utilities already exist?
   - What auth middlewares or decorators are in use?
4. **Check for existing utilities** - Look for security helpers, validators, or wrappers already built

Key questions:
- What ORM/database library and version?
- What templating engine for output?
- Existing input validation patterns?
- Security middleware or utility modules?

### 3. Research the Authoritative Fix

For the specific vulnerability type and stack:

1. **Official framework docs** - Search "[framework] [vulnerability type] prevention"
2. **OWASP Cheat Sheets** - For vulnerability-specific guidance
3. **CWE references** - For formal definitions (CWE-89, CWE-79, CWE-918, etc.)
4. **Framework security guides** - Many frameworks have dedicated security docs

**Important**: Use documentation for their specific framework version. Security APIs change.

### 4. Apply a Contextual Fix

Your fix should:
- **Match existing patterns** - Follow the style used elsewhere in the codebase
- **Use existing utilities** - If they have helpers, use them
- **Be minimal** - Fix the vulnerability, don't refactor unrelated code
- **Preserve functionality** - The code should still work as intended
- **Be framework-idiomatic** - Use the framework's recommended approach

### 5. Explain and Verify

After providing the fix:
- Explain why the original code was vulnerable (plain terms)
- Explain why the fix works (reference authoritative source)
- Suggest how to verify the fix
- Note related patterns to check elsewhere

## Key Principles

### Context is King
DryRunSecurity understands your codebase to find real vulnerabilities. Remediation should do the same - understand the codebase to provide real, contextual fixes.

### Don't Assume - Research
The correct fix varies by language, framework, version, and existing patterns. Look it up.

### Authoritative Sources Over Memorized Examples
Don't rely on generic examples. Check current official guidance for their specific stack.

### Minimal, Focused Changes
- Change only what's necessary
- Don't introduce inconsistent patterns
- Don't add unnecessary dependencies
- Don't refactor unrelated code

## Handling Any Vulnerability Type

DryRunSecurity detects vulnerabilities beyond OWASP Top 10. For any type:

1. Parse the finding
2. Research the vulnerability class
3. Find the framework-specific fix
4. Apply contextually

This works for: SQLi, XSS, CSRF, SSRF, IDOR, Mass Assignment, Auth Bypass, Prompt Injection, Race Conditions, Deserialization, Cryptographic issues, and anything else.

## What NOT to Do

- Don't provide generic examples without checking the codebase
- Don't assume the framework/version - check dependencies
- Don't over-engineer - keep fixes simple
- Don't ignore existing patterns
- Don't skip research - verify the fix is correct for their stack
