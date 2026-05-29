"""
Bot konfiguratsiyasi
"""
import os
from dataclasses import dataclass, field
from typing import List


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
