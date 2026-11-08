import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()

sources = ["szum-tech", "cybersecurity-skills", "better-auth", "claudekit", "modernstack", "trailofbits", "hashicorp"]

for s in sources:
    c.execute("SELECT slug, name, validation_status, validation_messages, license FROM skills WHERE source_name = ?", (s,))
    rows = c.fetchall()
    print(f"=== Source: {s} ({len(rows)} skills in DB) ===")
    for r in rows[:10]:
        print(f"  {r[0]}: status={r[2]}, license={r[4]}, msgs={r[3]}")
    if len(rows) > 10:
        print(f"  ... and {len(rows)-10} more")

conn.close()

