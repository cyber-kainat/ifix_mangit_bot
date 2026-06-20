"""
Bot konfiguratsiyasi
"""
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List


# O'zbekiston vaqti (UTC+5, yozgi vaqt yo'q — doimiy).
# Railway serveri UTC da ishlaydi, shuning uchun barcha vaqtni shu funksiya orqali olamiz.
UZ_TZ = timezone(timedelta(hours=5))


def uz_now() -> datetime:
    """O'zbekiston (Toshkent) vaqti bo'yicha hozirgi datetime."""
    return datetime.now(UZ_TZ)


def uz_now_str() -> str:
    """SQLite created_at uchun 'YYYY-MM-DD HH:MM:SS' formatdagi O'zbekiston vaqti."""
    return uz_now().strftime("%Y-%m-%d %H:%M:%S")


def _admin_ids_from_env() -> List[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


@dataclass
class Config:
    # MAXFIY: bot tokeni endi faqat env (Railway -> Variables) dan o'qiladi.
    # Kodda token saqlamaymiz (ochiq GitHub'ga tushib ketmasligi uchun).
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Admin Telegram ID raqamlari — env: "id1,id2,id3"
    ADMIN_IDS: List[int] = field(default_factory=_admin_ids_from_env)

    # Ma'lumotlar bazasi yo'li (Railway Volume uchun env orqali "/data/shop.db")
    DB_NAME: str = os.getenv("DB_NAME", "shop.db")

    # To'lov kartasi (plastik to'lov uchun) — env'dan
    CARD_NUMBER: str = os.getenv("CARD_NUMBER", "")
    CARD_OWNER: str = os.getenv("CARD_OWNER", "")

    # Do'kon ma'lumotlari (maxfiy emas — standart qiymat qoldirildi)
    SHOP_ADDRESS: str = os.getenv(
        "SHOP_ADDRESS", "Mangit shahri bozori, Orientr Xalq banki ro'parasi")
    SHOP_PHONE: str = os.getenv("SHOP_PHONE", "+998 93 353 07 23")
    SHOP_HOURS: str = os.getenv("SHOP_HOURS", "09:00 - 20:00 (Har kuni)")


config = Config()
