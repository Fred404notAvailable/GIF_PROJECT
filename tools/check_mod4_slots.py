import yaml

with open("DevCrew-Vault/catalog.yaml", "r", encoding="utf-8") as f:
    cat = yaml.safe_load(f)

for mod in cat.get("modules", []):
    if mod["id"] == 4:
        for p in mod.get("pinned_slots", []):
            print(f"Slot {p.get('slot')}: {p.get('slug')} (matched: {p.get('matched_slug')}, status: {p.get('status')}, src: {p.get('source')})")

