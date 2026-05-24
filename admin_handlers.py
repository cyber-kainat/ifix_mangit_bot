"""
Admin paneli handlerlari
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.admin_kb import (
    get_admin_menu, get_products_menu,
    get_brands_admin_keyboard, get_models_admin_keyboard,
    get_screens_admin_keyboard, get_screen_edit_keyboard,
    get_users_management_keyboard, get_user_action_keyboard
)
from keyboards.user_kb import get_main_menu
from states import AdminStates
from config import config

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ============ ADMIN MENU ============

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Sizda admin huquqi yo'q.")
        return
    
    await state.clear()
    await message.answer(
        "👑 <b>Admin paneli</b>\n\nKerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


# ============ STATISTIKA ============

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = await db.get_statistics()
    
    text = (
        "📊 <b>Umumiy statistika</b>\n\n"
        f"👥 <b>Ustalar:</b>\n"
        f"  • Jami: {stats['total_users']}\n"
        f"  • Tasdiqlangan: {stats['approved_users']}\n"
        f"  • Kutilmoqda: {stats['pending_users']}\n\n"
        f"📦 <b>Mahsulotlar:</b>\n"
        f"  • Brendlar: {stats['total_brands']}\n"
        f"  • Modellar: {stats['total_models']}\n"
        f"  • Ekran turlari: {stats['total_screens']}\n"
        f"  • Omborda jami: {stats['total_stock']} dona\n\n"
        f"🛒 <b>Buyurtmalar:</b>\n"
        f"  • Jami: {stats['total_orders']}\n"
        f"  • ⏳ Kutilmoqda: {stats['pending_orders']}\n"
        f"  • ✅ Tasdiqlangan: {stats['confirmed_orders']}\n"
        f"  • 🎉 Yakunlangan: {stats['completed_orders']}\n\n"
        f"💰 <b>Sotuv: {int(stats['total_revenue']):,} so'm</b>"
    )
    await message.answer(text, parse_mode="HTML")


# ============ USTALARNI BOSHQARISH ============

@router.message(F.text == "👥 Ustalar")
async def manage_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    users = await db.get_all_users()
    if not users:
        await message.answer("📭 Hozircha ustalar yo'q.")
        return
    
    text = (
        f"👥 <b>Ustalar ro'yxati</b> ({len(users)} ta)\n\n"
        "✅ - tasdiqlangan | ⏳ - kutilmoqda | 🚫 - bloklangan\n\n"
        "Boshqarish uchun foydalanuvchini tanlang:"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_users_management_keyboard(users)
    )


@router.callback_query(F.data.startswith("manage_user_"))
async def manage_one_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    telegram_id = int(callback.data.split("_")[2])
    user = await db.get_user(telegram_id)
    
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    status = "✅ Tasdiqlangan" if user['is_approved'] else ("🚫 Bloklangan" if user['is_blocked'] else "⏳ Kutilmoqda")
    
    text = (
        f"👤 <b>Usta haqida ma'lumot:</b>\n\n"
        f"Ism: <b>{user['full_name']}</b>\n"
        f"📱 Telefon: <code>{user['phone']}</code>\n"
        f"🆔 TG ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Username: @{user['username'] or 'yoq'}\n"
        f"📊 Holat: {status}\n"
        f"📅 Ro'yxat: {user['created_at'][:16]}"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_user_action_keyboard(telegram_id, user['is_approved'], user['is_blocked'])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back_users")
async def back_to_users(callback: CallbackQuery):
    users = await db.get_all_users()
    text = (
        f"👥 <b>Ustalar ro'yxati</b> ({len(users)} ta)\n\n"
        "✅ - tasdiqlangan | ⏳ - kutilmoqda | 🚫 - bloklangan"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_users_management_keyboard(users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_user_cb(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    telegram_id = int(callback.data.split("_")[1])
    await db.approve_user(telegram_id)
    
    await callback.message.edit_text(
        callback.message.html_text + "\n\n✅ <b>Tasdiqlandi!</b>",
        parse_mode="HTML"
    )
    
    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            telegram_id,
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Sizning hisobingiz admin tomonidan tasdiqlandi.\n"
            "Endi xarid qila olasiz! /start tugmasini bosing.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.answer("✅ Foydalanuvchi tasdiqlandi")


@router.callback_query(F.data.startswith("reject_"))
async def reject_user_cb(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    telegram_id = int(callback.data.split("_")[1])
    await db.block_user(telegram_id)
    
    await callback.message.edit_text(
        callback.message.html_text + "\n\n🚫 <b>Bloklandi!</b>",
        parse_mode="HTML"
    )
    
    try:
        await bot.send_message(
            telegram_id,
            "🚫 Afsuski, sizning hisobingiz admin tomonidan bloklangan.\n"
            f"Aloqa: {config.SHOP_PHONE}"
        )
    except Exception:
        pass
    
    await callback.answer("🚫 Foydalanuvchi bloklandi")


# ============ MAHSULOTLARNI BOSHQARISH ============

@router.message(F.text == "📦 Mahsulotlar")
async def products_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📦 <b>Mahsulotlarni boshqarish:</b>",
        parse_mode="HTML",
        reply_markup=get_products_menu()
    )


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# === BREND QO'SHISH ===

@router.callback_query(F.data == "admin_add_brand")
async def add_brand_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_brand_name)
    await callback.message.edit_text(
        "📝 Yangi brend nomini kiriting (masalan: <b>iPhone</b>, <b>Samsung</b>):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_brand_name, F.text)
async def save_brand(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Brend nomi 2-50 ta belgi bo'lishi kerak.")
        return
    
    await db.add_brand(name)
    await state.clear()
    await message.answer(
        f"✅ Brend <b>{name}</b> qo'shildi!",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


# === MODEL QO'SHISH ===

@router.callback_query(F.data == "admin_add_model")
async def add_model_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("❌ Avval brend qo'shing!")
        await callback.answer()
        return
    
    await state.set_state(AdminStates.selecting_brand_for_model)
    await callback.message.edit_text(
        "📱 Qaysi brendga model qo'shasiz?",
        reply_markup=get_brands_admin_keyboard(brands, action="addmodel")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_brand_for_model, F.data.startswith("admin_addmodel_brand_"))
async def select_brand_for_model(callback: CallbackQuery, state: FSMContext):
    brand_id = int(callback.data.split("_")[3])
    brand = await db.get_brand(brand_id)
    
    await state.update_data(brand_id=brand_id)
    await state.set_state(AdminStates.waiting_model_name)
    
    await callback.message.edit_text(
        f"📱 Brend: <b>{brand['name']}</b>\n\n"
        f"Model nomini kiriting (masalan: <b>15 Pro Max</b>, <b>S24 Ultra</b>):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_model_name, F.text)
async def save_model(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await message.answer("❌ Model nomi 1-50 belgi bo'lishi kerak.")
        return
    
    data = await state.get_data()
    await db.add_model(data['brand_id'], name)
    brand = await db.get_brand(data['brand_id'])
    
    await state.clear()
    await message.answer(
        f"✅ <b>{brand['name']} {name}</b> qo'shildi!",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


# === EKRAN QO'SHISH ===

@router.callback_query(F.data == "admin_add_screen")
async def add_screen_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("❌ Avval brend qo'shing!")
        await callback.answer()
        return
    
    await state.set_state(AdminStates.selecting_brand_for_screen)
    await callback.message.edit_text(
        "📱 Qaysi brendga ekran qo'shasiz?",
        reply_markup=get_brands_admin_keyboard(brands, action="addscreenb")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_brand_for_screen, F.data.startswith("admin_addscreenb_brand_"))
async def select_brand_for_screen(callback: CallbackQuery, state: FSMContext):
    brand_id = int(callback.data.split("_")[3])
    models = await db.get_models(brand_id)
    
    if not models:
        await callback.message.edit_text("❌ Bu brendda hali model yo'q. Avval model qo'shing!")
        await state.clear()
        await callback.answer()
        return
    
    await state.set_state(AdminStates.selecting_model_for_screen)
    brand = await db.get_brand(brand_id)
    await callback.message.edit_text(
        f"📱 Brend: <b>{brand['name']}</b>\n\nQaysi modelga ekran qo'shasiz?",
        parse_mode="HTML",
        reply_markup=get_models_admin_keyboard(models, action="addscreenm")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_model_for_screen, F.data.startswith("admin_addscreenm_model_"))
async def select_model_for_screen(callback: CallbackQuery, state: FSMContext):
    model_id = int(callback.data.split("_")[3])
    model = await db.get_model(model_id)
    
    await state.update_data(model_id=model_id)
    await state.set_state(AdminStates.waiting_screen_type)
    
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\n"
        f"Ekran turini kiriting (masalan: <b>OLED</b>, <b>IPS</b>, <b>AMOLED</b>, <b>Super Retina XDR</b>):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_screen_type, F.text)
async def save_screen_type(message: Message, state: FSMContext):
    screen_type = message.text.strip()
    if len(screen_type) < 2 or len(screen_type) > 50:
        await message.answer("❌ Ekran turi 2-50 belgi bo'lishi kerak.")
        return
    
    await state.update_data(screen_type=screen_type)
    await state.set_state(AdminStates.waiting_screen_price)
    await message.answer(
        f"💰 Narxni so'mda kiriting (faqat raqam, masalan: <b>850000</b>):",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_screen_price, F.text)
async def save_screen_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Narx noto'g'ri. Faqat raqam kiriting:")
        return
    
    await state.update_data(price=price)
    await state.set_state(AdminStates.waiting_screen_quantity)
    await message.answer("📦 Necha dona mavjud? (raqam kiriting):")


@router.message(AdminStates.waiting_screen_quantity, F.text)
async def save_screen_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Miqdor noto'g'ri. Musbat raqam kiriting:")
        return
    
    await state.update_data(quantity=qty)
    await state.set_state(AdminStates.waiting_screen_description)
    await message.answer(
        "📝 Mahsulot tavsifi (ixtiyoriy). Tashlab ketish uchun <b>'-'</b> yuboring:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_screen_description, F.text)
async def save_screen_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    if len(desc) > 500:
        await message.answer("❌ Tavsif juda uzun. 500 belgidan kam bo'lsin:")
        return
    
    data = await state.get_data()
    await db.add_screen(
        model_id=data['model_id'],
        screen_type=data['screen_type'],
        price=data['price'],
        quantity=data['quantity'],
        description=desc
    )
    
    model = await db.get_model(data['model_id'])
    await state.clear()
    
    await message.answer(
        f"✅ <b>Ekran qo'shildi!</b>\n\n"
        f"📱 {model['brand_name']} {model['name']}\n"
        f"🔧 Turi: {data['screen_type']}\n"
        f"💰 Narxi: {int(data['price']):,} so'm\n"
        f"📦 Mavjud: {data['quantity']} dona",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


# === BRENDLAR RO'YXATI ===

@router.callback_query(F.data == "admin_list_brands")
async def list_brands(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("📭 Brendlar yo'q.")
        await callback.answer()
        return
    
    text = "📋 <b>Brendlar ro'yxati:</b>\n\n"
    for b in brands:
        models = await db.get_models(b['id'])
        text += f"📱 <b>{b['name']}</b> ({len(models)} ta model)\n"
        for m in models:
            screens = await db.get_screens(m['id'])
            text += f"   └ {m['name']} ({len(screens)} ta ekran)\n"
        text += "\n"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


# === NARX/MIQDORNI O'ZGARTIRISH ===

@router.callback_query(F.data == "admin_edit_screen")
async def edit_screen_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("❌ Avval brend qo'shing!")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📱 Brendni tanlang:",
        reply_markup=get_brands_admin_keyboard(brands, action="editb")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_editb_brand_"))
async def edit_select_brand(callback: CallbackQuery):
    brand_id = int(callback.data.split("_")[3])
    models = await db.get_models(brand_id)
    
    if not models:
        await callback.message.edit_text("❌ Bu brendda model yo'q!")
        await callback.answer()
        return
    
    brand = await db.get_brand(brand_id)
    await callback.message.edit_text(
        f"📱 <b>{brand['name']}</b>\n\nModelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_admin_keyboard(models, action="editm")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_editm_model_"))
async def edit_select_model(callback: CallbackQuery):
    model_id = int(callback.data.split("_")[3])
    screens = await db.get_screens(model_id)
    
    if not screens:
        await callback.message.edit_text("❌ Bu modelda ekran yo'q!")
        await callback.answer()
        return
    
    model = await db.get_model(model_id)
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\nEkranni tanlang:",
        parse_mode="HTML",
        reply_markup=get_screens_admin_keyboard(screens, action="edits")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edits_screen_"))
async def edit_select_screen(callback: CallbackQuery):
    screen_id = int(callback.data.split("_")[3])
    screen = await db.get_screen(screen_id)
    
    text = (
        f"📱 <b>{screen['brand_name']} {screen['model_name']}</b>\n"
        f"🔧 Tur: <b>{screen['screen_type']}</b>\n"
        f"💰 Narx: <b>{int(screen['price']):,} so'm</b>\n"
        f"📦 Mavjud: <b>{screen['quantity']} dona</b>\n\n"
        f"Nimani o'zgartirmoqchisiz?"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_screen_edit_keyboard(screen_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_price_"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    screen_id = int(callback.data.split("_")[2])
    await state.update_data(screen_id=screen_id)
    await state.set_state(AdminStates.waiting_new_price)
    await callback.message.edit_text("💰 Yangi narxni kiriting (so'mda):")
    await callback.answer()


@router.message(AdminStates.waiting_new_price, F.text)
async def save_new_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Narx noto'g'ri:")
        return
    
    data = await state.get_data()
    await db.update_screen_price(data['screen_id'], price)
    await state.clear()
    await message.answer(
        f"✅ Yangi narx saqlandi: <b>{int(price):,} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_qty_start(callback: CallbackQuery, state: FSMContext):
    screen_id = int(callback.data.split("_")[2])
    await state.update_data(screen_id=screen_id)
    await state.set_state(AdminStates.waiting_new_quantity)
    await callback.message.edit_text("📦 Yangi miqdorni kiriting:")
    await callback.answer()


@router.message(AdminStates.waiting_new_quantity, F.text)
async def save_new_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Miqdor noto'g'ri:")
        return
    
    data = await state.get_data()
    await db.update_screen_quantity(data['screen_id'], qty)
    await state.clear()
    await message.answer(
        f"✅ Yangi miqdor saqlandi: <b>{qty} dona</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("delete_screen_"))
async def delete_screen_cb(callback: CallbackQuery):
    screen_id = int(callback.data.split("_")[2])
    await db.delete_screen(screen_id)
    await callback.message.edit_text("🗑 Ekran o'chirildi.")
    await callback.answer("O'chirildi!")


# ============ BUYURTMALARNI BOSHQARISH ============

@router.message(F.text == "🛍 Buyurtmalar")
async def show_orders(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    orders = await db.get_pending_orders()
    if not orders:
        await message.answer("📭 Kutilayotgan buyurtmalar yo'q.")
        return
    
    text = f"🛍 <b>Kutilayotgan buyurtmalar ({len(orders)} ta):</b>\n\n"
    payment_names = {"naqd": "💵 Naqd", "click": "💳 Click", "payme": "💳 Payme"}
    pickup_names = {"shop": "🏪 Do'kondan", "delivery": "🚚 Yetkazib berish"}
    
    for o in orders[:10]:
        text += (
            f"📦 <b>Buyurtma #{o['id']}</b>\n"
            f"👤 {o['full_name']} | {o['phone']}\n"
            f"📱 {o['brand_name']} {o['model_name']} - {o['screen_type']}\n"
            f"📦 {o['quantity']} dona | 💰 {int(o['total_price']):,} so'm\n"
            f"💳 {payment_names.get(o['payment_method'], o['payment_method'])} | "
            f"{pickup_names.get(o['pickup_type'], o['pickup_type'])}\n"
            f"📅 {o['created_at'][:16]}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("order_confirm_"))
async def confirm_order_admin(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return
    
    await db.update_order_status(order_id, "tasdiqlandi")
    
    await callback.message.edit_text(
        callback.message.html_text + "\n\n✅ <b>TASDIQLANDI</b>",
        parse_mode="HTML"
    )
    
    try:
        await bot.send_message(
            order['telegram_id'],
            f"✅ <b>Buyurtmangiz tasdiqlandi!</b>\n\n"
            f"🆔 #{order_id}\n"
            f"📱 {order['brand_name']} {order['model_name']}\n"
            f"💰 {int(order['total_price']):,} so'm\n\n"
            f"📞 Admin tez orada bog'lanadi: {config.SHOP_PHONE}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.answer("✅ Tasdiqlandi")


@router.callback_query(F.data.startswith("order_cancel_"))
async def cancel_order_admin(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        return
    
    await db.update_order_status(order_id, "bekor")
    
    # Mahsulotni omborga qaytarish
    screen = await db.get_screen(order['screen_id'])
    if screen:
        await db.update_screen_quantity(order['screen_id'], screen['quantity'] + order['quantity'])
    
    await callback.message.edit_text(
        callback.message.html_text + "\n\n❌ <b>BEKOR QILINDI</b>",
        parse_mode="HTML"
    )
    
    try:
        await bot.send_message(
            order['telegram_id'],
            f"❌ Buyurtmangiz <b>#{order_id}</b> bekor qilindi.\n"
            f"Aloqa: {config.SHOP_PHONE}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.answer("❌ Bekor qilindi")


@router.callback_query(F.data.startswith("order_complete_"))
async def complete_order_admin(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    await db.update_order_status(order_id, "yakunlandi")
    
    await callback.message.edit_text(
        callback.message.html_text + "\n\n🎉 <b>YAKUNLANDI</b>",
        parse_mode="HTML"
    )
    
    try:
        await bot.send_message(
            order['telegram_id'],
            f"🎉 Buyurtmangiz <b>#{order_id}</b> yakunlandi!\n"
            f"Bizdan xarid qilganingiz uchun rahmat! ❤️",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.answer("🎉 Yakunlandi")


# Asosiy menyuga qaytish
@router.message(F.text == "🔙 Asosiy menyuga")
async def admin_back(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user and user['is_approved']:
        await message.answer("Asosiy menyu:", reply_markup=get_main_menu())
    else:
        await message.answer("Salom!", reply_markup=get_main_menu())
