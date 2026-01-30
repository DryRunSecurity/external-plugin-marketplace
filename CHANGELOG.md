# Changelog

All notable changes to DryRunSecurity Skills will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/DryRunSecurity/external-plugin-marketplace/releases/tag/v1.0.0
