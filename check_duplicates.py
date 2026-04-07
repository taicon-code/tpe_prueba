import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

lines = []

lines.append("=== TODOS los FK constraints ===")
with connection.cursor() as c:
    c.execute("""
        SELECT kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.COLUMN_NAME,
               kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.TABLE_CONSTRAINTS tc
          ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
         AND kcu.TABLE_SCHEMA    = tc.TABLE_SCHEMA
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
        ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME
    """)
    for r in c.fetchall():
        lines.append(f"  {r[0]}.{r[2]}  [{r[1]}]  ->  {r[3]}.{r[4]}")

for tabla in ['pm_sim', 'abog_sim', 'res', 'rr', 'autotpe', 'rap', 'raee', 'autotsp', 'dictamen']:
    lines.append(f"\n=== SHOW CREATE TABLE {tabla} ===")
    with connection.cursor() as c:
        try:
            c.execute(f"SHOW CREATE TABLE `{tabla}`")
            lines.append(c.fetchone()[1])
        except Exception as e:
            lines.append(f"  ERROR: {e}")

output = "\n".join(lines)
with open("fk_report.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("Reporte guardado en fk_report.txt")
print(output[:3000])
