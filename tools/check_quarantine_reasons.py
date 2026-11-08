from pathlib import Path

qdir = Path("DevCrew-Vault/_quarantine")
reports = list(qdir.glob("*/REPORT.md"))
print(f"Total quarantined skills with REPORT.md: {len(reports)}")

sample_skills = ["agent-supply-chain-audit", "builder-factory", "owasp-audit", "server-actions", "tailwind-css-4", "storybook-testing"]

for s in sample_skills:
    matches = list(qdir.glob(f"*{s}*/REPORT.md"))
    if matches:
        print(f"\n=== Report for {s} ({matches[0].parent.name}) ===")
        print(matches[0].read_text(encoding="utf-8")[:500])
    else:
        print(f"\n{s}: Not found in _quarantine")

