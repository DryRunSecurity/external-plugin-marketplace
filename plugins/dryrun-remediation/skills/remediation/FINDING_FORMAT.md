# DryRunSecurity Finding Format

DryRunSecurity findings follow this format:

```
<summary paragraph describing what the PR/MR introduces>

<details>
<summary>
[emoji] Vulnerability Title in <code>path/to/file.ext</code>
</summary>

| **Vulnerability** | Vulnerability Name |
|:---|:---|
| **Description** | Detailed explanation... |

<Permalink to affected lines>
</details>
```

## Key Elements to Extract

| Element | Location | Example |
|---------|----------|---------|
| **Vulnerability type** | Table row | "Prompt Injection", "Cross-Site Scripting" |
| **File path** | `<code>` tag in summary | `openhands/runtime/file_ops.py` |
| **Line numbers** | Permalink | `#L231-L232` → lines 231-232 |
| **Description** | Table row | Attack scenario and why it's vulnerable |
| **Severity** | Emoji | `:yellow_circle:` = needs attention, none = blocking |

## Example Parsing

```
Summary: "Prompt Injection in <code>openhands/.../file_ops.py</code>"
→ Vulnerability: Prompt Injection
→ File: openhands/runtime/plugins/agent_skills/file_ops/file_ops.py
→ Lines: 231-232 (from permalink)
→ Issue: User input concatenated directly into LLM prompt without sanitization
```
