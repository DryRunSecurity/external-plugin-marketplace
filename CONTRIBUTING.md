# Contributing to DryRunSecurity Skills

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-change
   ```

2. **Make your changes** to the skill files:
   - `plugins/dryrun-remediation/skills/remediation/SKILL.md` - Remediation skill (Claude Code)
   - `plugins/dryrun-pr-review/skills/dryrun-pr-review/SKILL.md` - PR review skill (Claude Code)
   - `standalone/.cursorrules` - Cursor (both workflows combined)
   - `standalone/.windsurfrules` - Windsurf (both workflows combined)
   - `standalone/RULES.md` - Generic/VS Code (both workflows combined)
   - `standalone/copilot-instructions.md` - GitHub Copilot (both workflows combined)

3. **Keep files in sync** - The standalone files combine both workflows (Workflow 1: Remediation, Workflow 2: PR Review). When updating a workflow, update the corresponding Claude Code SKILL.md and all four standalone files.

4. **Open a PR** to `main`

5. **After merge**, create a release (see below)

### Releasing a New Version

After merging changes to `main`:

1. **Update version numbers** in all files:
   ```
   # SKILL.md frontmatter
   version: 1.1.0

   # Standalone file headers
   # Version: 1.1.0
   ```

2. **Update CHANGELOG.md** with the new version

3. **Update manifest versions** (if needed):
   - `.claude-plugin/marketplace.json`
   - `plugins/dryrun-remediation/.claude-plugin/plugin.json`
   - `plugins/dryrun-pr-review/.claude-plugin/plugin.json`

4. **Commit the version bump**:
   ```bash
   git add -A
   git commit -m "Bump version to 1.1.0"
   git push
   ```

5. **Create and push the git tag**:
   ```bash
   git tag -a v1.1.0 -m "Release 1.1.0: Brief description of changes"
   git push origin v1.1.0
   ```

6. **Create a GitHub Release** (optional but recommended):
   - Go to Releases → Draft a new release
   - Choose the tag you just created
   - Add release notes from CHANGELOG

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes to skill behavior
- **MINOR** (1.0.0 → 1.1.0): New features, significant improvements
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, small tweaks

### File Sync Checklist

When making changes, ensure all versions are updated:

**Remediation workflow changes:**
- [ ] `plugins/dryrun-remediation/skills/remediation/SKILL.md`
- [ ] Workflow 1 section in all four standalone files

**PR review workflow changes:**
- [ ] `plugins/dryrun-pr-review/skills/dryrun-pr-review/SKILL.md`
- [ ] Workflow 2 section in all four standalone files

**All releases:**
- [ ] `standalone/.cursorrules`
- [ ] `standalone/.windsurfrules`
- [ ] `standalone/RULES.md`
- [ ] `standalone/copilot-instructions.md`
- [ ] Version numbers match across all files
- [ ] `CHANGELOG.md` updated (for releases)

### Testing Changes

Before releasing:

1. **Test with Cursor**: Copy `.cursorrules` to a test project, ask Cursor to fix a sample vulnerability
2. **Test with Claude Code**: Install the plugin locally and test
3. **Verify the skill**:
   - Does it guide research of authoritative sources?
   - Does it examine the codebase context?
   - Does it produce contextual fixes?

### Quick Commands

```bash
# Check current version in files
grep -h "Version:" standalone/.cursorrules plugins/dryrun-remediation/skills/remediation/SKILL.md plugins/dryrun-pr-review/skills/dryrun-pr-review/SKILL.md

# See all tags
git tag -l

# See what changed since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```
