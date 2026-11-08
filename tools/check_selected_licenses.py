import yaml
import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()

# Check licenses of all skills currently marked selected
c.execute("""
    SELECT sm.slug, s.license, s.source_name, sm.module_id 
    FROM skill_modules sm 
    JOIN skills s ON sm.slug = s.slug 
    WHERE sm.status = 'selected'
""")
rows = c.fetchall()
print(f"Total selected skills: {len(rows)}")
bad_licenses = [r for r in rows if r[1] not in ("MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0")]
print(f"Bad or unknown licenses: {len(bad_licenses)}")
for b in bad_licenses:
    print(f"  - {b[0]}: license='{b[1]}' (src={b[2]})")

conn.close()

