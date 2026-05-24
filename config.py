"""
Bot konfiguratsiyasi
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # Bot token - Render environment variable dan olinadi
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Admin Telegram ID - vergul bilan ajratilgan
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "5939503983").split(",") if x.strip()
    ])
    
    DB_NAME: str = "shop.db"
    
    CLICK_CARD: str = "8600 1234 5678 9012"
    CLICK_OWNER: str = "Aliyev Ali"
    PAYME_CARD: str = "8600 9876 5432 1098"
    PAYME_OWNER: str = "Aliyev Ali"
    
    SHOP_ADDRESS: str = "Toshkent sh., Chilonzor tumani, 1-mavze"
    SHOP_PHONE: str = "+998 90 123 45 67"


config = Config()