"""
SQLite ma'lumotlar bazasi - barcha jadvallar va funksiyalar
Yangilangan: kategoriyalar, tannarx (cost_price), qarz, foyda hisoboti
"""
import os
import aiosqlite
from datetime import datetime
from typing import Optional

from config import uz_now_str


# Bazaning yo'li. Railway da Volume ulanganda env orqali "/data/shop.db" beriladi.
# Lokal ishlatishda standart "shop.db".
DB_NAME = os.getenv("DB_NAME", "shop.db")

# Do'kondan naqd sotilgan (botsiz) savdolar shu maxsus "mijoz" ostida qayd etiladi.
# Telegram ID lar bunchalik kichik bo'lmaydi, shuning uchun to'qnashmaydi.
WALKIN_TG_ID = 1


# Standart kategoriyalar (init paytida bazaga qo'shiladi)
DEFAULT_CATEGORIES = [
    # (name, icon, requires_model)
    ("Ekran", "📱", 1),
    ("Orqa krishka", "🪞", 1),
    ("Batareya", "🔋", 1),
    ("Kamera shisha", "📷", 1),
    ("Pastki plata", "🔌", 1),
    ("Aksessuar", "🧰", 0),
]


# ============ HELPERS ============

async def _column_exists(db, table: str, column: str) -> bool:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in await cursor.fetchall()]
    return column in cols


async def init_db():
    """Bazani yaratish va boshlang'ich jadvallarni o'rnatish + migratsiya"""
    # Volume yo'li berilgan bo'lsa (masalan /data/shop.db), papkani yaratib qo'yamiz
    db_dir = os.path.dirname(DB_NAME)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    async with aiosqlite.connect(DB_NAME) as db:
        # ---- Foydalanuvchilar (ustalar) jadvali ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                username TEXT,
                is_approved INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---- Brendlar ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---- Modellar ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE,
                UNIQUE(brand_id, name)
            )
        """)

        # ---- Kategoriyalar (Yangi) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📦',
                requires_model INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---- Mahsulotlar (Yangi - universal: ekran/krishka/batareya/aksessuar...) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                model_id INTEGER,
                name TEXT NOT NULL,
                cost_price REAL NOT NULL DEFAULT 0,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 3,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
            )
        """)

        # ---- Eski ekranlar jadvali (legacy, migratsiya uchun saqlanadi) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS screens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                screen_type TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
            )
        """)

        # ---- Buyurtmalar ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                screen_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                total_price REAL NOT NULL,
                payment_method TEXT NOT NULL,
                pickup_type TEXT NOT NULL,
                status TEXT DEFAULT 'kutilmoqda',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ---- Tovar qabul qilish (kirim) tarixi — o'rtacha tannarx audit uchun ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                old_cost REAL,
                new_cost REAL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---- Migration: orders jadvaliga yangi ustunlar ----
        if not await _column_exists(db, "orders", "product_id"):
            await db.execute("ALTER TABLE orders ADD COLUMN product_id INTEGER")
        if not await _column_exists(db, "orders", "payment_status"):
            # paid / debt / partial
            await db.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'paid'")
        if not await _column_exists(db, "orders", "paid_amount"):
            await db.execute("ALTER TABLE orders ADD COLUMN paid_amount REAL DEFAULT 0")
        if not await _column_exists(db, "orders", "cost_at_sale"):
            # Sotilgan paytdagi tannarx (tarixiy foyda hisoboti uchun)
            await db.execute("ALTER TABLE orders ADD COLUMN cost_at_sale REAL DEFAULT 0")
        if not await _column_exists(db, "orders", "group_id"):
            # Savat (bir nechta mahsulot) bitta guruhga birlashtiriladi
            await db.execute("ALTER TABLE orders ADD COLUMN group_id TEXT")
        # Eski/yagona buyurtmalarga group_id beramiz (S<id>) — guruhlash bir xil ishlashi uchun
        await db.execute("UPDATE orders SET group_id = 'S' || id WHERE group_id IS NULL")

        # ---- Indekslar ----
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_group ON orders(group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_tg ON users(telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_brand ON models(brand_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_screens_model ON screens(model_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_cat ON products(category_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_model ON products(model_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_payment ON orders(payment_status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id)")

        await db.commit()

        # ---- Standart kategoriyalarni yuklash ----
        for name, icon, req_model in DEFAULT_CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO categories (name, icon, requires_model) VALUES (?, ?, ?)",
                (name, icon, req_model)
            )
        await db.commit()

        # ---- One-time migration: screens → products ----
        await _migrate_screens_to_products(db)


async def _migrate_screens_to_products(db):
    """Eski 'screens' jadvali ma'lumotlarini 'products' jadvaliga ko'chiradi (faqat 1 marta)."""
    # Ekran kategoriya ID sini olish
    cursor = await db.execute("SELECT id FROM categories WHERE name = 'Ekran'")
    row = await cursor.fetchone()
    if not row:
        return
    ekran_cat_id = row[0]

    # Allaqachon migratsiya qilinganmi?
    cursor = await db.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (ekran_cat_id,))
    products_cnt = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM screens")
    screens_cnt = (await cursor.fetchone())[0]

    if screens_cnt > 0 and products_cnt == 0:
        # Migratsiya: ID lar mos kelishi uchun aniq INSERT
        cursor = await db.execute(
            "SELECT id, model_id, screen_type, price, quantity, description FROM screens"
        )
        rows = await cursor.fetchall()
        for sid, model_id, stype, price, qty, desc in rows:
            # Tannarxni taxminiy 70% deb belgilaymiz (admin keyin yangilashi mumkin)
            cost = round(float(price) * 0.7, 2)
            await db.execute(
                """INSERT OR IGNORE INTO products
                   (id, category_id, model_id, name, cost_price, price, quantity, min_quantity, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, ekran_cat_id, model_id, stype, cost, price, qty, 3, desc or "")
            )

        # Eski buyurtmalarda product_id ni screen_id dan to'ldirish
        await db.execute(
            "UPDATE orders SET product_id = screen_id WHERE product_id IS NULL AND screen_id IS NOT NULL"
        )
        # Tannarxni taxminan to'ldirish (eski buyurtmalar uchun)
        await db.execute("""
            UPDATE orders
            SET cost_at_sale = COALESCE((
                SELECT p.cost_price * orders.quantity
                FROM products p WHERE p.id = orders.product_id
            ), 0)
            WHERE cost_at_sale = 0 OR cost_at_sale IS NULL
        """)
        # Eski buyurtmalarni "to'liq to'langan" deb belgilash
        await db.execute("""
            UPDATE orders
            SET payment_status = 'paid', paid_amount = total_price
            WHERE payment_status IS NULL OR payment_status = ''
        """)
        await db.commit()


# ============ FOYDALANUVCHI FUNKSIYALARI ============

async def add_user(telegram_id: int, full_name: str, phone: str, username: str = None) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, full_name, phone, username, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, full_name, phone, username, uz_now_str())
        )
        await db.commit()
        return cursor.lastrowid


async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_pending_users() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_approved = 0 AND is_blocked = 0 ORDER BY created_at DESC"
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id > 1 ORDER BY created_at DESC"
        )
        return [dict(row) for row in await cursor.fetchall()]


async def approve_user(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_approved = 1, is_blocked = 0 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()


async def block_user(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_blocked = 1, is_approved = 0 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()


# ============ BREND ============

async def add_brand(name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO brands (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_or_create_brand(name: str) -> int:
    """Brendni nomi bo'yicha topadi yoki yaratadi (Excel import uchun)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM brands WHERE name = ? COLLATE NOCASE", (name,))
        row = await cur.fetchone()
        if row:
            return row["id"]
        cur = await db.execute("INSERT INTO brands (name) VALUES (?)", (name,))
        await db.commit()
        return cur.lastrowid


async def get_brands() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM brands ORDER BY name")
        return [dict(row) for row in await cursor.fetchall()]


async def get_brand(brand_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM brands WHERE id = ?", (brand_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def rename_brand(brand_id: int, name: str) -> bool:
    """Brend nomini o'zgartirish. Nom band bo'lsa False qaytaradi."""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("UPDATE brands SET name = ? WHERE id = ?", (name, brand_id))
            await db.commit()
            return True
        except Exception:
            return False


async def count_brand_children(brand_id: int) -> dict:
    """Brendga tegishli model va mahsulotlar soni (o'chirishdan oldin ogohlantirish uchun)."""
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT COUNT(*) FROM models WHERE brand_id = ?", (brand_id,))
        models = (await cur.fetchone())[0]
        cur = await db.execute(
            "SELECT COUNT(*) FROM products WHERE model_id IN (SELECT id FROM models WHERE brand_id = ?)",
            (brand_id,)
        )
        products = (await cur.fetchone())[0]
        return {"models": models, "products": products}


async def delete_brand(brand_id: int):
    """Brendni va unga bog'liq barcha model/mahsulot/ekranlarni o'chiradi (cascade)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM products WHERE model_id IN (SELECT id FROM models WHERE brand_id = ?)",
            (brand_id,)
        )
        await db.execute(
            "DELETE FROM screens WHERE model_id IN (SELECT id FROM models WHERE brand_id = ?)",
            (brand_id,)
        )
        await db.execute("DELETE FROM models WHERE brand_id = ?", (brand_id,))
        await db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
        await db.commit()


# ============ MODEL ============

async def add_model(brand_id: int, name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO models (brand_id, name) VALUES (?, ?)",
            (brand_id, name)
        )
        await db.commit()
        return cursor.lastrowid


async def get_or_create_model(brand_id: int, name: str) -> int:
    """Modelni topadi yoki yaratadi (Excel import uchun)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id FROM models WHERE brand_id = ? AND name = ? COLLATE NOCASE",
            (brand_id, name)
        )
        row = await cur.fetchone()
        if row:
            return row["id"]
        cur = await db.execute(
            "INSERT INTO models (brand_id, name) VALUES (?, ?)", (brand_id, name)
        )
        await db.commit()
        return cur.lastrowid


async def get_models(brand_id: int) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM models WHERE brand_id = ? ORDER BY name", (brand_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_model(model_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT m.*, b.name as brand_name FROM models m
               JOIN brands b ON m.brand_id = b.id WHERE m.id = ?""",
            (model_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def rename_model(model_id: int, name: str) -> bool:
    """Model nomini o'zgartirish. Nom band bo'lsa False qaytaradi."""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("UPDATE models SET name = ? WHERE id = ?", (name, model_id))
            await db.commit()
            return True
        except Exception:
            return False


async def count_model_products(model_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT COUNT(*) FROM products WHERE model_id = ?", (model_id,))
        return (await cur.fetchone())[0]


async def get_all_models_of_brand(brand_id: int) -> list:
    """Brendning BARCHA modellari (mahsuloti bor-yo'qligidan qat'i nazar)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM models WHERE brand_id = ? ORDER BY name", (brand_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_all_products_of_model(model_id: int) -> list:
    """Modelning BARCHA mahsulotlari (har qanday kategoriya)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT p.*, c.name as category_name, c.icon as category_icon
               FROM products p JOIN categories c ON p.category_id = c.id
               WHERE p.model_id = ? ORDER BY c.id, p.name""",
            (model_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def delete_model(model_id: int):
    """Modelni va unga bog'liq mahsulot/ekranlarni o'chiradi (cascade)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products WHERE model_id = ?", (model_id,))
        await db.execute("DELETE FROM screens WHERE model_id = ?", (model_id,))
        await db.execute("DELETE FROM models WHERE id = ?", (model_id,))
        await db.commit()


# ============ KATEGORIYALAR ============

async def get_categories() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories ORDER BY id")
        return [dict(row) for row in await cursor.fetchall()]


async def get_category(category_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_category_by_name(name: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ============ MAHSULOTLAR ============

async def add_product(category_id: int, model_id: Optional[int], name: str,
                      cost_price: float, price: float, quantity: int = 0,
                      min_quantity: int = 3, description: str = "") -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO products
               (category_id, model_id, name, cost_price, price, quantity, min_quantity, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category_id, model_id, name, cost_price, price, quantity, min_quantity, description, uz_now_str())
        )
        await db.commit()
        return cursor.lastrowid


async def upsert_product(category_id: int, model_id: Optional[int], name: str,
                         cost_price: float, price: float, quantity: int,
                         min_quantity: int, description: str = "") -> str:
    """Excel import uchun: bir xil (kategoriya+model+nom) bo'lsa yangilaydi, bo'lmasa qo'shadi.
    Qaytaradi: 'added' yoki 'updated'."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if model_id is None:
            cur = await db.execute(
                "SELECT id FROM products WHERE category_id = ? AND model_id IS NULL AND name = ? COLLATE NOCASE",
                (category_id, name)
            )
        else:
            cur = await db.execute(
                "SELECT id FROM products WHERE category_id = ? AND model_id = ? AND name = ? COLLATE NOCASE",
                (category_id, model_id, name)
            )
        row = await cur.fetchone()
        if row:
            await db.execute(
                """UPDATE products SET cost_price = ?, price = ?, quantity = ?,
                   min_quantity = ?, description = ? WHERE id = ?""",
                (cost_price, price, quantity, min_quantity, description, row["id"])
            )
            await db.commit()
            return "updated"
        await db.execute(
            """INSERT INTO products
               (category_id, model_id, name, cost_price, price, quantity, min_quantity, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category_id, model_id, name, cost_price, price, quantity, min_quantity, description, uz_now_str())
        )
        await db.commit()
        return "added"


async def get_product(product_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT p.*, c.name as category_name, c.icon as category_icon, c.requires_model,
                      m.name as model_name, b.name as brand_name, b.id as brand_id
               FROM products p
               JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE p.id = ?""",
            (product_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_products_by_model(model_id: int, category_id: int) -> list:
    """Belgilangan model va kategoriya bo'yicha mahsulotlar (masalan iPhone 13 ning batareyalari)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products WHERE model_id = ? AND category_id = ? ORDER BY name",
            (model_id, category_id)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_universal_products(category_id: int) -> list:
    """Brendsiz/modelsiz mahsulotlar (aksessuarlar)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products WHERE category_id = ? AND model_id IS NULL ORDER BY name",
            (category_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_brands_with_products(category_id: int) -> list:
    """Tanlangan kategoriyada mahsuloti bor brendlar"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT DISTINCT b.* FROM brands b
               JOIN models m ON m.brand_id = b.id
               JOIN products p ON p.model_id = m.id
               WHERE p.category_id = ?
               ORDER BY b.name""",
            (category_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_models_with_products(brand_id: int, category_id: int) -> list:
    """Tanlangan brend + kategoriya da mahsuloti bor modellar"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT DISTINCT m.* FROM models m
               JOIN products p ON p.model_id = m.id
               WHERE m.brand_id = ? AND p.category_id = ?
               ORDER BY m.name""",
            (brand_id, category_id)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def update_product_price(product_id: int, price: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET price = ? WHERE id = ?", (price, product_id))
        await db.commit()


async def update_product_cost(product_id: int, cost: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET cost_price = ? WHERE id = ?", (cost, product_id))
        await db.commit()


async def update_product_quantity(product_id: int, quantity: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET quantity = ? WHERE id = ?", (quantity, product_id))
        await db.commit()


async def update_product_min_quantity(product_id: int, min_qty: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET min_quantity = ? WHERE id = ?", (min_qty, product_id))
        await db.commit()


async def rename_product(product_id: int, name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET name = ? WHERE id = ?", (name, product_id))
        await db.commit()


async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def get_low_stock_products(category_id: Optional[int] = None) -> list:
    """Tugab qolayotgan mahsulotlar (quantity <= min_quantity).
    Toshkentdan zakaz qilish uchun ro'yxat."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon,
                   m.name as model_name, b.name as brand_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN models m ON p.model_id = m.id
            LEFT JOIN brands b ON m.brand_id = b.id
            WHERE p.quantity <= p.min_quantity
        """
        params = []
        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)
        query += " ORDER BY c.id, p.quantity ASC, b.name, m.name"
        cursor = await db.execute(query, params)
        return [dict(row) for row in await cursor.fetchall()]


# ============ TOVAR QABUL QILISH (kirim + o'rtacha tannarx WAC) ============

async def receive_stock(product_id: int, quantity: int, unit_cost: float, note: str = "") -> Optional[dict]:
    """Yangi tovar kelganda: skladni oshiradi va tannarxni O'RTACHA (weighted average) qilib yangilaydi.

    Yangi tannarx = (eski_dona*eski_tannarx + kelgan_dona*kelgan_narx) / (eski_dona + kelgan_dona)
    Bu ikki do'kondan har xil narxda kelgan tovarlar aralashganda foydani to'g'ri chiqaradi.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT quantity, cost_price FROM products WHERE id = ?", (product_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        cur_qty = int(row["quantity"] or 0)
        cur_cost = float(row["cost_price"] or 0)
        new_qty = cur_qty + quantity
        if new_qty > 0:
            new_cost = (cur_qty * cur_cost + quantity * unit_cost) / new_qty
        else:
            new_cost = unit_cost
        new_cost = round(new_cost, 2)

        await db.execute(
            "UPDATE products SET quantity = ?, cost_price = ? WHERE id = ?",
            (new_qty, new_cost, product_id)
        )
        await db.execute(
            """INSERT INTO stock_receipts
               (product_id, quantity, unit_cost, total_cost, old_cost, new_cost, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (product_id, quantity, unit_cost, unit_cost * quantity, cur_cost, new_cost, note, uz_now_str())
        )
        await db.commit()
        return {
            "old_qty": cur_qty, "new_qty": new_qty,
            "old_cost": cur_cost, "new_cost": new_cost,
            "unit_cost": unit_cost, "added": quantity,
            "batch_total": unit_cost * quantity,
        }


async def get_recent_receipts(limit: int = 20) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT r.*, p.name AS product_name, c.icon AS category_icon,
                      m.name AS model_name, b.name AS brand_name
               FROM stock_receipts r
               LEFT JOIN products p ON r.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               ORDER BY r.id DESC LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]


# ============ BUYURTMALAR ============

async def add_order(user_id: int, product_id: int, quantity: int, total_price: float,
                    cost_at_sale: float, payment_method: str, pickup_type: str,
                    payment_status: str = "paid", paid_amount: float = 0,
                    group_id: str = None) -> int:
    """Buyurtma yaratish.
    payment_status: 'paid' (to'liq), 'debt' (qarz), 'partial' (qisman)
    cost_at_sale: butun buyurtmaning tannarxi (cost_price * quantity)
    group_id: savatdagi mahsulotlarni birlashtirish uchun. None bo'lsa 'S<id>' beriladi.
    """
    if payment_status == "paid":
        paid_amount = total_price
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO orders
               (user_id, product_id, screen_id, quantity, total_price, cost_at_sale,
                payment_method, pickup_type, payment_status, paid_amount, created_at, group_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, product_id, product_id, quantity, total_price, cost_at_sale,
             payment_method, pickup_type, payment_status, paid_amount, uz_now_str(), group_id)
        )
        oid = cursor.lastrowid
        if not group_id:
            await db.execute("UPDATE orders SET group_id = ? WHERE id = ?", (f"S{oid}", oid))
        await db.commit()
        return oid


async def get_order(order_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, u.full_name, u.phone, u.telegram_id,
                      p.name as product_name, p.price as unit_price, p.cost_price as unit_cost,
                      c.name as category_name, c.icon as category_icon,
                      m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN users u ON o.user_id = u.id
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.id = ?""",
            (order_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_orders(user_id: int, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, p.name as product_name,
                      c.name as category_name, c.icon as category_icon,
                      m.name as model_name, b.name as brand_name
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.user_id = ?
               ORDER BY o.created_at DESC LIMIT ?""",
            (user_id, limit)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_pending_orders() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, u.full_name, u.phone, u.telegram_id,
                      p.name as product_name,
                      c.name as category_name, c.icon as category_icon,
                      m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN users u ON o.user_id = u.id
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.status = 'kutilmoqda'
               ORDER BY o.created_at DESC"""
        )
        return [dict(row) for row in await cursor.fetchall()]


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


# ============ BUYURTMA GURUHLARI (savat + boshqaruv) ============

async def list_order_groups(status: str = None, limit: int = 30) -> list:
    """Buyurtmalarni guruh (savat) bo'yicha ro'yxatlaydi. status=None bo'lsa hammasi."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT o.group_id, MIN(o.id) AS min_id, o.status,
                   o.payment_method, o.pickup_type, o.payment_status,
                   MIN(o.created_at) AS created_at,
                   u.full_name, u.phone, u.telegram_id,
                   COUNT(*) AS items, SUM(o.quantity) AS units,
                   SUM(o.total_price) AS total, SUM(o.paid_amount) AS paid
            FROM orders o JOIN users u ON o.user_id = u.id
        """
        params = []
        if status:
            query += " WHERE o.status = ?"
            params.append(status)
        query += " GROUP BY o.group_id ORDER BY min_id DESC LIMIT ?"
        params.append(limit)
        cur = await db.execute(query, params)
        return [dict(r) for r in await cur.fetchall()]


async def get_order_group(group_id: str) -> Optional[dict]:
    """Guruh sarlavhasi (mijoz, jami) + ichidagi mahsulotlar."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT o.group_id, o.status, o.payment_method, o.pickup_type, o.payment_status,
                      o.created_at, u.full_name, u.phone, u.telegram_id, u.id AS user_db_id,
                      COUNT(*) AS items, SUM(o.quantity) AS units,
                      SUM(o.total_price) AS total, SUM(o.paid_amount) AS paid,
                      SUM(o.total_price - o.paid_amount) AS debt
               FROM orders o JOIN users u ON o.user_id = u.id
               WHERE o.group_id = ? GROUP BY o.group_id""",
            (group_id,)
        )
        head = await cur.fetchone()
        if not head:
            return None
        cur = await db.execute(
            """SELECT o.id, o.product_id, o.quantity, o.total_price, o.cost_at_sale,
                      p.name AS product_name, c.icon AS category_icon,
                      m.name AS model_name, b.name AS brand_name
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.group_id = ? ORDER BY o.id""",
            (group_id,)
        )
        items = [dict(r) for r in await cur.fetchall()]
        result = dict(head)
        result["items"] = items
        return result


async def set_group_status(group_id: str, status: str):
    """Guruhdagi barcha buyurtmalar statusini o'zgartiradi (sklad tegmaydi)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE orders SET status = ? WHERE group_id = ?", (status, group_id))
        await db.commit()


async def _restore_stock_for_group(db, group_id: str):
    """Bekor qilinmagan qatorlar uchun skladni qaytaradi (ichki yordamchi)."""
    db.row_factory = aiosqlite.Row
    cur = await db.execute(
        "SELECT product_id, quantity FROM orders WHERE group_id = ? AND status != 'bekor'",
        (group_id,)
    )
    for row in await cur.fetchall():
        if row["product_id"]:
            await db.execute(
                "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                (row["quantity"], row["product_id"])
            )


async def cancel_group(group_id: str):
    """Guruhni bekor qiladi: skladni qaytaradi + status='bekor' (yozuv qoladi, hisobotda yo'q)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await _restore_stock_for_group(db, group_id)
        await db.execute("UPDATE orders SET status = 'bekor' WHERE group_id = ?", (group_id,))
        await db.commit()


async def delete_group(group_id: str):
    """Guruhni butunlay o'chiradi: skladni qaytaradi + yozuvlarni o'chiradi (hisobotdan ham chiqadi)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await _restore_stock_for_group(db, group_id)
        await db.execute("DELETE FROM orders WHERE group_id = ?", (group_id,))
        await db.commit()


async def get_or_create_walkin_user() -> int:
    """Do'kondan naqd sotilgan savdolar uchun maxsus 'mijoz' (bir marta yaratiladi)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (WALKIN_TG_ID,))
        row = await cur.fetchone()
        if row:
            return row["id"]
        cur = await db.execute(
            """INSERT INTO users (telegram_id, full_name, phone, username, is_approved, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (WALKIN_TG_ID, "🏪 Do'kon (naqd savdo)", "-", None, uz_now_str())
        )
        await db.commit()
        return cur.lastrowid


async def get_or_create_offline_user(full_name: str, phone: str = "-") -> int:
    """Tizimda bo'lmagan ('boshqa usta') uchun yozuv. Bir xil ism bo'lsa qayta ishlatadi
    (qarz bitta odam ostida yig'ilishi uchun). Telegram ID manfiy (sun'iy) beriladi."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id FROM users WHERE telegram_id < 1 AND full_name = ? COLLATE NOCASE",
            (full_name,)
        )
        row = await cur.fetchone()
        if row:
            return row["id"]
        cur = await db.execute("SELECT COALESCE(MIN(telegram_id), 0) AS mn FROM users")
        mn = (await cur.fetchone())["mn"]
        new_tg = mn - 1 if mn < 0 else -1
        cur = await db.execute(
            """INSERT INTO users (telegram_id, full_name, phone, username, is_approved, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (new_tg, full_name, phone, None, uz_now_str())
        )
        await db.commit()
        return cur.lastrowid


async def get_sellable_users() -> list:
    """Tezkor sotuvda tanlash uchun: bot orqali ro'yxatdan o'tgan, tasdiqlangan ustalar."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE is_approved = 1 AND is_blocked = 0 AND telegram_id > 1 "
            "ORDER BY full_name"
        )
        return [dict(r) for r in await cur.fetchall()]


async def add_manual_sale(product_id: int, quantity: int, user_id: int,
                          payment_status: str = "paid", paid_amount: float = None) -> dict:
    """Admin qo'lda sotuvni qayd etadi: skladdan ayiradi + hisobotga yozadi.
    payment_status: 'paid' (to'liq) | 'debt' (qarz) | 'partial' (qisman).
    Qaytaradi: {'order_id','total','profit','remaining','debt'} yoki {'error':...}"""
    product = await get_product(product_id)
    if not product:
        return {"error": "topilmadi"}
    if product["quantity"] < quantity:
        return {"error": "stock", "available": product["quantity"]}

    total = float(product["price"]) * quantity
    cost = float(product["cost_price"]) * quantity

    if payment_status == "paid":
        paid_amount = total
    elif payment_status == "debt":
        paid_amount = 0
    else:  # partial
        paid_amount = max(0.0, min(float(paid_amount or 0), total))

    order_id = await add_order(
        user_id=user_id, product_id=product_id, quantity=quantity,
        total_price=total, cost_at_sale=cost,
        payment_method="naqd", pickup_type="shop",
        payment_status=payment_status, paid_amount=paid_amount,
    )
    # Qo'lda sotuv = mahsulot qo'lma-qo'l berildi => darhol yakunlangan (to'lov holatidan qat'i nazar).
    # Hisobotga kiradi; qarz/qisman bo'lsa qarz alohida kuzatiladi.
    await update_order_status(order_id, "yakunlandi")
    await update_product_quantity(product_id, product["quantity"] - quantity)

    return {
        "order_id": order_id,
        "total": total,
        "profit": total - cost,
        "remaining": product["quantity"] - quantity,
        "debt": total - paid_amount,
    }


# ============ QARZ FUNKSIYALARI ============

async def get_user_debts(user_id: int) -> list:
    """Foydalanuvchining qarzdor buyurtmalari"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, p.name as product_name,
                      c.name as category_name, c.icon as category_icon,
                      m.name as model_name, b.name as brand_name,
                      (o.total_price - o.paid_amount) as debt_amount
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.user_id = ?
                 AND o.payment_status IN ('debt', 'partial')
                 AND o.status != 'bekor'
               ORDER BY o.created_at DESC""",
            (user_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_user_total_debt(user_id: int) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """SELECT COALESCE(SUM(total_price - paid_amount), 0)
               FROM orders
               WHERE user_id = ?
                 AND payment_status IN ('debt', 'partial')
                 AND status != 'bekor'""",
            (user_id,)
        )
        row = await cursor.fetchone()
        return float(row[0]) if row else 0.0


async def get_all_debtors() -> list:
    """Hozir qarzi bor barcha ustalar (qarz miqdori bilan)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT u.*,
                      COALESCE(SUM(o.total_price - o.paid_amount), 0) as total_debt,
                      COUNT(o.id) as debt_orders_count
               FROM users u
               JOIN orders o ON o.user_id = u.id
               WHERE o.payment_status IN ('debt', 'partial') AND o.status != 'bekor'
               GROUP BY u.id
               HAVING total_debt > 0
               ORDER BY total_debt DESC"""
        )
        return [dict(row) for row in await cursor.fetchall()]


async def pay_order_debt(order_id: int, amount: float) -> dict:
    """Buyurtmaga to'lov qo'shish. Qaytaradi: yangi paid_amount va status."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT total_price, paid_amount FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            return {}
        total = float(row["total_price"])
        already = float(row["paid_amount"] or 0)
        new_paid = min(total, already + amount)
        new_status = "paid" if new_paid >= total - 0.01 else "partial"
        await db.execute(
            "UPDATE orders SET paid_amount = ?, payment_status = ? WHERE id = ?",
            (new_paid, new_status, order_id)
        )
        await db.commit()
        return {"paid_amount": new_paid, "payment_status": new_status, "total_price": total}


async def pay_user_full_debt(user_id: int) -> float:
    """Foydalanuvchining barcha qarzlarini to'liq to'langan qilib belgilash. Jami summani qaytaradi."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """SELECT COALESCE(SUM(total_price - paid_amount), 0)
               FROM orders
               WHERE user_id = ? AND payment_status IN ('debt', 'partial') AND status != 'bekor'""",
            (user_id,)
        )
        total = float((await cursor.fetchone())[0])
        await db.execute(
            """UPDATE orders SET paid_amount = total_price, payment_status = 'paid'
               WHERE user_id = ? AND payment_status IN ('debt', 'partial') AND status != 'bekor'""",
            (user_id,)
        )
        await db.commit()
        return total


# ============ STATISTIKA / HISOBOTLAR ============

async def get_statistics() -> dict:
    """Admin uchun umumiy statistika"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        stats = {}

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE telegram_id > 1")
        stats['total_users'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE is_approved = 1 AND telegram_id > 1"
        )
        stats['approved_users'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_approved = 0 AND is_blocked = 0")
        stats['pending_users'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM brands")
        stats['total_brands'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM models")
        stats['total_models'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM products")
        stats['total_products'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COALESCE(SUM(quantity), 0) as total FROM products")
        stats['total_stock'] = (await cursor.fetchone())['total']

        # Tugab qolayotganlar
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE quantity <= min_quantity"
        )
        stats['low_stock_count'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders")
        stats['total_orders'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'kutilmoqda'")
        stats['pending_orders'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'tasdiqlandi'")
        stats['confirmed_orders'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'yakunlandi'")
        stats['completed_orders'] = (await cursor.fetchone())['cnt']

        cursor = await db.execute(
            "SELECT COALESCE(SUM(total_price), 0) as total FROM orders WHERE status = 'yakunlandi'"
        )
        stats['total_revenue'] = (await cursor.fetchone())['total']

        # Umumiy qarz
        cursor = await db.execute(
            """SELECT COALESCE(SUM(total_price - paid_amount), 0) as debt
               FROM orders WHERE payment_status IN ('debt','partial') AND status != 'bekor'"""
        )
        stats['total_debt'] = (await cursor.fetchone())['debt']

        return stats


async def get_sales_summary(date_from: str, date_to: str) -> dict:
    """date_from / date_to formati: 'YYYY-MM-DD'. Tanlangan sana oralig'ida foyda/zarar."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # date_to ni inclusive qilish uchun 23:59 qo'shamiz (created_at TIMESTAMP)
        df = f"{date_from} 00:00:00"
        dt = f"{date_to} 23:59:59"

        cursor = await db.execute(
            """SELECT
                 COUNT(*) as orders_count,
                 COALESCE(SUM(quantity), 0) as units_sold,
                 COALESCE(SUM(total_price), 0) as revenue,
                 COALESCE(SUM(cost_at_sale), 0) as cost,
                 COALESCE(SUM(total_price - cost_at_sale), 0) as profit,
                 COALESCE(SUM(paid_amount), 0) as paid_received,
                 COALESCE(SUM(total_price - paid_amount), 0) as debt_added
               FROM orders
               WHERE created_at BETWEEN ? AND ? AND status = 'yakunlandi'""",
            (df, dt)
        )
        row = await cursor.fetchone()
        result = dict(row)
        result['date_from'] = date_from
        result['date_to'] = date_to
        result['margin_percent'] = (
            (result['profit'] / result['revenue'] * 100) if result['revenue'] > 0 else 0
        )
        return result


async def get_sales_by_category(date_from: str, date_to: str) -> list:
    """Sana oralig'ida kategoriya bo'yicha sotuv (Excel uchun)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        df = f"{date_from} 00:00:00"
        dt = f"{date_to} 23:59:59"
        cursor = await db.execute(
            """SELECT c.name as category_name, c.icon as category_icon,
                      COUNT(o.id) as orders_count,
                      COALESCE(SUM(o.quantity), 0) as units,
                      COALESCE(SUM(o.total_price), 0) as revenue,
                      COALESCE(SUM(o.cost_at_sale), 0) as cost,
                      COALESCE(SUM(o.total_price - o.cost_at_sale), 0) as profit
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE o.created_at BETWEEN ? AND ? AND o.status = 'yakunlandi'
               GROUP BY c.id
               ORDER BY revenue DESC""",
            (df, dt)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_sales_details(date_from: str, date_to: str) -> list:
    """Sana oralig'ida har bir buyurtma (Excel uchun)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        df = f"{date_from} 00:00:00"
        dt = f"{date_to} 23:59:59"
        cursor = await db.execute(
            """SELECT o.id, o.created_at, o.quantity, o.total_price, o.cost_at_sale,
                      (o.total_price - o.cost_at_sale) as profit,
                      o.payment_method, o.payment_status, o.paid_amount, o.status,
                      u.full_name as customer, u.phone as customer_phone,
                      p.name as product_name,
                      c.name as category_name,
                      m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN users u ON o.user_id = u.id
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN models m ON p.model_id = m.id
               LEFT JOIN brands b ON m.brand_id = b.id
               WHERE o.created_at BETWEEN ? AND ? AND o.status = 'yakunlandi'
               ORDER BY o.created_at""",
            (df, dt)
        )
        return [dict(row) for row in await cursor.fetchall()]
