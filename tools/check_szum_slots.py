from pathlib import Path

slots = ["server-actions", "react-19-compiler", "tailwind-css-4", "storybook-testing"]
p = Path(".staging/szum-tech")

for s in slots:
    found = list(p.rglob(f"*{s}*"))
    print(f"Slot {s}: found {[str(f.relative_to(p)) for f in found if f.is_dir()]}")

