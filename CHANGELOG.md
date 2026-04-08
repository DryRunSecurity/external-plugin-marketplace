# Changelog

All notable changes to DryRunSecurity Skills will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`dryrun-pr-review` plugin**: Full PR/MR lifecycle skill for DryRunSecurity users
  - Detects GitHub vs GitLab from `git remote get-url origin`; uses `gh` or `glab` accordingly
  - Convention discovery: reads existing branches, commit history, and PR/MR titles before creating anything — no opinionated defaults imposed
  - Saves discovered conventions to `.claude/pr-conventions.md` (with user consent) for future runs
  - Polls for DryRunSecurity review comments (timestamp-based); presents findings to user for decisions
  - Loops: apply fixes → push → re-poll until DryRunSecurity is satisfied
- **Combined standalone files**: `.cursorrules`, `.windsurfrules`, `RULES.md`, and `copilot-instructions.md` now contain both the Remediation workflow (Workflow 1) and PR Review workflow (Workflow 2) with routing instructions for IDEs

### Improved
- **Reduced permission prompts in `dryrun-pr-review`** (Claude Code and all standalone formats):
  - Merged Platform Detection and Repo Info into a single script — was two separate shell invocations
  - Merged convention discovery bash blocks into one conditional script — was three separate invocations
  - Added explicit instruction to keep the polling loop as a single shell invocation
  - Added instruction to consolidate related commands to minimise permission prompts
- **Fixed `allowed_tools` in `dryrun-pr-review` SKILL.md**: added `Write`, `Edit`, `Glob`, `Grep` — previously missing, causing unexpected permission prompts when writing conventions file or making code edits
- **README**: added recommended Claude Code permission pre-approvals for `git`, `gh`, and `glab` to reduce prompts at the session level
- **Fixed `copilot-instructions.md`** version out of sync with other standalone files (was `1.0.0`, now `1.0.1`)

## [1.0.1] - 2026-02-06

### Improved
- **Enhanced skill frontmatter for better Tessl score**:
  - Changed description to third-person voice ("Helps fix" vs "Help fix")
  - Added explicit `triggers` list with vulnerability keywords for better activation
  - Added `output` field describing expected return format
  - Added `license: Proprietary` field
  - Added `compatibility` list for supported agents (claude-code, cursor, windsurf, cline, aider)
  - Added `allowed_tools` list for required tool access
- **Action-oriented step guidance**:
  - Added explicit `**Action:**` directives to each step
  - Specified which tools to use at each step (Glob, Grep, Read, WebFetch, Edit)
  - Added "Follow these steps in order" instruction for clarity

## [1.2.0] - 2025-01-30

### Added
- **DryRunSecurity finding format parsing**: Step 1 now includes the exact format of DryRunSecurity PR comments, showing how to extract:
  - Vulnerability type from the markdown table
  - File path from the `<code>` tag
  - Line numbers from the GitHub permalink
  - Severity indicators (`:yellow_circle:` vs blocking)
- Example parsing walkthrough for Prompt Injection finding

### Improved
- More precise guidance on what information to extract from each part of the finding

## [1.1.0] - 2025-01-30

### Changed
- **Systematic context gathering**: Now follows structured 5-step context gathering approach inspired by DryRunSecurity's Reposture scanner:
  1. Configuration files → Identify tech stack, frameworks, versions
  2. Authentication patterns → How users prove identity
  3. Authorization patterns → How permissions are enforced
  4. Authorization decorators/middleware → Existing protection patterns
  5. Similar code patterns → Find existing secure patterns to follow

### Improved
- More specific guidance on what files to search for each context type
- Better instructions for using existing decorators and middleware
- Clearer examples of the context-gathering process

## [1.0.0] - 2025-01-30

### Added
- Initial release of DryRunSecurity remediation skill
- Support for Claude Code (plugin system)
- Support for Cursor (`.cursorrules`)
- Support for Windsurf (`.windsurfrules`)
- Support for generic AI assistants (`RULES.md`)

### Philosophy
- Context-first approach: Skills guide AI to understand your codebase before suggesting fixes
- Research-driven: References authoritative sources (official docs, OWASP, CWE) rather than static examples
- Minimal fixes: Changes only what's necessary, matches existing code patterns

### Supported Vulnerability Types
- Works with any vulnerability DryRunSecurity identifies
- SQL Injection, XSS, CSRF, SSRF, IDOR, Mass Assignment
- Auth Bypass, Hardcoded Secrets, Path Traversal
- Command Injection, Prompt Injection, Race Conditions
- And more

[Unreleased]: https://github.com/DryRunSecurity/external-plugin-marketplace/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/DryRunSecurity/external-plugin-marketplace/releases/tag/v1.0.1
[1.2.0]: https://github.com/DryRunSecurity/external-plugin-marketplace/releases/tag/v1.2.0
[1.1.0]: https://github.com/DryRunSecurity/external-plugin-marketplace/releases/tag/v1.1.0
[1.0.0]: https://github.com/DryRunSecurity/external-plugin-marketplace/releases/tag/v1.0.0
