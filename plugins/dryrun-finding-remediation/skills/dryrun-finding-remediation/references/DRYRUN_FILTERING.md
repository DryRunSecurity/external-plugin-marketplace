# What DryRunSecurity Flags (and What It Doesn't)

This reference describes filtering for **code vulnerabilities**, not SCA findings. SCA findings cover dependency advisories and may require version upgrades. Historical findings describe the scanned source; verify whether the vulnerable behavior still exists on the chosen remediation base.

## What Gets Filtered OUT (Not Reported)

DryRunSecurity intentionally does NOT report:

### Non-Code Issues
- Outdated dependencies or CVEs in libraries (use dependency scanners for these)
- Language/runtime version issues (e.g., "Go 1.24 has CVE-XXXX")
- Infrastructure or configuration assumptions

### False Positives & Low-Impact Issues
- Vulnerabilities requiring another unproven vulnerability to exist first
- Context-inappropriate findings (XSS in CLI tools, CSRF without browser context, SQLi in NoSQL)
- Theoretical risks without practical exploit paths
- Issues only exploitable by already-authorized users against themselves

### Sensitive Logging False Positives
- Exception/error logging (unless proven to contain secrets or PII)
- ID logging (user IDs, UUIDs, transaction IDs)
- Metadata logging (timestamps, counters, non-sensitive headers)
- Only flags logging of: passwords, API keys, tokens, actual PII

### Developer/Test Context
- Vulnerabilities in test files or test utilities
- Debug endpoints requiring source code access
- Issues requiring repository write access

### Non-Security Nitpicks
- Code style or best practice suggestions
- "Should use X instead of Y" without security impact
- Missing rate limiting without abuse scenario
- Verbose error messages without credential/PII exposure

## What DOES Get Reported

If DryRunSecurity flagged it, it passed rigorous filtering. The finding represents:
- A real vulnerability in application source code
- An exploitable issue with a practical attack path
- Something that requires code changes to fix (not just version bumps)
- A confirmed risk after multiple stages of validation

Use the finding's evidence to guide remediation, and verify its applicability on the chosen base. If the reported behavior is already fixed, explain the evidence rather than manufacturing a change.
