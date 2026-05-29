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


@dataclass
class Config:
    # Telegram bot tokeni - @BotFather dan oling
    BOT_TOKEN: str = "8000831961:AAFzlLk8EvaDUnXbLouLZ-9AFryk9CA5I5U"
    
    # Admin Telegram ID raqamlari (ro'yxat - bir nechta admin bo'lishi mumkin)
    # O'z ID raqamingizni @userinfobot dan oling
    ADMIN_IDS: List[int] = field(default_factory=lambda: [5939503983, 813345127, 8001740351])
    
    # Ma'lumotlar bazasi yo'li (Railway Volume uchun env orqali "/data/shop.db")
    DB_NAME: str = os.getenv("DB_NAME", "shop.db")
    
    # To'lov kartasi (plastik to'lov uchun yagona admin kartasi)
    CARD_NUMBER: str = "9860 3501 4277 2812"
    CARD_OWNER: str = "Hakimjon Otajonov"

    # Do'kon ma'lumotlari
    SHOP_ADDRESS: str = "Mangit shahri bozori, Orientr Xalq banki ro'parasi"
    SHOP_PHONE: str = "+998 93 353 07 23"
    SHOP_HOURS: str = "09:00 - 20:00 (Har kuni)"


config = Config()
