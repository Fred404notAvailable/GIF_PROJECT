from pathlib import Path
from tools.validate_skills import validate_skill_folder

skill_dir = Path(".staging/cybersecurity-skills/skills/owasp-audit")
res = validate_skill_folder(skill_dir)
print("Validation result for owasp-audit:", res.status)
print("Errors:", res.errors)
print("Warnings:", len(res.warnings))

