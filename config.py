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
    ADMIN_IDS: List[int] = field(default_factory=lambda: [5939503983, 813345127])
    
    # Ma'lumotlar bazasi nomi
    DB_NAME: str = "shop.db"
    
    # To'lov ma'lumotlari (Click va Payme uchun kartalar)
    CLICK_CARD: str = "8600 1234 5678 9012"
    CLICK_OWNER: str = "Aliyev Ali"
    PAYME_CARD: str = "8600 9876 5432 1098"
    PAYME_OWNER: str = "Aliyev Ali"
    
    # Do'kon manzili (naqd to'lov uchun)
    SHOP_ADDRESS: str = "Toshkent sh., Chilonzor tumani, 1-mavze"
    SHOP_PHONE: str = "+998 90 123 45 67"


config = Config()
