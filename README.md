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

**Recommended: pre-approve the CLI tools** to avoid repeated permission prompts during the PR workflow. Run this once after installing:

```bash
/permissions allow Bash(git:*)
/permissions allow Bash(gh:*)
/permissions allow Bash(glab:*)
```

Or add them to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["Bash(git:*)", "Bash(gh:*)", "Bash(glab:*)"]
  }
}
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

## GitHub Actions remediation

Two reusable workflows run the bundled skills with a pinned Deep Agents Code runtime:

| Workflow | Result | Caller example |
|---|---|---|
| [PR comment remediation](.github/workflows/dryrun-comment-remediation.yml) | Inline suggestions with local rationale, plus a timeline explanation and full patch; never commits or pushes to the target PR | [Comment caller](examples/github-actions/dryrun-comment-remediation.yml) |
| [Finding ID remediation](.github/workflows/dryrun-findings-remediation.yml) | One combined remediation PR with committed fixes and detailed analysis for the selected findings | [Finding caller](examples/github-actions/dryrun-findings-remediation.yml) |

Both publish agent-written explanations of the original DryRun issue, exact changes, why they address it, and validation or remaining prerequisites. Replays reuse the deterministic finding PR; an existing PR's explanation can be refreshed from its immutable head without changing its code or adding commits. Large patches may be artifact-only, but the explanations remain visible on GitHub.

### Installation

1. Copy the desired caller example into your repository's `.github/workflows/` directory **on the default branch**. This is required for automatic `issue_comment` events and for manual dispatch to be available. The comment caller listens to created/edited PR **timeline conversation comments**, not inline review comments.
2. The examples pin workflow commit `96212166b894b2af7e51c133b244a9182f14d806`. Keep an immutable, reviewed commit pin when updating; the examples do not depend on a development branch or assume a release tag exists.
3. Create the caller repository secret `OPENAI_API_KEY`. The examples explicitly map it to the required `MODEL_API_KEY`; no secrets are implicitly inherited. **GitHub Free private repositories need repository secrets** because organization secrets are not available to them.
4. For findings, also set repository secret `DRYRUN_API_KEY` and repository variable `DRYRUN_ACCOUNT_ID`, or supply the account UUID at dispatch. Allow GitHub Actions to create pull requests in repository settings; organization policy must also permit this. Do not bypass a policy that disables PR creation.
5. Allow this public reusable workflow and its referenced actions in your Actions policy. Keep the caller permissions shown in the examples: the called jobs can reduce permissions, not elevate them ([GitHub reference](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)).

Automatic comment runs accept only `dryrunsecurity[bot]` (user ID `142451713`, type `Bot`). Irrelevant events are filtered before model execution. Manual comment runs and all finding runs require a repository writer. Only open, **same-repository PRs** are supported; fork PR remediation is not supported.

### Inputs and secrets

Shared inputs are passed under the calling job's `with`:

| Input | Default | Meaning |
|---|---|---|
| `provider` | `openai` | `openai` or `anthropic` only |
| `model` | Empty | Resolves to `gpt-5.5` for OpenAI or `claude-sonnet-4-5` for Anthropic |
| `base_url` | Empty | Native provider SDK endpoint; an explicit HTTPS override selects a compatible API/gateway |
| `use_responses_api` | `true` | OpenAI Responses API; set `false` for Chat Completions-only gateways; ignored for Anthropic |

With no `base_url` override, OpenAI uses `https://api.openai.com/v1` and Anthropic uses `https://api.anthropic.com`. There is no internal endpoint or credential fallback.

**Comment inputs:** `pr_number` selects a PR for manual runs; `comment_id` is optional and defaults to the most recently updated verified DryRun comment on that PR. Automatic runs use the actual event's PR and comment instead.

**Finding inputs:** supply exactly one of `finding_id`, `finding_ids` (comma/whitespace-separated UUIDs, up to 20 unique IDs), or `issue_number`. `account_id` is required. Optional `base_branch` defaults to the caller's default branch; `finding_type` accepts `pullrequest`, `deepscan`, or `sca`. `dryrun_api_base_url` defaults to `https://simple-api.dryrun.security`. An issue must contain UUIDs under a dedicated `## DryRun finding IDs` heading (bullets or an unlabelled fenced list, ending at the next heading), or proper DryRun risk-register links with a `finding` query parameter; arbitrary prose is not interpreted as IDs.

**Secrets:** `MODEL_API_KEY` is required for both workflows and must match the selected provider/endpoint. `DRYRUN_API_KEY` is required only for findings. The caller's built-in `GITHUB_TOKEN` is used automatically; do not supply a separate GitHub token.

### Anthropic and compatible gateways

To use Anthropic, merge these settings into either example's `remediate` job, retaining its other inputs and, for findings, its `DRYRUN_API_KEY` mapping:

```yaml
with:
  provider: anthropic
  model: claude-sonnet-4-5
secrets:
  MODEL_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

For an OpenAI-compatible gateway, use an explicit endpoint, a model exposed by that gateway, and its matching key:

```yaml
with:
  provider: openai
  model: your-gateway-model
  base_url: https://gateway.example.com/v1
  use_responses_api: false
secrets:
  MODEL_API_KEY: ${{ secrets.MODEL_GATEWAY_API_KEY }}
```

Anthropic-compatible gateways likewise use `provider: anthropic` with `base_url`, `model`, and a matching key. Only OpenAI/Anthropic-compatible APIs are supported; **native AWS Bedrock authentication is not supported**. Only configure endpoints you trust with repository content and the supplied model key.

### Execution boundaries and review

- Read-only preparation and write-capable publication run in separate jobs. GitHub credentials are scoped to checkout, preparation, and publication; the DryRun key is available only during finding preparation. The model key is available only to the agent execution stage, and its container receives no GitHub or DryRun credentials.
- The agent has only filesystem tools, with project instructions/hooks/MCP disabled and sensitive or unsupported source paths excluded. It cannot run shell commands, application tests, builds, or deployments. Network access is needed for the model API: these restrictions are **not OS-level network isolation**.
- An external credential-free npm container may regenerate a changed manifest's lockfile using only the manifest and original lockfile, with lifecycle scripts disabled. Only a root `package-lock.json` is supported: no workspaces, alternative package managers, or authenticated private registries. This is not application validation.
- Proposals and agent output are retained as artifacts for seven days; additional agent diagnostics are uploaded only on failure. Treat artifacts as sensitive repository data. Agent stdout is not echoed into workflow logs.
- Fixes remain unmerged and require human review and CI; there are no autonomous merges or deployments. The workflow does not run application tests. Changes created using `GITHUB_TOKEN` do not automatically trigger ordinary downstream Actions runs, so arrange explicit CI validation before merging.

**Maintainers:** both jobs in both reusable workflows check out implementation SHA `73fc31261eddd535230fc8b0a418f1dcf7729f29`. This one checkout supplies the runtime and skills. Bump **all four immutable checkout pins in both workflows together** when releasing runtime or skill updates. The caller's `uses: ...@ref` is a separate reference selecting the workflow definition, not the implementation checkout.

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
