"""
Asosiy fayl - Botni ishga tushirish
"""
import asyncio
import logging
import os
import sys
import time

# Server vaqtini O'zbekiston (Toshkent, UTC+5) ga o'rnatamiz.
# Railway UTC da ishlaydi — bularsiz vaqt 5 soat kam ko'rsatardi.
os.environ["TZ"] = "Asia/Tashkent"
try:
    time.tzset()
except AttributeError:
    pass  # Windows tzset ni qo'llab-quvvatlamaydi

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, BotCommandScopeDefault,
                           BotCommandScopeChat)

from config import config
from database.db import init_db
from handlers import user_handlers, catalog_handlers, admin_handlers, photo_handlers


async def _set_commands(bot: Bot):
    """Telegram '/' menyusini sozlash.
    Oddiy mijozlarga faqat /start; admin buyruqlari faqat adminlarga ko'rinadi."""
    # Hammaga
    await bot.set_my_commands(
        [BotCommand(command="start", description="Boshlash / Ro'yxatdan o'tish")],
        scope=BotCommandScopeDefault(),
    )
    # Faqat adminlarga
    admin_cmds = [
        BotCommand(command="admin", description="🛠 Admin paneli"),
        BotCommand(command="rasm", description="🖼 Mahsulotga rasm qo'yish"),
        BotCommand(command="chegirma", description="💸 Chegirma qo'yish"),
        BotCommand(command="chegirma_ochir", description="❌ Chegirmani bekor qilish"),
        BotCommand(command="banner", description="📢 Banner qo'shish"),
        BotCommand(command="bannerlar", description="📋 Bannerlar ro'yxati"),
        BotCommand(command="banner_ochir", description="🗑 Bannerni o'chirish"),
        BotCommand(command="aloqa", description="📞 Aloqa telefonini o'zgartirish"),
        BotCommand(command="telegram", description="✈️ Telegram havolasini o'zgartirish"),
        BotCommand(command="instagram", description="📷 Instagram havolasini o'zgartirish"),
    ]
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.set_my_commands(
                admin_cmds, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"Admin {admin_id} buyruqlarini o'rnatib bo'lmadi: {e}")


async def on_startup(bot: Bot):
    """Bot ishga tushganda chaqiriladi"""
    await init_db()
    print("✅ Ma'lumotlar bazasi tayyor!")

    # '/' buyruq menyusini sozlash
    await _set_commands(bot)

    # Bir martalik: eski SQLite ma'lumotini Postgres'ga ko'chirish
    if os.getenv("RUN_MIGRATION") == "1":
        print("🔄 SQLite -> Postgres ko'chirish...")
        from database.migrate_pg import migrate
        await migrate()

    # Adminlarga xabar
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🤖 <b>Bot ishga tushdi!</b>\n\n"
                "Admin paneli: /admin"
            )
        except Exception as e:
            print(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")


async def main():
    # Logging sozlash
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Token tekshiruvi — endi env'dan keladi
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ XATO: BOT_TOKEN o'rnatilmagan!")
        print("Railway -> ifix_mangit_bot -> Variables ga BOT_TOKEN ni qo'ying.")
        return
    
    # Bot va dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Routerlarni ulash - tartibi muhim!
    # Admin handler birinchi (admin uchun maxsus tugmalar)
    dp.include_router(photo_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(catalog_handlers.router)
    dp.include_router(user_handlers.router)
    
    # Ishga tushish
    await on_startup(bot)
    
    print("🚀 Bot ishga tushdi! To'xtatish uchun Ctrl+C bosing.")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Bot to'xtatildi.")
