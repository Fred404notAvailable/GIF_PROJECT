import yaml
import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()

# Get all currently selected skills
selected_skills = {r[0]: {"source": r[1], "license": r[2], "module_id": r[3]} 
                   for r in c.execute("SELECT sm.slug, s.source_name, s.license, sm.module_id FROM skill_modules sm JOIN skills s ON sm.slug = s.slug WHERE sm.status = 'selected'").fetchall()}

with open("DevCrew-Vault/catalog.yaml", "r", encoding="utf-8") as f:
    cat = yaml.safe_load(f)

print(f"Total selected skills in DB: {len(selected_skills)}")

used_skills = set()
matched_slots = []
unfilled_slots = []

for mod in cat.get("modules", []):
    m_id = mod["id"]
    for p in mod.get("pinned_slots", []):
        slot = p.get("slot")
        expected_slug = p.get("slug")
        expected_src = p.get("source")
        
        # Check strict matching: does expected_slug exist in selected_skills and not already used?
        if expected_slug in selected_skills and expected_slug not in used_skills:
            actual = selected_skills[expected_slug]
            used_skills.add(expected_slug)
            matched_slots.append((slot, m_id, expected_slug, actual["source"], actual["license"], "matched"))
        else:
            # Unfilled
            unfilled_slots.append((slot, m_id, expected_slug, expected_src))

print(f"\nStrict matched slots: {len(matched_slots)}")
print(f"Unfilled slots: {len(unfilled_slots)}")

backfill_skills = [slug for slug in selected_skills if slug not in used_skills]
print(f"Unpinned backfill skills count: {len(backfill_skills)}")
for b in backfill_skills:
    print(f"  - {b} (mod={selected_skills[b]['module_id']}, src={selected_skills[b]['source']})")

conn.close()

