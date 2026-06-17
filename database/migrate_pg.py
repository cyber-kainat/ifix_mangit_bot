"""
Bir martalik ko'chirish: /data/shop.db (SQLite) -> PostgreSQL.
Bot RUN_MIGRATION=1 bilan ishga tushganda chaqiriladi. SQLite faylga TEGMAYDI
(faqat o'qiydi) — shuning uchun zaxira sifatida saqlanib qoladi.
"""
import os
import sqlite3
import asyncpg


async def migrate():
    pg_url = os.getenv("DATABASE_URL")
    sqlite_path = os.getenv("DB_NAME", "/data/shop.db")
    if not pg_url:
        print("⏭ DATABASE_URL yo'q — ko'chirish o'tkazib yuborildi")
        return
    if not os.path.exists(sqlite_path):
        print(f"⏭ SQLite topilmadi ({sqlite_path}) — ko'chirish o'tkazib yuborildi")
        return

    s = sqlite3.connect(sqlite_path)
    s.row_factory = sqlite3.Row
    pg = await asyncpg.connect(pg_url)
    try:
        tables = [r[0] for r in s.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'").fetchall()]
        for t in tables:
            rows = s.execute(f"SELECT * FROM {t}").fetchall()
            if not rows:
                continue
            pgcols = {r["column_name"] for r in await pg.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=$1", t)}
            if not pgcols:
                continue
            use = [c for c in rows[0].keys() if c in pgcols]
            collist = ",".join(f'"{c}"' for c in use)
            ph = ",".join(f"${i+1}" for i in range(len(use)))
            ok = 0
            for row in rows:
                try:
                    await pg.execute(
                        f"INSERT INTO {t} ({collist}) VALUES ({ph}) "
                        f"ON CONFLICT DO NOTHING", *[row[c] for c in use])
                    ok += 1
                except Exception:
                    pass
            if "id" in pgcols:
                try:
                    await pg.execute(
                        f"SELECT setval(pg_get_serial_sequence('{t}','id'), "
                        f"COALESCE((SELECT MAX(id) FROM {t}),1))")
                except Exception:
                    pass
            print(f"  {t}: {ok}/{len(rows)} ko'chirildi")
        print("✅ Ko'chirish tugadi")
    finally:
        await pg.close()
        s.close()
