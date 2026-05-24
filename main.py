"""
Asosiy fayl - Botni ishga tushirish
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db
from handlers import user_handlers, catalog_handlers, admin_handlers


async def on_startup(bot: Bot):
    """Bot ishga tushganda chaqiriladi"""
    await init_db()
    print("✅ Ma'lumotlar bazasi tayyor!")
    
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
    
    # Token tekshiruvi
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ XATO: BOT_TOKEN o'rnatilmagan!")
        print("config.py ni oching va BOT_TOKEN ni @BotFather dan olingan token bilan to'ldiring.")
        return
    
    # Bot va dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Routerlarni ulash - tartibi muhim!
    # Admin handler birinchi (admin uchun maxsus tugmalar)
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
