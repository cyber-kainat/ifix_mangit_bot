"""
SQLite ma'lumotlar bazasi - barcha jadvallar va funksiyalar
"""
import aiosqlite
from datetime import datetime
from typing import Optional


DB_NAME = "shop.db"


async def init_db():
    """Bazani yaratish va boshlang'ich jadvallarni o'rnatish"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Foydalanuvchilar (ustalar) jadvali
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
        
        # Brendlar jadvali (iPhone, Samsung, Xiaomi...)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Modellar jadvali (iPhone 13, Galaxy S22...)
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
        
        # Ekranlar jadvali (Asosiy mahsulot - ekran turi va narxi)
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
        
        # Buyurtmalar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                screen_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                total_price REAL NOT NULL,
                payment_method TEXT NOT NULL,
                pickup_type TEXT NOT NULL,
                status TEXT DEFAULT 'kutilmoqda',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (screen_id) REFERENCES screens(id)
            )
        """)
        
        # Indekslar tezlik uchun
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_tg ON users(telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_brand ON models(brand_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_screens_model ON screens(model_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        
        await db.commit()


# ============ FOYDALANUVCHI FUNKSIYALARI ============

async def add_user(telegram_id: int, full_name: str, phone: str, username: str = None) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, full_name, phone, username) VALUES (?, ?, ?, ?)",
            (telegram_id, full_name, phone, username)
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


async def get_pending_users() -> list:
    """Tasdiqlanmagan ustalar"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_approved = 0 AND is_blocked = 0 ORDER BY created_at DESC"
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
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


# ============ BREND FUNKSIYALARI ============

async def add_brand(name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO brands (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


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


async def delete_brand(brand_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
        await db.commit()


# ============ MODEL FUNKSIYALARI ============

async def add_model(brand_id: int, name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO models (brand_id, name) VALUES (?, ?)",
            (brand_id, name)
        )
        await db.commit()
        return cursor.lastrowid


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


async def delete_model(model_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM models WHERE id = ?", (model_id,))
        await db.commit()


# ============ EKRAN FUNKSIYALARI ============

async def add_screen(model_id: int, screen_type: str, price: float, quantity: int = 0, description: str = "") -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO screens (model_id, screen_type, price, quantity, description) 
               VALUES (?, ?, ?, ?, ?)""",
            (model_id, screen_type, price, quantity, description)
        )
        await db.commit()
        return cursor.lastrowid


async def get_screens(model_id: int) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM screens WHERE model_id = ? ORDER BY screen_type", (model_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_screen(screen_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT s.*, m.name as model_name, b.name as brand_name 
               FROM screens s 
               JOIN models m ON s.model_id = m.id 
               JOIN brands b ON m.brand_id = b.id 
               WHERE s.id = ?""",
            (screen_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_screen_price(screen_id: int, price: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE screens SET price = ? WHERE id = ?", (price, screen_id)
        )
        await db.commit()


async def update_screen_quantity(screen_id: int, quantity: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE screens SET quantity = ? WHERE id = ?", (quantity, screen_id)
        )
        await db.commit()


async def delete_screen(screen_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM screens WHERE id = ?", (screen_id,))
        await db.commit()


# ============ BUYURTMA FUNKSIYALARI ============

async def add_order(user_id: int, screen_id: int, quantity: int, total_price: float, 
                    payment_method: str, pickup_type: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO orders (user_id, screen_id, quantity, total_price, payment_method, pickup_type) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, screen_id, quantity, total_price, payment_method, pickup_type)
        )
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, u.full_name, u.phone, u.telegram_id,
                      s.screen_type, s.price as unit_price,
                      m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN users u ON o.user_id = u.id
               JOIN screens s ON o.screen_id = s.id
               JOIN models m ON s.model_id = m.id
               JOIN brands b ON m.brand_id = b.id
               WHERE o.id = ?""",
            (order_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_orders(user_id: int, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, s.screen_type, m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN screens s ON o.screen_id = s.id
               JOIN models m ON s.model_id = m.id
               JOIN brands b ON m.brand_id = b.id
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
                      s.screen_type, m.name as model_name, b.name as brand_name
               FROM orders o
               JOIN users u ON o.user_id = u.id
               JOIN screens s ON o.screen_id = s.id
               JOIN models m ON s.model_id = m.id
               JOIN brands b ON m.brand_id = b.id
               WHERE o.status = 'kutilmoqda'
               ORDER BY o.created_at DESC"""
        )
        return [dict(row) for row in await cursor.fetchall()]


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
        await db.commit()


# ============ HISOBOT FUNKSIYALARI ============

async def get_statistics() -> dict:
    """Admin uchun umumiy statistika"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        stats = {}
        
        # Foydalanuvchilar
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
        stats['total_users'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_approved = 1")
        stats['approved_users'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_approved = 0 AND is_blocked = 0")
        stats['pending_users'] = (await cursor.fetchone())['cnt']
        
        # Mahsulotlar
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM brands")
        stats['total_brands'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM models")
        stats['total_models'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM screens")
        stats['total_screens'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COALESCE(SUM(quantity), 0) as total FROM screens")
        stats['total_stock'] = (await cursor.fetchone())['total']
        
        # Buyurtmalar
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders")
        stats['total_orders'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'kutilmoqda'")
        stats['pending_orders'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'tasdiqlandi'")
        stats['confirmed_orders'] = (await cursor.fetchone())['cnt']
        
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'yakunlandi'")
        stats['completed_orders'] = (await cursor.fetchone())['cnt']
        
        # Sotuv summasi (tasdiqlangan va yakunlangan)
        cursor = await db.execute(
            "SELECT COALESCE(SUM(total_price), 0) as total FROM orders WHERE status IN ('tasdiqlandi', 'yakunlandi')"
        )
        stats['total_revenue'] = (await cursor.fetchone())['total']
        
        return stats
