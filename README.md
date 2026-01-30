# DryRunSecurity Skills for AI Coding Assistants

Official skills for AI coding assistants (Claude Code, OpenAI Codex) to help fix security vulnerabilities identified by DryRunSecurity.

## What This Does

When DryRunSecurity scans your pull request and leaves a comment about a security vulnerability, this skill helps your AI coding assistant understand and fix the issue. Instead of just telling you there's a problem, you get guided remediation.

**The Flow:**
```
DryRunSecurity finds vulnerability → Comments on your PR →
You ask your AI assistant to fix it → Skill provides secure code patterns →
You push the fix → DryRunSecurity approves
```

## Available Skills

### dryrun-remediation

Helps fix security vulnerabilities including:
- **SQL Injection** - Parameterized query patterns for GORM, Django, SQLAlchemy, Prisma, Knex, ActiveRecord, JDBC
- **Cross-Site Scripting (XSS)** - Proper output encoding for React, Django, Rails, EJS, Blade
- **Server-Side Request Forgery (SSRF)** - URL validation and allowlisting
- **Insecure Direct Object Reference (IDOR)** - Authorization checks
- **Mass Assignment** - Input allowlisting
- **Authentication/Authorization Bypass** - Proper access controls
- **Hardcoded Secrets** - Environment variable patterns
- **Path Traversal** - Safe file path handling
- **Command Injection** - Safe subprocess execution
- **Prompt Injection** - LLM input delimiting

## Installation

### For Cursor

Copy the contents of [`standalone/.cursorrules`](standalone/.cursorrules) to your project's `.cursorrules` file, or download it directly:

```bash
curl -o .cursorrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/main/standalone/.cursorrules
```

### For Windsurf

Copy the contents of [`standalone/.windsurfrules`](standalone/.windsurfrules) to your project's `.windsurfrules` file, or download it directly:

```bash
curl -o .windsurfrules https://raw.githubusercontent.com/DryRunSecurity/external-plugin-marketplace/main/standalone/.windsurfrules
```

### For Claude Code

```bash
# Add the marketplace
/plugin marketplace add DryRunSecurity/external-plugin-marketplace

# Install the remediation skill
/plugin install dryrun-remediation@dryrunsecurity
```

### For Other AI Assistants (VS Code, Codex, etc.)

Copy the contents of [`standalone/RULES.md`](standalone/RULES.md) into your AI assistant's system prompt or rules configuration.

## Usage

Once installed, simply share the DryRunSecurity finding with your AI assistant:

```
"DryRunSecurity found a SQL injection vulnerability in my PR.
Here's the comment: [paste comment]. Can you help me fix it?"
```

Or ask directly:

```
"Fix the SQL injection in src/handlers/user.go line 45"
```

The skill will guide the assistant to:
1. Understand the specific vulnerability
2. Apply the correct fix pattern for your language/framework
3. Preserve your code's functionality
4. Verify the fix addresses the issue

## Example

**DryRunSecurity Comment:**
> SQL Injection: User input from the `username` parameter is concatenated directly into a SQL query using `db.Raw()` without parameterization.

**Your Request:**
> "Help me fix this SQL injection"

**Result:**
The assistant will identify the vulnerable pattern and provide the parameterized query fix specific to your framework (GORM, in this case).

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
└── README.md
```

## Support

- **Documentation:** https://docs.dryrunsecurity.com
- **Issues:** https://github.com/DryRunSecurity/external-plugin-marketplace/issues
- **Contact:** support@dryrunsecurity.com
