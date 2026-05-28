"""
Katalog ko'rish va buyurtma berish handlerlari
Yangilangan: kategoriya tanlash + qarz/qisman to'lov
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user_kb import (
    get_categories_keyboard, get_brands_keyboard, get_models_keyboard,
    get_products_keyboard, get_quantity_keyboard, get_payment_keyboard,
    get_pickup_keyboard, get_payment_status_keyboard, get_confirm_keyboard,
    get_main_menu
)
from keyboards.admin_kb import get_order_admin_keyboard
from states import OrderStates
from config import config

router = Router()


PAYMENT_NAMES = {"naqd": "💵 Naqd", "click": "💳 Click", "payme": "💳 Payme"}
PICKUP_NAMES = {"shop": "🏪 Do'kondan olib ketish", "delivery": "🚚 Yetkazib berish"}
PSTATUS_NAMES = {
    "paid": "✅ To'liq to'lov",
    "debt": "📒 Qarz",
    "partial": "💰 Qisman to'lov"
}


# ============ 1. KATEGORIYA TANLASH ============

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

    categories = await db.get_categories()
    if not categories:
        await message.answer("📭 Hozircha katalog bo'sh.")
        return

    await state.set_state(OrderStates.selecting_category)
    await message.answer(
        "📂 <b>Mahsulot turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(categories)
    )


@router.callback_query(F.data.startswith("cat_"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    category = await db.get_category(category_id)
    if not category:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    await state.update_data(category_id=category_id)

    # Aksessuar singari brend/modelga bog'liq bo'lmagan kategoriyalar uchun
    if not category['requires_model']:
        products = await db.get_universal_products(category_id)
        if not products:
            await callback.answer(f"{category['name']} bo'limi hali bo'sh!", show_alert=True)
            return
        await state.set_state(OrderStates.selecting_product)
        await callback.message.edit_text(
            f"{category['icon']} <b>{category['name']}</b>\n\nMahsulotni tanlang:\n"
            f"✅ - mavjud  |  ❌ - tugagan",
            parse_mode="HTML",
            reply_markup=get_products_keyboard(products, model_id=None, category_id=category_id)
        )
        await callback.answer()
        return

    # Brend/modelga bog'liq kategoriyalar uchun
    brands = await db.get_brands_with_products(category_id)
    if not brands:
        await callback.answer(f"{category['name']} bo'limida hali mahsulot yo'q!", show_alert=True)
        return

    await state.set_state(OrderStates.selecting_brand)
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b>\n\nBrendni tanlang:",
        parse_mode="HTML",
        reply_markup=get_brands_keyboard(brands, category_id)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    categories = await db.get_categories()
    await state.set_state(OrderStates.selecting_category)
    await callback.message.edit_text(
        "📂 <b>Mahsulot turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(categories)
    )
    await callback.answer()


# ============ 2. BREND → MODEL → MAHSULOT ============

@router.callback_query(F.data.startswith("brand_"))
async def select_brand(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category_id = int(parts[1])
    brand_id = int(parts[2])

    category = await db.get_category(category_id)
    brand = await db.get_brand(brand_id)
    if not brand or not category:
        await callback.answer("Topilmadi!", show_alert=True)
        return

    models = await db.get_models_with_products(brand_id, category_id)
    if not models:
        await callback.answer("Bu brend uchun model yo'q!", show_alert=True)
        return

    await state.set_state(OrderStates.selecting_model)
    await state.update_data(brand_id=brand_id)
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b> — {brand['name']}\n\nModelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_keyboard(models, brand_id, category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_brands_"))
async def back_to_brands(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[3])
    category = await db.get_category(category_id)
    brands = await db.get_brands_with_products(category_id)
    await state.set_state(OrderStates.selecting_brand)
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b>\n\nBrendni tanlang:",
        parse_mode="HTML",
        reply_markup=get_brands_keyboard(brands, category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("model_"))
async def select_model(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category_id = int(parts[1])
    model_id = int(parts[2])

    model = await db.get_model(model_id)
    category = await db.get_category(category_id)
    if not model or not category:
        await callback.answer("Topilmadi!", show_alert=True)
        return

    products = await db.get_products_by_model(model_id, category_id)
    if not products:
        await callback.answer("Mahsulot yo'q!", show_alert=True)
        return

    await state.set_state(OrderStates.selecting_product)
    await state.update_data(model_id=model_id)

    await callback.message.edit_text(
        f"{category['icon']} <b>{model['brand_name']} {model['name']}</b>\n"
        f"Turi: {category['name']}\n\n"
        f"Mahsulotni tanlang:\n"
        f"✅ - mavjud  |  ❌ - tugagan",
        parse_mode="HTML",
        reply_markup=get_products_keyboard(products, model_id, category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_models_"))
async def back_to_models(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category_id = int(parts[3])
    model_id = int(parts[4])
    model = await db.get_model(model_id)
    if not model:
        return

    category = await db.get_category(category_id)
    models = await db.get_models_with_products(model['brand_id'], category_id)
    await state.set_state(OrderStates.selecting_model)
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b> — {model['brand_name']}\n\nModelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_keyboard(models, model['brand_id'], category_id)
    )
    await callback.answer()


# ============ 3. BUYURTMA BERISH ============

@router.callback_query(F.data.startswith("prod_"))
async def select_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("Mahsulot topilmadi!", show_alert=True)
        return

    if product['quantity'] <= 0:
        await callback.answer("❌ Bu mahsulot hozircha mavjud emas!", show_alert=True)
        return

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    text = (
        f"{product.get('category_icon', '📦')} <b>{title}</b>\n"
        f"💰 Narx: <b>{int(product['price']):,} so'm</b>\n"
        f"📦 Mavjud: <b>{product['quantity']} dona</b>\n"
    )
    if product.get('description'):
        text += f"\n📝 {product['description']}\n"

    text += "\n<b>Nechta olmoqchisiz?</b>"

    await state.set_state(OrderStates.selecting_quantity)
    await state.update_data(product_id=product_id, quantity=1)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_quantity_keyboard(product_id, 1, product['quantity'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_minus_"))
async def qty_minus(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id = int(parts[2])
    current = int(parts[3])

    if current <= 1:
        await callback.answer("Minimum 1 dona", show_alert=False)
        return

    new_qty = current - 1
    product = await db.get_product(product_id)
    await state.update_data(quantity=new_qty)

    await callback.message.edit_reply_markup(
        reply_markup=get_quantity_keyboard(product_id, new_qty, product['quantity'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_plus_"))
async def qty_plus(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id = int(parts[2])
    current = int(parts[3])
    max_qty = int(parts[4])

    if current >= max_qty:
        await callback.answer(f"Maksimum {max_qty} dona mavjud", show_alert=True)
        return

    new_qty = current + 1
    await state.update_data(quantity=new_qty)

    await callback.message.edit_reply_markup(
        reply_markup=get_quantity_keyboard(product_id, new_qty, max_qty)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty_ok_"))
async def qty_confirmed(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id = int(parts[2])
    quantity = int(parts[3])

    product = await db.get_product(product_id)
    total = product['price'] * quantity

    await state.update_data(quantity=quantity, total=total)
    await state.set_state(OrderStates.selecting_payment)

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    await callback.message.edit_text(
        f"💳 <b>To'lov usulini tanlang:</b>\n\n"
        f"{product.get('category_icon','📦')} {title}\n"
        f"📦 {quantity} dona\n"
        f"💰 Jami: <b>{int(total):,} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_payment_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"), OrderStates.selecting_payment)
async def select_payment(callback: CallbackQuery, state: FSMContext):
    payment = callback.data.replace("pay_", "")

    await state.update_data(payment_method=payment)
    await state.set_state(OrderStates.selecting_pickup)

    data = await state.get_data()
    product = await db.get_product(data['product_id'])

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    await callback.message.edit_text(
        f"🚚 <b>Olib ketish usulini tanlang:</b>\n\n"
        f"{product.get('category_icon','📦')} {title}\n"
        f"📦 {data['quantity']} dona\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: {PAYMENT_NAMES[payment]}",
        parse_mode="HTML",
        reply_markup=get_pickup_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pickup_"), OrderStates.selecting_pickup)
async def select_pickup(callback: CallbackQuery, state: FSMContext):
    pickup = callback.data.replace("pickup_", "")
    await state.update_data(pickup_type=pickup)
    await state.set_state(OrderStates.selecting_payment_status)

    data = await state.get_data()
    product = await db.get_product(data['product_id'])
    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    await callback.message.edit_text(
        f"💼 <b>To'lov holatini tanlang:</b>\n\n"
        f"{product.get('category_icon','📦')} {title}\n"
        f"📦 {data['quantity']} dona\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: {PAYMENT_NAMES[data['payment_method']]}\n"
        f"🚚 Olish: {PICKUP_NAMES[pickup]}\n\n"
        f"<i>To'liq — hozir to'lash\n"
        f"Qarz — keyinroq to'lash (admin tasdig'i bilan)\n"
        f"Qisman — bir qismini hozir to'lash</i>",
        parse_mode="HTML",
        reply_markup=get_payment_status_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pstatus_"), OrderStates.selecting_payment_status)
async def select_payment_status(callback: CallbackQuery, state: FSMContext):
    pstatus = callback.data.replace("pstatus_", "")
    data = await state.get_data()

    if pstatus == "partial":
        # Qisman summasini so'rash
        await state.set_state(OrderStates.waiting_partial_amount)
        await callback.message.edit_text(
            f"💰 Jami summa: <b>{int(data['total']):,} so'm</b>\n\n"
            f"Hozir qancha to'laysiz? (so'mda raqam kiriting)",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    paid_amount = data['total'] if pstatus == "paid" else 0
    await state.update_data(payment_status=pstatus, paid_amount=paid_amount)
    await _show_confirmation(callback, state)


@router.message(OrderStates.waiting_partial_amount, F.text)
async def process_partial_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(" ", "").replace(",", ""))
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa. Faqat raqam kiriting:")
        return

    data = await state.get_data()
    if amount >= data['total']:
        # To'liq to'lov bo'lib qoldi
        await state.update_data(payment_status="paid", paid_amount=data['total'])
    elif amount == 0:
        await state.update_data(payment_status="debt", paid_amount=0)
    else:
        await state.update_data(payment_status="partial", paid_amount=amount)

    await _show_confirmation_msg(message, state)


async def _show_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = await db.get_product(data['product_id'])

    text = _build_confirmation_text(product, data)
    await state.set_state(OrderStates.confirming)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())
    await callback.answer()


async def _show_confirmation_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    product = await db.get_product(data['product_id'])
    text = _build_confirmation_text(product, data)
    await state.set_state(OrderStates.confirming)
    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())


def _build_confirmation_text(product: dict, data: dict) -> str:
    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    debt = data['total'] - data.get('paid_amount', 0)
    text = (
        f"📋 <b>Buyurtmangizni tasdiqlang:</b>\n\n"
        f"{product.get('category_icon','📦')} <b>{title}</b>\n"
        f"📦 Miqdor: <b>{data['quantity']} dona</b>\n"
        f"💰 Bitta narxi: {int(product['price']):,} so'm\n"
        f"💰 <b>Jami: {int(data['total']):,} so'm</b>\n\n"
        f"💳 To'lov: <b>{PAYMENT_NAMES[data['payment_method']]}</b>\n"
        f"🚚 Olib ketish: <b>{PICKUP_NAMES[data['pickup_type']]}</b>\n"
        f"💼 To'lov holati: <b>{PSTATUS_NAMES[data['payment_status']]}</b>\n"
    )

    if data['payment_status'] == "partial":
        text += f"   • Hozir to'laysiz: {int(data['paid_amount']):,} so'm\n"
        text += f"   • Qarzga: {int(debt):,} so'm\n"
    elif data['payment_status'] == "debt":
        text += f"   • Qarz miqdori: {int(data['total']):,} so'm\n"

    # To'lov tafsilotlari (qarzga olganda bunday emas)
    if data['paid_amount'] > 0:
        if data['payment_method'] == "click":
            text += f"\n💳 Click karta: <code>{config.CLICK_CARD}</code>\n👤 Egasi: {config.CLICK_OWNER}"
        elif data['payment_method'] == "payme":
            text += f"\n💳 Payme karta: <code>{config.PAYME_CARD}</code>\n👤 Egasi: {config.PAYME_OWNER}"
        elif data['payment_method'] == "naqd" and data['pickup_type'] == "shop":
            text += f"\n🏪 Manzil: {config.SHOP_ADDRESS}"

    return text


@router.callback_query(F.data == "confirm_order", OrderStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    product = await db.get_product(data['product_id'])

    if product['quantity'] < data['quantity']:
        await callback.message.edit_text(
            "❌ Afsuski, bu mahsulot endi yetarli emas. Iltimos, qaytadan urinib ko'ring."
        )
        await state.clear()
        return

    cost_at_sale = float(product['cost_price']) * data['quantity']

    order_id = await db.add_order(
        user_id=user['id'],
        product_id=data['product_id'],
        quantity=data['quantity'],
        total_price=data['total'],
        cost_at_sale=cost_at_sale,
        payment_method=data['payment_method'],
        pickup_type=data['pickup_type'],
        payment_status=data['payment_status'],
        paid_amount=data.get('paid_amount', 0),
    )

    await db.update_product_quantity(data['product_id'], product['quantity'] - data['quantity'])

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    debt = data['total'] - data.get('paid_amount', 0)
    msg = (
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma raqami: <b>#{order_id}</b>\n"
        f"{product.get('category_icon','📦')} {title}\n"
        f"📦 {data['quantity']} dona\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: {PAYMENT_NAMES[data['payment_method']]} ({PSTATUS_NAMES[data['payment_status']]})\n"
        f"🚚 {PICKUP_NAMES[data['pickup_type']]}\n"
    )
    if debt > 0:
        msg += f"\n📒 <b>Qarz qoldi: {int(debt):,} so'm</b>\n"
    msg += f"\n📞 Admin tez orada siz bilan bog'lanadi.\nAloqa: {config.SHOP_PHONE}"

    await callback.message.edit_text(msg, parse_mode="HTML")

    # Adminlarga xabar
    admin_text = (
        f"🆕 <b>Yangi buyurtma! #{order_id}</b>\n\n"
        f"👤 Mijoz: <b>{user['full_name']}</b>\n"
        f"📱 Telefon: <code>{user['phone']}</code>\n"
        f"🆔 TG: <code>{user['telegram_id']}</code>\n\n"
        f"{product.get('category_icon','📦')} Mahsulot: <b>{title}</b>\n"
        f"📦 Miqdor: <b>{data['quantity']} dona</b>\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 To'lov: <b>{PAYMENT_NAMES[data['payment_method']]}</b> "
        f"({PSTATUS_NAMES[data['payment_status']]})\n"
        f"🚚 Olish: <b>{PICKUP_NAMES[data['pickup_type']]}</b>\n"
    )
    if debt > 0:
        admin_text += f"\n⚠️ <b>QARZ: {int(debt):,} so'm</b>"

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
    pstatus_emoji = {"paid": "✅", "debt": "📒", "partial": "💰"}

    text = "📋 <b>Sizning buyurtmalaringiz:</b>\n\n"
    for o in orders[:10]:
        emoji = status_emoji.get(o['status'], "📦")
        pemoji = pstatus_emoji.get(o.get('payment_status'), "")
        product_title = o.get('product_name', '?')
        if o.get('brand_name') and o.get('model_name'):
            product_title = f"{o['brand_name']} {o['model_name']} — {product_title}"
        cat = o.get('category_icon', '📦')
        debt = float(o['total_price']) - float(o.get('paid_amount', 0) or 0)
        text += (
            f"{emoji} <b>#{o['id']}</b> · {o['status']} {pemoji}\n"
            f"   {cat} {product_title}\n"
            f"   📦 {o['quantity']} dona | 💰 {int(o['total_price']):,} so'm\n"
        )
        if debt > 0:
            text += f"   📒 Qarz: <b>{int(debt):,} so'm</b>\n"
        text += f"   📅 {o['created_at'][:16]}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
