"""
Foydalanuvchi handlerlari - /start, ro'yxatdan o'tish, asosiy menyu
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user_kb import get_phone_keyboard, get_main_menu
from keyboards.admin_kb import get_approve_user_keyboard
from states import RegisterStates
from config import config

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if user is None:
        # Yangi foydalanuvchi - ro'yxatdan o'tishni so'rash
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "📱 <b>Telefon Ekranlari Do'koni</b> botiga xush kelibsiz!\n\n"
            "Bizdan mahsulot sotib olish uchun ro'yxatdan o'tishingiz kerak. "
            "Admin sizni tasdiqlagandan keyin xaridlarni amalga oshira olasiz.\n\n"
            "📝 Iltimos, <b>ism va familiyangizni</b> kiriting:",
            parse_mode="HTML"
        )
        await state.set_state(RegisterStates.waiting_for_name)
    
    elif user['is_blocked']:
        await message.answer(
            "🚫 Sizning hisobingiz bloklangan.\n"
            f"Aloqa uchun: {config.SHOP_PHONE}"
        )
    
    elif not user['is_approved']:
        await message.answer(
            "⏳ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
            "Sizning so'rovingiz admin tomonidan ko'rib chiqilmoqda. "
            "Tasdiqlangandan so'ng xabar olasiz.\n\n"
            f"Aloqa: {config.SHOP_PHONE}",
            parse_mode="HTML"
        )
    
    else:
        # Tasdiqlangan foydalanuvchi
        await message.answer(
            f"👋 Salom, <b>{user['full_name']}</b>!\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )


@router.message(RegisterStates.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Ism juda qisqa. Iltimos, to'liq ism-familiyangizni kiriting:")
        return
    
    if len(name) > 100:
        await message.answer("❌ Ism juda uzun. Qisqaroq kiriting:")
        return
    
    await state.update_data(full_name=name)
    await message.answer(
        f"✅ <b>{name}</b>\n\n"
        "📱 Endi telefon raqamingizni yuboring.\n"
        "Pastdagi tugmani bosishingiz mumkin:",
        parse_mode="HTML",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(RegisterStates.waiting_for_phone)


@router.message(RegisterStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext, bot):
    if message.contact.user_id != message.from_user.id:
        await message.answer("❌ Iltimos, o'zingizning telefon raqamingizni yuboring!")
        return
    
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    
    await finish_registration(message, state, phone, bot)


@router.message(RegisterStates.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext, bot):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    
    # Oddiy tekshiruv
    if not phone.startswith("+"):
        if phone.startswith("998"):
            phone = "+" + phone
        elif phone.startswith("8") and len(phone) == 9:
            phone = "+99" + phone
        else:
            await message.answer(
                "❌ Telefon raqami noto'g'ri. Misol: +998901234567\n"
                "Yoki pastdagi tugmani bosing 👇",
                reply_markup=get_phone_keyboard()
            )
            return
    
    if len(phone) < 12 or not phone[1:].isdigit():
        await message.answer("❌ Telefon raqami noto'g'ri. Qaytadan kiriting:")
        return
    
    await finish_registration(message, state, phone, bot)


async def finish_registration(message: Message, state: FSMContext, phone: str, bot):
    """Ro'yxatdan o'tishni yakunlash"""
    data = await state.get_data()
    full_name = data.get('full_name', 'Noma\'lum')
    
    await db.add_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        username=message.from_user.username
    )
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 Ism: <b>{full_name}</b>\n"
        f"📱 Telefon: <b>{phone}</b>\n\n"
        "⏳ Sizning so'rovingiz admin tomonidan ko'rib chiqilmoqda.\n"
        "Tasdiqlangandan keyin xabar yuboriladi va xarid qila olasiz.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Adminlarga xabar
    admin_text = (
        f"🆕 <b>Yangi usta ro'yxatdan o'tdi!</b>\n\n"
        f"👤 Ism: <b>{full_name}</b>\n"
        f"📱 Telefon: <code>{phone}</code>\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: @{message.from_user.username or 'yoq'}"
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML",
                reply_markup=get_approve_user_keyboard(message.from_user.id)
            )
        except Exception as e:
            print(f"Adminga xabar yuborishda xato: {e}")


@router.message(F.text == "ℹ️ Ma'lumot")
async def info_handler(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return
    
    await message.answer(
        "ℹ️ <b>Bot haqida</b>\n\n"
        "📱 Bu bot orqali telefon ekranlariga buyurtma berishingiz mumkin.\n\n"
        "🛒 <b>Katalog</b> - barcha mahsulotlarni ko'rish va buyurtma berish\n"
        "📋 <b>Buyurtmalarim</b> - o'zingizning buyurtmalaringiz tarixi\n"
        "📞 <b>Aloqa</b> - bog'lanish ma'lumotlari\n\n"
        "💳 To'lov: Naqd / Click / Payme\n"
        f"🏪 Manzil: {config.SHOP_ADDRESS}",
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return

    await message.answer(
        "📞 <b>Bog'lanish</b>\n\n"
        f"☎️ Telefon: {config.SHOP_PHONE}\n"
        f"📍 Manzil: {config.SHOP_ADDRESS}\n\n"
        "Ish vaqti: 09:00 - 19:00 (Dushanba-Shanba)",
        parse_mode="HTML"
    )


@router.message(F.text == "💳 Qarzlarim")
async def my_debts(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return

    total = await db.get_user_total_debt(user['id'])
    if total <= 0:
        await message.answer(
            "✅ <b>Sizda qarz yo'q!</b>\n\nBarcha buyurtmalaringiz to'liq to'langan.",
            parse_mode="HTML"
        )
        return

    debts = await db.get_user_debts(user['id'])
    text = (
        f"💳 <b>Sizning qarzlaringiz</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Jami qarz: {int(total):,} so'm</b>\n"
        f"Buyurtmalar soni: {len(debts)} ta\n\n"
    )
    for d in debts[:10]:
        product_title = d.get('product_name', '?')
        if d.get('brand_name') and d.get('model_name'):
            product_title = f"{d['brand_name']} {d['model_name']} — {product_title}"
        cat = d.get('category_icon', '📦')
        debt_amount = float(d['total_price']) - float(d.get('paid_amount', 0) or 0)
        text += (
            f"📦 <b>#{d['id']}</b>\n"
            f"   {cat} {product_title}\n"
            f"   Jami: {int(d['total_price']):,} so'm\n"
            f"   To'langan: {int(d.get('paid_amount', 0) or 0):,} so'm\n"
            f"   <b>Qarz: {int(debt_amount):,} so'm</b>\n"
            f"   📅 {d['created_at'][:16]}\n\n"
        )

    text += f"\n📞 To'lov uchun: {config.SHOP_PHONE}"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🔙 Asosiy menyuga")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user and user['is_approved']:
        await message.answer("Asosiy menyu:", reply_markup=get_main_menu())
