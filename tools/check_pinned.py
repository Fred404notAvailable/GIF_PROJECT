import yaml

with open("DevCrew-Vault/catalog.yaml", "r", encoding="utf-8") as f:
    cat = yaml.safe_load(f)

for mod in cat.get("modules", []):
    m_id = mod["id"]
    m_name = mod["name"]
    print(f"=== Module {m_id}: {m_name} ===")
    for p in mod.get("pinned_slots", []):
        slot = p.get("slot")
        slug = p.get("slug")
        matched = p.get("matched_slug")
        status = p.get("status")
        src = p.get("source")
        print(f"  Slot {slot:02d}: slug='{slug}', matched='{matched}', status='{status}', src='{src}'")

