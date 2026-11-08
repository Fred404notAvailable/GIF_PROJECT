from pathlib import Path

sources = ["szum-tech", "cybersecurity-skills", "better-auth", "claudekit", "modernstack", "trailofbits"]

for s in sources:
    p = Path(".staging") / s
    if not p.exists():
        print(f"{s}: DOES NOT EXIST in .staging")
        continue
    skill_mds = list(p.rglob("SKILL.md"))
    print(f"{s}: exists in .staging, found {len(skill_mds)} SKILL.md files")
    for sm in skill_mds[:5]:
        print(f"   - {sm.relative_to(p)}")
    if len(skill_mds) > 5:
        print(f"   ... and {len(skill_mds)-5} more")

