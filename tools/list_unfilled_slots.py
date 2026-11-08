import yaml
import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()

selected_skills = {r[0]: {"source": r[1], "license": r[2], "module_id": r[3]} 
                   for r in c.execute("SELECT sm.slug, s.source_name, s.license, sm.module_id FROM skill_modules sm JOIN skills s ON sm.slug = s.slug WHERE sm.status = 'selected'").fetchall()}

with open("DevCrew-Vault/catalog.yaml", "r", encoding="utf-8") as f:
    cat = yaml.safe_load(f)

used_skills = set()
for mod in cat.get("modules", []):
    m_id = mod["id"]
    for p in mod.get("pinned_slots", []):
        slot = p.get("slot")
        expected_slug = p.get("slug")
        expected_src = p.get("source")
        if expected_slug in selected_skills and expected_slug not in used_skills:
            used_skills.add(expected_slug)
        else:
            print(f"Slot {slot:02d} (Mod {m_id}): expected '{expected_slug}' from '{expected_src}' -> unfilled")

conn.close()

