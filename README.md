# DryRunSecurity Skills for AI Coding Assistants

Official skills for AI coding assistants (Claude Code, Cursor, Windsurf, Codex) to help fix security vulnerabilities identified by DryRunSecurity.

## What This Does

When DryRunSecurity scans your pull request and leaves a comment about a security vulnerability, this skill helps your AI coding assistant understand and fix the issue. Instead of just telling you there's a problem, you get guided remediation.

**The Flow:**
```
DryRunSecurity finds vulnerability → Comments on your PR →
You ask your AI assistant to fix it → Skill guides contextual fix →
You push the fix → DryRunSecurity approves
```

## Philosophy

**Context is King.** DryRunSecurity spends significant effort understanding your codebase to identify *real* vulnerabilities. This remediation skill does the same - it guides AI assistants to:

1. **Understand your codebase** - Existing patterns, tech stack, utilities
2. **Research authoritative sources** - Official docs, OWASP, CWE references
3. **Apply contextual fixes** - Matches your code style, uses your existing utilities
4. **Explain and verify** - Why it was vulnerable, why the fix works

No static cheat sheets. No generic examples. Fixes grounded in *your* code.

## Installation

### For Cursor

Download to your project (always latest):
```bash
curl -o .cursorrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/main/standalone/.cursorrules
```

Or pin to a specific version:
```bash
curl -o .cursorrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/v1.0.0/standalone/.cursorrules
```

### For Windsurf

Download to your project (always latest):
```bash
curl -o .windsurfrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/main/standalone/.windsurfrules
```

Or pin to a specific version:
```bash
curl -o .windsurfrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/v1.0.0/standalone/.windsurfrules
```

### For Claude Code

```bash
# Add the marketplace
/plugin marketplace add DryRunSecurity/external-plugin-marketplace

# Install the remediation plugin
/plugin install dryrun-remediation@dryrunsecurity
```

### For Other AI Assistants (VS Code, Codex, etc.)

Download or copy [`standalone/RULES.md`](standalone/RULES.md) into your AI assistant's system prompt or rules configuration.

## Versioning

All skill files include a version number in their header:
```
# Version: 1.0.0
```

### Version Policy

- **`main` branch** - Always contains the latest version
- **Git tags** (`v1.0.0`, `v1.1.0`, etc.) - Pinned releases

### Staying Up to Date

**Option 1: Always latest (recommended for most users)**
```bash
# Re-run the curl command to get the latest
curl -o .cursorrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/main/standalone/.cursorrules
```

**Option 2: Pin to a version**
```bash
# Use a specific tag
curl -o .cursorrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/v1.0.0/standalone/.cursorrules
```

### Checking Your Version

Look at the top of your rules file:
```
# DryRunSecurity Vulnerability Remediation
# Version: 1.0.0
```

Compare with the [latest release](https://github.com/DryRunSecurity/external-plugin-marketplace/releases).

## Usage

Once installed, share the DryRunSecurity finding with your AI assistant:

```
"DryRunSecurity found a SQL injection vulnerability in my PR.
Here's the comment: [paste comment]. Can you help me fix it?"
```

Or point directly to the file:

```
"Fix the SQL injection in src/handlers/user.go line 45"
```

The skill guides the assistant to:
1. Read and understand your affected code
2. Find how similar issues are handled elsewhere in your codebase
3. Research the authoritative fix for your framework/version
4. Apply a fix that matches your existing patterns
5. Explain why it was vulnerable and why the fix works

## Supported Vulnerability Types

The skill works for any vulnerability DryRunSecurity identifies, including:

- SQL Injection, XSS, CSRF, SSRF
- IDOR, Mass Assignment, Auth Bypass
- Hardcoded Secrets, Path Traversal
- Command Injection, Prompt Injection
- Race Conditions, Deserialization issues
- Cryptographic weaknesses
- And any other security finding

## Directory Structure

```
external-plugin-marketplace/
├── .claude-plugin/
│   └── marketplace.json           # Claude Code marketplace config
├── plugins/
│   └── dryrun-remediation/
│       ├── .claude-plugin/
│       │   └── plugin.json        # Claude Code plugin manifest
│       └── skills/
│           └── remediation/
│               └── SKILL.md       # Full skill for Claude Code
├── standalone/
│   ├── .cursorrules               # For Cursor IDE
│   ├── .windsurfrules             # For Windsurf IDE
│   └── RULES.md                   # Generic (VS Code, Codex, etc.)
├── CONTRIBUTING.md                # Development workflow
├── CHANGELOG.md                   # Version history
└── README.md
```

## Support

- **Documentation:** https://docs.dryrunsecurity.com
- **Issues:** https://github.com/DryRunSecurity/external-plugin-marketplace/issues
- **Contact:** support@dryrunsecurity.com
