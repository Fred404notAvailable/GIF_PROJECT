# Validation Report — code-review-playbook
**Status:** invalid
## Errors
- Optional field 'allowed-tools' has wrong type (expected list, got str)
## Warnings
- Body is 8121 chars (>8000); consider moving large content to references/
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\run-pr-checks.py line 88: '(r"eval\\s*\\(", "Use of eval() - potential code injection"),'
