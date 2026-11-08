# Validation Report — security-audit
**Status:** invalid
## Errors
- Optional field 'allowed-tools' has wrong type (expected list, got str)
## Warnings
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\javascript.sh line 62: '# === Check for eval() usage (SA-JS-01) ==='
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\javascript.sh line 63: 'echo "=== Checking for eval() Usage ==="'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\javascript.sh line 66: 'echo "ERROR: eval() usage detected (potential code injection):"'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\javascript.sh line 70: 'echo "OK: No eval() usage detected"'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\nodejs.sh line 186: '# === Check for eval() usage ==='
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\nodejs.sh line 188: 'echo "=== Checking for eval() Usage ==="'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\nodejs.sh line 191: 'echo "ERROR: eval() usage detected:"'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\nodejs.sh line 195: 'echo "OK: No eval() usage detected"'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\python.sh line 96: '# === SA-PY-02/03: eval() / exec() code injection ==='
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\python.sh line 98: 'echo "=== Checking for eval()/exec() Code Injection ==="'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\python.sh line 102: 'echo "ERROR [SA-PY-02]: eval() calls found — risk of code injection:"'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scanners\python.sh line 106: 'echo "OK: No eval() calls detected"'
