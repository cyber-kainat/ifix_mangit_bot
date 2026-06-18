"""
aiosqlite-moslashuvchan yupqa qatlam.

DATABASE_URL (yoki DATABASE_PUBLIC_URL) bo'lsa — PostgreSQL (asyncpg) ustida ishlaydi.
Bo'lmasa — haqiqiy aiosqlite (lokal sinov uchun).

Maqsad: db.py'ni deyarli o'zgartirmasdan (faqat `import pgcompat as aiosqlite`)
Postgres'da ishlatish. asyncpg `Record` obyekti ham nomli (`row["id"]`),
ham pozitsion (`row[0]`), ham unpack (`a, b = row`), ham `dict(row)`ni qo'llaydi —
shuning uchun xom Record qaytaramiz.
"""
import os
import re

_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

if not _URL:
    # ---- Lokal: haqiqiy aiosqlite ----
    import aiosqlite as _sq
    Row = _sq.Row
    connect = _sq.connect
else:
    # ---- Bulut: PostgreSQL (asyncpg) ----
    import asyncpg

    Row = dict  # db.py `row_factory = aiosqlite.Row` qiladi — bizda e'tiborsiz
    _pool = None

    async def _get_pool():
        global _pool
        if _pool is None:
            _pool = await asyncpg.create_pool(
                _URL, min_size=1, max_size=5, command_timeout=30)
        return _pool

    def _to_pg(sql: str) -> str:
        # ?  ->  $1, $2 ...
        out, i = [], 0
        for ch in sql:
            if ch == "?":
                i += 1
                out.append(f"${i}")
            else:
                out.append(ch)
        sql = "".join(out)
        sql = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
                     "BIGSERIAL PRIMARY KEY", sql, flags=re.I)
        # SQLite INTEGER = 64-bit; PG INTEGER = 32-bit (telegram_id sig'maydi) -> BIGINT
        sql = re.sub(r"\bINTEGER\b", "BIGINT", sql, flags=re.I)
        sql = re.sub(r"\s+COLLATE\s+NOCASE", "", sql, flags=re.I)
        # SQLite LIKE katta-kichik harfga befarq — PG'da ILIKE shunday
        sql = re.sub(r"\bLIKE\b", "ILIKE", sql, flags=re.I)
        # created_at va h.k. — kod string saqlaydi (uz_now_str), shuning uchun TEXT
        sql = re.sub(r"TIMESTAMP\s+DEFAULT\s+CURRENT_TIMESTAMP",
                     "TEXT DEFAULT (now()::text)", sql, flags=re.I)
        sql = re.sub(r"\bTIMESTAMP\b", "TEXT", sql, flags=re.I)
        return sql

    class _Cursor:
        def __init__(self, rows=None, lastrowid=None):
            self._rows = rows if rows is not None else []
            self.lastrowid = lastrowid

        async def fetchall(self):
            return self._rows

        async def fetchone(self):
            return self._rows[0] if self._rows else None

    class _Conn:
        def __init__(self, conn):
            self._c = conn
            self.row_factory = None  # e'tiborsiz

        async def execute(self, sql, params=()):
            params = tuple(params or ())
            # PRAGMA table_info(X)  ->  information_schema (cid,name,type pozitsiyalari saqlanadi)
            m = re.match(r"\s*pragma\s+table_info\(\s*['\"]?(\w+)['\"]?\s*\)",
                         sql, flags=re.I)
            if m:
                rows = await self._c.fetch(
                    "SELECT ordinal_position AS cid, column_name AS name, "
                    "data_type AS type FROM information_schema.columns "
                    "WHERE table_name = $1 ORDER BY ordinal_position", m.group(1))
                return _Cursor(list(rows))
            low0 = sql.lstrip()[:8].lower()
            if low0.startswith(("pragma", "begin", "vacuum")):
                return _Cursor()
            q = _to_pg(sql)
            lowq = q.lstrip().lower()
            if lowq.startswith("select") or " returning " in lowq:
                rows = await self._c.fetch(q, *params)
                return _Cursor(list(rows))
            if lowq.startswith("insert"):
                q2 = q.rstrip().rstrip(";")
                if re.match(r"\s*insert\s+or\s+ignore", q2, flags=re.I):
                    q2 = re.sub(r"insert\s+or\s+ignore", "INSERT", q2,
                                count=1, flags=re.I)
                    q2 += " ON CONFLICT DO NOTHING"
                # lastrowid uchun RETURNING id (id ustuni bo'lmasa — fallback)
                try:
                    row = await self._c.fetchrow(q2 + " RETURNING id", *params)
                    return _Cursor(lastrowid=(row["id"] if row else None))
                except (asyncpg.UndefinedColumnError,
                        asyncpg.PostgresSyntaxError):
                    await self._c.execute(q2, *params)
                    return _Cursor()
            # UPDATE / DELETE / DDL / boshqa
            try:
                await self._c.execute(q, *params)
            except asyncpg.DuplicateColumnError:
                pass  # ALTER ADD COLUMN — allaqachon mavjud
            return _Cursor()

        async def commit(self):
            pass  # asyncpg autocommit

        async def rollback(self):
            pass

    class _Ctx:
        async def __aenter__(self):
            self._pool = await _get_pool()
            self._conn = await self._pool.acquire()
            return _Conn(self._conn)

        async def __aexit__(self, *a):
            await self._pool.release(self._conn)

    def connect(_name=None):
        return _Ctx()
