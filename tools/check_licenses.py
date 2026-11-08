import sqlite3
import json

conn = sqlite3.connect("DevCrew-Vault/registry.db")
cur = conn.cursor()
rows = cur.execute("SELECT slug, name, snapshot_json FROM mcp_servers WHERE status = 'selected'").fetchall()

for slug, name, snap in rows:
    if not snap:
        continue
    data = json.loads(snap)
    lic = data.get("license")
    pkg_lics = [p.get("license") for p in data.get("packages", []) if isinstance(p, dict)]
    rem_lics = [r.get("license") for r in data.get("remotes", []) if isinstance(r, dict)]
    print(f"{slug} ({name}): top_lic={lic}, pkg_lics={pkg_lics}, rem_lics={rem_lics}, keys={list(data.keys())}")

conn.close()
