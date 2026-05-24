"""
Katalog ko'rish va buyurtma berish handlerlari
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user_kb import (
    get_brands_keyboard, get_models_keyboard, get_screens_keyboard,
    get_quantity_keyboard, get_payment_keyboard, get_pickup_keyboard,
    get_confirm_keyboard, get_main_menu
)
from keyboards.admin_kb import get_order_admin_keyboard
from states import OrderStates
from config import config

router = Router()


# ============ KATALOG ============

@router.message(F.text == "🛒 Katalog")
async def show_catalog(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Avval ro'yxatdan o'ting: /start")
        return
    
    if not user['is_approved']:
        await message.answer("⏳ Sizning hisobingiz hali tasdiqlanmagan.")
        return
    
    brands = await db.get_brands()
    if not brands:
        await message.answer("📭 Hozircha katalog bo'sh. Tez orada to'ldiriladi!")
        return
    
    await message.answer(
        "📱 <b>Telefon brendlarini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_brands_keyboard(brands)
    )


@router.callback_query(F.data.startswith("brand_"))
async def select_brand(callback: CallbackQuery):
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    
    if not brand:
        await callback.answer("Brend topilmadi!", show_alert=True)
        return
    
    models = await db.get_models(brand_id)
    if not models:
        await callback.answer("Bu brend uchun model yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📱 <b>{brand['name']}</b>\n\n"
        f"Modelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_keyboard(models, brand_id)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_brands")
async def back_to_brands(callback: CallbackQuery):
    brands = await db.get_brands()
    await callback.message.edit_text(
        "📱 <b>Telefon brendlarini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_brands_keyboard(brands)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("model_"))
async def select_model(callback: CallbackQuery):
    model_id = int(callback.data.split("_")[1])
    model = await db.get_model(model_id)
    
    if not model:
        await callback.answer("Model topilmadi!", show_alert=True)
        return
    
    screens = await db.get_screens(model_id)
    if not screens:
        await callback.answer("Bu model uchun ekran yo'q!", show_alert=True)
        return
    
    # screens ga model_id qo'shish (ortga qaytish uchun)
    for s in screens:
        s['model_id'] = model_id
    
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\n"
        f"Ekran turini tanlang:\n"
        f"✅ - mavjud  |  ❌ - tugagan",
        parse_mode="HTML",
        reply_markup=get_screens_keyboard(screens, model_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_models_"))
async def back_to_models(callback: CallbackQuery):
    model_id = int(callback.data.split("_")[3])
    model = await db.get_model(model_id)
    if not model:
        return
    
    models = await db.get_models(model['brand_id'])
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']}</b>\n\n"
        f"Modelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_keyboard(models, model['brand_id'])
    )
    await callback.answer()


# ============ BUYURTMA BERISH ============

@router.callback_query(F.data.startswith("screen_"))
async def select_screen(callback: CallbackQuery, state: FSMContext):
    screen_id = int(callback.data.split("_")[1])
    screen = await db.get_screen(screen_id)
    
    if not screen:
        await callback.answer("Ekran topilmadi!", show_alert=True)
        return
    
    if screen['quantity'] <= 0:
        await callback.answer("❌ Bu ekran hozircha mavjud emas!", show_alert=True)
        return
    
    text = (
        f"📱 <b>{screen['brand_name']} {screen['model_name']}</b>\n"
        f"🔧 Ekran turi: <b>{screen['screen_type']}</b>\n"
        f"💰 Narx: <b>{int(screen['price']):,} so'm</b>\n"
        f"📦 Mavjud: <b>{screen['quantity']} dona</b>\n"
    )
    if screen.get('description'):
        text += f"\n📝 {screen['description']}\n"
    
    text += "\n<b>Nechta olmoqchisiz?</b>"
    
    await state.set_state(OrderStates.selecting_quantity)
    await state.update_data(screen_id=screen_id, quantity=1)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_quantity_keyboard(screen_id, 1, screen['quantity'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_minus_"))
async def qty_minus(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    screen_id = int(parts[2])
    current = int(parts[3])
    
    if current <= 1:
        await callback.answer("Minimum 1 dona", show_alert=False)
        return
    
    new_qty = current - 1
    screen = await db.get_screen(screen_id)
    await state.update_data(quantity=new_qty)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_quantity_keyboard(screen_id, new_qty, screen['quantity'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_plus_"))
async def qty_plus(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    screen_id = int(parts[2])
    current = int(parts[3])
    max_qty = int(parts[4])
    
    if current >= max_qty:
        await callback.answer(f"Maksimum {max_qty} dona mavjud", show_alert=True)
        return
    
    new_qty = current + 1
    await state.update_data(quantity=new_qty)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_quantity_keyboard(screen_id, new_qty, max_qty)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_ok_"))
async def qty_confirmed(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    screen_id = int(parts[2])
    quantity = int(parts[3])
    
    screen = await db.get_screen(screen_id)
    total = screen['price'] * quantity
    
    await state.update_data(quantity=quantity, total=total)
    await state.set_state(OrderStates.selecting_payment)
    
    await callback.message.edit_text(
        f"💳 <b>To'lov usulini tanlang:</b>\n\n"
        f"📱 {screen['brand_name']} {screen['model_name']}\n"
        f"🔧 {screen['screen_type']}\n"
        f"📦 {quantity} dona\n"
        f"💰 Jami: <b>{int(total):,} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_payment_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"), OrderStates.selecting_payment)
async def select_payment(callback: CallbackQuery, state: FSMContext):
    payment = callback.data.replace("pay_", "")
    payment_names = {"naqd": "💵 Naqd", "click": "💳 Click", "payme": "💳 Payme"}
    
    await state.update_data(payment_method=payment)
    await state.set_state(OrderStates.selecting_pickup)
    
    data = await state.get_data()
    screen = await db.get_screen(data['screen_id'])
    
    await callback.message.edit_text(
        f"🚚 <b>Olib ketish usulini tanlang:</b>\n\n"
        f"📱 {screen['brand_name']} {screen['model_name']}\n"
        f"🔧 {screen['screen_type']}\n"
        f"📦 {data['quantity']} dona\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: {payment_names[payment]}",
        parse_mode="HTML",
        reply_markup=get_pickup_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_"), OrderStates.selecting_pickup)
async def select_pickup(callback: CallbackQuery, state: FSMContext):
    pickup = callback.data.replace("pickup_", "")
    pickup_names = {"shop": "🏪 Do'kondan olib ketish", "delivery": "🚚 Yetkazib berish"}
    
    await state.update_data(pickup_type=pickup)
    await state.set_state(OrderStates.confirming)
    
    data = await state.get_data()
    screen = await db.get_screen(data['screen_id'])
    payment_names = {"naqd": "💵 Naqd", "click": "💳 Click", "payme": "💳 Payme"}
    
    text = (
        f"📋 <b>Buyurtmangizni tasdiqlang:</b>\n\n"
        f"📱 Mahsulot: <b>{screen['brand_name']} {screen['model_name']}</b>\n"
        f"🔧 Ekran turi: <b>{screen['screen_type']}</b>\n"
        f"📦 Miqdor: <b>{data['quantity']} dona</b>\n"
        f"💰 Bitta narxi: {int(screen['price']):,} so'm\n"
        f"💰 <b>Jami: {int(data['total']):,} so'm</b>\n\n"
        f"💳 To'lov: <b>{payment_names[data['payment_method']]}</b>\n"
        f"🚚 Olib ketish: <b>{pickup_names[pickup]}</b>\n"
    )
    
    # To'lov tafsilotlari
    if data['payment_method'] == "click":
        text += f"\n💳 Click karta: <code>{config.CLICK_CARD}</code>\n👤 Egasi: {config.CLICK_OWNER}"
    elif data['payment_method'] == "payme":
        text += f"\n💳 Payme karta: <code>{config.PAYME_CARD}</code>\n👤 Egasi: {config.PAYME_OWNER}"
    elif data['payment_method'] == "naqd" and pickup == "shop":
        text += f"\n🏪 Manzil: {config.SHOP_ADDRESS}"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_order", OrderStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    screen = await db.get_screen(data['screen_id'])
    
    # Yana bir bor mavjudlikni tekshirish
    if screen['quantity'] < data['quantity']:
        await callback.message.edit_text(
            "❌ Afsuski, bu mahsulot endi yetarli emas. Iltimos, qaytadan urinib ko'ring."
        )
        await state.clear()
        return
    
    # Buyurtmani saqlash
    order_id = await db.add_order(
        user_id=user['id'],
        screen_id=data['screen_id'],
        quantity=data['quantity'],
        total_price=data['total'],
        payment_method=data['payment_method'],
        pickup_type=data['pickup_type']
    )
    
    # Omborxonadan ayirish
    await db.update_screen_quantity(data['screen_id'], screen['quantity'] - data['quantity'])
    
    payment_names = {"naqd": "💵 Naqd", "click": "💳 Click", "payme": "💳 Payme"}
    pickup_names = {"shop": "🏪 Do'kondan olib ketish", "delivery": "🚚 Yetkazib berish"}
    
    await callback.message.edit_text(
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma raqami: <b>#{order_id}</b>\n"
        f"📱 {screen['brand_name']} {screen['model_name']}\n"
        f"🔧 {screen['screen_type']}\n"
        f"📦 {data['quantity']} dona\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: {payment_names[data['payment_method']]}\n"
        f"🚚 {pickup_names[data['pickup_type']]}\n\n"
        f"📞 Admin tez orada siz bilan bog'lanadi.\n"
        f"Aloqa: {config.SHOP_PHONE}",
        parse_mode="HTML"
    )
    
    # Adminlarga xabar yuborish
    admin_text = (
        f"🆕 <b>Yangi buyurtma! #{order_id}</b>\n\n"
        f"👤 Mijoz: <b>{user['full_name']}</b>\n"
        f"📱 Telefon: <code>{user['phone']}</code>\n"
        f"🆔 TG: <code>{user['telegram_id']}</code>\n\n"
        f"📱 Mahsulot: <b>{screen['brand_name']} {screen['model_name']}</b>\n"
        f"🔧 Tur: <b>{screen['screen_type']}</b>\n"
        f"📦 Miqdor: <b>{data['quantity']} dona</b>\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n\n"
        f"💳 To'lov: <b>{payment_names[data['payment_method']]}</b>\n"
        f"🚚 Olish: <b>{pickup_names[data['pickup_type']]}</b>"
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML",
                reply_markup=get_order_admin_keyboard(order_id)
            )
        except Exception as e:
            print(f"Admin xato: {e}")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await callback.message.answer("Asosiy menyu:", reply_markup=get_main_menu())
    await callback.answer()


# ============ BUYURTMALAR TARIXI ============

@router.message(F.text == "📋 Buyurtmalarim")
async def my_orders(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return
    
    orders = await db.get_user_orders(user['id'])
    if not orders:
        await message.answer("📭 Sizda hali buyurtmalar yo'q.")
        return
    
    status_emoji = {
        "kutilmoqda": "⏳",
        "tasdiqlandi": "✅",
        "yakunlandi": "🎉",
        "bekor": "❌"
    }
    
    text = "📋 <b>Sizning buyurtmalaringiz:</b>\n\n"
    for o in orders[:10]:
        emoji = status_emoji.get(o['status'], "📦")
        text += (
            f"{emoji} <b>#{o['id']}</b> - {o['status']}\n"
            f"   📱 {o['brand_name']} {o['model_name']} ({o['screen_type']})\n"
            f"   📦 {o['quantity']} dona | 💰 {int(o['total_price']):,} so'm\n"
            f"   📅 {o['created_at'][:16]}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
