import sqlite3

conn = sqlite3.connect("DevCrew-Vault/registry.db")
c = conn.cursor()
c.execute("UPDATE skill_modules SET status = 'candidate' WHERE slug IN ('backend-development', 'svelte')")
conn.commit()
print("Updated candidate count:", c.rowcount)
conn.close()

