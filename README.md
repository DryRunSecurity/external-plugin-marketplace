# DryRunSecurity Skills for AI Coding Assistants

Official skills for AI coding assistants (Claude Code, Cursor, Windsurf, Codex) to work with DryRunSecurity — covering both vulnerability remediation and the full PR/MR review workflow.

## What This Does

This repo provides two skills that together cover the complete DryRunSecurity workflow:

**Vulnerability Remediation** — When DryRunSecurity scans your pull request and leaves a finding, this skill guides your AI assistant to understand and fix it contextually.

**PR Review Workflow** — Automates the full PR/MR lifecycle: branch, commit, push, open a PR or MR, then poll for and present DryRunSecurity review comments for your decisions.

**The Full Flow:**
```
You write code → AI creates branch + commit + PR/MR →
DryRunSecurity scans and comments → AI presents findings →
You decide what to fix → AI remediates and re-submits →
DryRunSecurity approves
```

## Philosophy

**Context is King.** DryRunSecurity spends significant effort understanding your codebase to identify *real* vulnerabilities. These skills do the same — they guide AI assistants to:

1. **Understand your codebase** - Existing patterns, tech stack, conventions
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

# Install the PR review workflow plugin
/plugin install dryrun-pr-review@dryrunsecurity
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
# DryRunSecurity AI Assistant Instructions
# Version: 1.0.0
```

Compare with the [latest release](https://github.com/DryRunSecurity/external-plugin-marketplace/releases).

## Usage

### Fixing a DryRunSecurity finding

Share the finding with your AI assistant:

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

### Creating a PR/MR for DryRunSecurity review

```
"Create a PR for my changes"
"Submit this for review"
"Push and open a pull request"
```

The skill will detect whether you're on GitHub or GitLab, discover your repo's existing branch and commit conventions, open the PR/MR, then poll for DryRunSecurity comments and present them to you for decisions.

## Supported Vulnerability Types

The skill works for any vulnerability DryRunSecurity identifies, including:

- SQL Injection, XSS, CSRF, SSRF
- IDOR, Mass Assignment, Auth Bypass
- Hardcoded Secrets, Path Traversal
- Command Injection, Prompt Injection
- Race Conditions, Deserialization issues
- Cryptographic weaknesses
- And any other security finding

## Available Plugins

### dryrun-remediation

**Description:** Fix security vulnerabilities identified by DryRunSecurity. Provides guided remediation for SQL injection, XSS, SSRF, IDOR, and other security findings.

**Version:** 1.0.1

**Skills included:**

| Skill | Description |
|-------|-------------|
| `remediation` | Researches authoritative sources and applies contextual fixes for DryRunSecurity findings |

**When to use:**
- DryRunSecurity leaves a finding comment on your PR
- You want guided, codebase-aware remediation for a security vulnerability

**Example usage:**
```
DryRunSecurity found a SQL injection in my PR. Here's the comment: [paste]. Can you fix it?
```

---

### dryrun-pr-review

**Description:** PR workflow automation — creates commits, branches, and PRs following conventions, then polls for and addresses DryRunSecurity review comments.

**Version:** 1.0.0

**Skills included:**

| Skill | Description |
|-------|-------------|
| `dryrun-pr-review` | Full PR lifecycle: branch, commit, push, PR creation, DryRunSecurity review polling |

**When to use:**
- Creating a new pull request
- Pushing changes for DryRunSecurity review
- Waiting on and addressing DryRunSecurity PR feedback

**Example usage:**
```
Create a PR for my changes
```
```
Submit this for review
```

**Features:**
- Detects GitHub vs GitLab automatically from git remote
- Discovers and follows your repo's existing branch and commit conventions
- Saves discovered conventions to `.claude/pr-conventions.md` for future runs
- Polls for DryRunSecurity review comments (timestamp-based, reliable across edits)
- Presents findings to user for decisions — does not auto-fix
- Loops: apply fixes → push → re-poll until DryRunSecurity is satisfied

---

## Directory Structure

```
external-plugin-marketplace/
├── .claude-plugin/
│   └── marketplace.json              # Claude Code marketplace config
├── plugins/
│   ├── dryrun-remediation/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json           # Plugin manifest
│   │   └── skills/
│   │       └── remediation/
│   │           ├── SKILL.md
│   │           ├── DRYRUN_FILTERING.md
│   │           ├── FINDING_FORMAT.md
│   │           └── VULNERABILITY_TYPES.md
│   └── dryrun-pr-review/
│       ├── .claude-plugin/
│       │   └── plugin.json           # Plugin manifest
│       └── skills/
│           └── dryrun-pr-review/
│               └── SKILL.md
├── standalone/
│   ├── .cursorrules                  # For Cursor IDE
│   ├── .windsurfrules                # For Windsurf IDE
│   ├── RULES.md                      # Generic (VS Code, Codex, etc.)
│   └── copilot-instructions.md       # For GitHub Copilot (.github/copilot-instructions.md)
├── CONTRIBUTING.md                   # Development workflow
├── CHANGELOG.md                      # Version history
└── README.md
```

## Support

- **Documentation:** https://docs.dryrunsecurity.com
- **Issues:** https://github.com/DryRunSecurity/external-plugin-marketplace/issues
- **Contact:** support@dryrunsecurity.com
