import sqlite3
import yaml
from pathlib import Path
from datetime import datetime, timezone

def approve_all():
    conn = sqlite3.connect("DevCrew-Vault/registry.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT name, version, slug, capability_class, requires_secrets, license
        FROM mcp_servers
        WHERE status IN ('selected', 'approved')
        ORDER BY name
    """)
    servers = cur.fetchall()
    print(f"Found {len(servers)} vetted servers to approve.")

    # 1. Update catalog.yaml approvals
    catalog_path = Path("DevCrew-Vault/catalog.yaml")
    cat = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    
    approvals = {}
    for name, ver, slug, cap, sec, lic in servers:
        approvals[name] = ver
    
    cat["approvals"] = approvals
    catalog_path.write_text(yaml.dump(cat, sort_keys=False), encoding="utf-8")
    print(f"Updated {catalog_path} with {len(approvals)} approvals.")

    # 2. Update database
    now_iso = datetime.now(timezone.utc).isoformat()
    for name, ver, slug, cap, sec, lic in servers:
        cur.execute("""
            UPDATE mcp_servers
            SET status = 'approved',
                approved_version = ?,
                approved_by = 'user (approve all request)',
                approved_at = ?
            WHERE name = ?
        """, (ver, now_iso, name))
    conn.commit()
    conn.close()
    print("Database statuses updated to 'approved'.")

if __name__ == "__main__":
    approve_all()

