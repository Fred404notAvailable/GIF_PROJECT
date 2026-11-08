import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()

for m_id in range(1, 8):
    c.execute("""
        SELECT sm.slug, s.source_name, s.license 
        FROM skill_modules sm 
        JOIN skills s ON sm.slug = s.slug 
        WHERE sm.status = 'selected' AND sm.module_id = ?
        ORDER BY sm.slug
    """, (m_id,))
    rows = c.fetchall()
    print(f"=== Module {m_id}: {len(rows)} selected skills ===")
    for r in rows:
        print(f"  - {r[0]} ({r[1]}, {r[2]})")

conn.close()

