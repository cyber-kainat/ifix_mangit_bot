"""
Katalog, savat va buyurtma berish handlerlari
Yangilangan: savat (bir nechta mahsulot) + guruh buyurtma + qarz/qisman to'lov
"""
import uuid
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user_kb import (
    get_categories_keyboard, get_brands_keyboard, get_models_keyboard,
    get_products_keyboard, get_quantity_keyboard, get_payment_keyboard,
    get_pickup_keyboard, get_payment_status_keyboard, get_confirm_keyboard,
    get_main_menu, get_added_to_cart_kb, get_cart_kb
)
from keyboards.admin_kb import get_group_actions_kb
from states import OrderStates
from config import config

router = Router()


PAYMENT_NAMES = {"naqd": "💵 Naqd", "plastik": "💳 Plastik"}
PICKUP_NAMES = {"shop": "🏪 Do'kondan olib ketish", "delivery": "🚚 Yetkazib berish"}
PSTATUS_NAMES = {"paid": "✅ To'liq to'lov", "debt": "📒 Qarz", "partial": "💰 Qisman to'lov"}


def _cart_summary(cart: list):
    """Savatdagi mahsulotlar matni va umumiy summa."""
    lines = []
    total = 0
    for it in cart:
        sub = float(it["price"]) * it["quantity"]
        total += sub
        lines.append(
            f"{it.get('category_icon', '📦')} {it['title']} — "
            f"{it['quantity']} x {int(it['price']):,} = <b>{int(sub):,}</b>"
        )
    return "\n".join(lines), total


# ============ 1. KATEGORIYA TANLASH ============

@router.message(F.text == "🛒 Katalog")
async def show_catalog(message: Message, state: FSMContext):
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

    # Savatni saqlab qolamiz (navigatsiya davomida yo'qolmasin)
    data = await state.get_data()
    cart = data.get('cart', [])
    await state.clear()
    await state.update_data(cart=cart)
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


# ============ 3. MIQDOR TANLASH ============

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
        text, parse_mode="HTML",
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


# ============ 4. SAVAT ============

@router.callback_query(F.data.startswith("qty_ok_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id = int(parts[2])
    quantity = int(parts[3])

    product = await db.get_product(product_id)
    if not product or product['quantity'] <= 0:
        await callback.answer("Mahsulot mavjud emas", show_alert=True)
        return

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    data = await state.get_data()
    cart = data.get('cart', [])
    # Allaqachon savatda bo'lsa, miqdorni yangilaymiz
    for it in cart:
        if it['product_id'] == product_id:
            it['quantity'] = quantity
            break
    else:
        cart.append({
            'product_id': product_id,
            'title': title,
            'category_icon': product.get('category_icon', '📦'),
            'price': float(product['price']),
            'quantity': quantity,
        })

    await state.update_data(cart=cart)
    await state.set_state(None)
    await callback.message.edit_text(
        f"✅ <b>Savatga qo'shildi:</b>\n"
        f"{product.get('category_icon','📦')} {title} — {quantity} dona\n\n"
        f"🛒 Savatda: <b>{len(cart)} ta mahsulot</b>",
        parse_mode="HTML",
        reply_markup=get_added_to_cart_kb(len(cart))
    )
    await callback.answer("Savatga qo'shildi ✓")


@router.callback_query(F.data == "cart_add_more")
async def cart_add_more(callback: CallbackQuery, state: FSMContext):
    categories = await db.get_categories()
    await state.set_state(OrderStates.selecting_category)
    await callback.message.edit_text(
        "📂 <b>Mahsulot turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(categories)
    )
    await callback.answer()


async def _show_cart(target, state: FSMContext, edit: bool):
    data = await state.get_data()
    cart = data.get('cart', [])
    if not cart:
        txt = "🛒 Savat bo'sh.\n\n«🛒 Katalog» orqali mahsulot qo'shing."
        if edit:
            await target.edit_text(txt)
        else:
            await target.answer(txt)
        return
    summary, total = _cart_summary(cart)
    txt = (
        f"🛒 <b>Savat:</b>\n\n{summary}\n\n"
        f"💰 <b>Jami: {int(total):,} so'm</b>\n\n"
        f"Mahsulotni o'chirish uchun ❌ tugmasini bosing:"
    )
    if edit:
        await target.edit_text(txt, parse_mode="HTML", reply_markup=get_cart_kb(cart))
    else:
        await target.answer(txt, parse_mode="HTML", reply_markup=get_cart_kb(cart))


@router.callback_query(F.data == "cart_view")
async def cart_view_cb(callback: CallbackQuery, state: FSMContext):
    await _show_cart(callback.message, state, edit=True)
    await callback.answer()


@router.message(F.text == "🛒 Savatim")
async def cart_view_msg(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return
    await _show_cart(message, state, edit=False)


@router.callback_query(F.data.startswith("cartrm_"))
async def cart_remove(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.split("_")[1])
    data = await state.get_data()
    cart = [it for it in data.get('cart', []) if it['product_id'] != pid]
    await state.update_data(cart=cart)
    await _show_cart(callback.message, state, edit=True)
    await callback.answer("O'chirildi")


@router.callback_query(F.data == "cart_clear")
async def cart_clear(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[])
    await callback.message.edit_text("🗑 Savat tozalandi.")
    await callback.message.answer("Asosiy menyu:", reply_markup=get_main_menu())
    await callback.answer()


# ============ 5. CHECKOUT (to'lov → olish → holat → tasdiq) ============

@router.callback_query(F.data == "cart_checkout")
async def cart_checkout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    if not cart:
        await callback.answer("Savat bo'sh", show_alert=True)
        return
    summary, total = _cart_summary(cart)
    await state.update_data(total=total)
    await state.set_state(OrderStates.selecting_payment)
    await callback.message.edit_text(
        f"💳 <b>To'lov usulini tanlang:</b>\n\n{summary}\n\n💰 Jami: <b>{int(total):,} so'm</b>",
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
    await callback.message.edit_text(
        f"🚚 <b>Olib ketish usulini tanlang:</b>\n\n"
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
    await callback.message.edit_text(
        f"💼 <b>To'lov holatini tanlang:</b>\n\n"
        f"💰 Jami: <b>{int(data['total']):,} so'm</b>\n"
        f"💳 {PAYMENT_NAMES[data['payment_method']]}\n"
        f"🚚 {PICKUP_NAMES[pickup]}\n\n"
        f"<i>To'liq — hozir to'lash\nQarz — keyinroq\nQisman — bir qismini hozir</i>",
        parse_mode="HTML",
        reply_markup=get_payment_status_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pstatus_"), OrderStates.selecting_payment_status)
async def select_payment_status(callback: CallbackQuery, state: FSMContext):
    pstatus = callback.data.replace("pstatus_", "")
    data = await state.get_data()

    if pstatus == "partial":
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
    await _show_confirmation(callback.message, state, edit=True)
    await callback.answer()


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
        await state.update_data(payment_status="paid", paid_amount=data['total'])
    elif amount == 0:
        await state.update_data(payment_status="debt", paid_amount=0)
    else:
        await state.update_data(payment_status="partial", paid_amount=amount)

    await _show_confirmation(message, state, edit=False)


async def _show_confirmation(target, state: FSMContext, edit: bool):
    data = await state.get_data()
    cart = data.get('cart', [])
    summary, total = _cart_summary(cart)
    debt = total - data.get('paid_amount', 0)

    text = (
        f"📋 <b>Buyurtmangizni tasdiqlang:</b>\n\n{summary}\n\n"
        f"💰 <b>Jami: {int(total):,} so'm</b>\n\n"
        f"💳 To'lov: <b>{PAYMENT_NAMES[data['payment_method']]}</b>\n"
        f"🚚 Olib ketish: <b>{PICKUP_NAMES[data['pickup_type']]}</b>\n"
        f"💼 Holat: <b>{PSTATUS_NAMES[data['payment_status']]}</b>\n"
    )
    if data['payment_status'] == "partial":
        text += f"   • Hozir: {int(data['paid_amount']):,} so'm\n   • Qarzga: {int(debt):,} so'm\n"
    elif data['payment_status'] == "debt":
        text += f"   • Qarz: {int(total):,} so'm\n"

    if data.get('paid_amount', 0) > 0:
        if data['payment_method'] == "plastik":
            text += (
                f"\n💳 Karta: <code>{config.CARD_NUMBER}</code>\n"
                f"👤 Egasi: {config.CARD_OWNER}\n"
                f"🧾 Tasdiqlagach <b>chek rasmini</b> yuborasiz."
            )
        elif data['payment_method'] == "naqd" and data['pickup_type'] == "shop":
            text += f"\n🏪 Manzil: {config.SHOP_ADDRESS}"

    await state.set_state(OrderStates.confirming)
    if edit:
        await target.edit_text(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())


@router.callback_query(F.data == "confirm_order", OrderStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cart = data.get('cart', [])
    user = await db.get_user(callback.from_user.id)
    if not cart:
        await callback.answer("Savat bo'sh", show_alert=True)
        return

    # Mavjudlikni qayta tekshiramiz
    items = []
    for it in cart:
        p = await db.get_product(it['product_id'])
        if not p or p['quantity'] < it['quantity']:
            await callback.message.edit_text(
                f"❌ <b>{it['title']}</b> yetarli emas "
                f"(mavjud: {p['quantity'] if p else 0} dona).\n"
                f"Savatni tahrirlang.",
                parse_mode="HTML"
            )
            await state.set_state(None)
            await callback.answer()
            return
        items.append((p, it['quantity']))

    total = sum(float(p['price']) * q for p, q in items)
    pstatus = data['payment_status']
    paid_total = data.get('paid_amount', total if pstatus == "paid" else 0)

    group_id = uuid.uuid4().hex[:12]
    remaining = paid_total
    for p, q in items:
        sub = float(p['price']) * q
        cost = float(p['cost_price']) * q
        if pstatus == "paid":
            pa = sub
        elif pstatus == "debt":
            pa = 0
        else:
            pa = min(sub, remaining)
            remaining -= pa
        await db.add_order(
            user_id=user['id'], product_id=p['id'], quantity=q,
            total_price=sub, cost_at_sale=cost,
            payment_method=data['payment_method'], pickup_type=data['pickup_type'],
            payment_status=pstatus, paid_amount=pa, group_id=group_id
        )
        await db.update_product_quantity(p['id'], p['quantity'] - q)

    debt = total - paid_total
    needs_receipt = (data['payment_method'] == "plastik" and paid_total > 0)
    summary, _ = _cart_summary(cart)

    # Foydalanuvchiga
    msg = (
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n{summary}\n\n"
        f"💰 Jami: <b>{int(total):,} so'm</b>\n"
        f"💳 {PAYMENT_NAMES[data['payment_method']]} ({PSTATUS_NAMES[pstatus]})\n"
        f"🚚 {PICKUP_NAMES[data['pickup_type']]}\n"
    )
    if debt > 0:
        msg += f"\n📒 <b>Qarz qoldi: {int(debt):,} so'm</b>\n"
    if needs_receipt:
        msg += (
            f"\n💳 <b>Karta:</b> <code>{config.CARD_NUMBER}</code>\n👤 {config.CARD_OWNER}\n\n"
            f"🧾 <b>To'lab, chek rasmini shu yerga yuboring.</b>"
        )
    else:
        msg += f"\n📞 Admin tez orada bog'lanadi.\nAloqa: {config.SHOP_PHONE}"
    await callback.message.edit_text(msg, parse_mode="HTML")

    # Adminlarga (guruh + boshqaruv tugmalari)
    admin_text = (
        f"🆕 <b>Yangi buyurtma!</b>\n\n"
        f"👤 Mijoz: <b>{user['full_name']}</b>\n"
        f"📱 <code>{user['phone']}</code>\n"
        f"🆔 <code>{user['telegram_id']}</code>\n\n"
        f"{summary}\n\n"
        f"💰 Jami: <b>{int(total):,} so'm</b>\n"
        f"💳 <b>{PAYMENT_NAMES[data['payment_method']]}</b> ({PSTATUS_NAMES[pstatus]})\n"
        f"🚚 <b>{PICKUP_NAMES[data['pickup_type']]}</b>\n"
    )
    if debt > 0:
        admin_text += f"⚠️ <b>QARZ: {int(debt):,} so'm</b>\n"
    if needs_receipt:
        admin_text += "🧾 <i>Usta chek yuboradi (pastda).</i>\n"

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, admin_text, parse_mode="HTML",
                reply_markup=get_group_actions_kb(group_id)
            )
        except Exception as e:
            print(f"Admin xato: {e}")

    if needs_receipt:
        await state.set_state(OrderStates.waiting_receipt)
        await state.update_data(cart=[], receipt_group_id=group_id, receipt_summary=summary)
    else:
        await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    # Savatni saqlab, savat ko'rinishiga qaytamiz
    await state.set_state(None)
    data = await state.get_data()
    if data.get('cart'):
        await _show_cart(callback.message, state, edit=True)
    else:
        await callback.message.edit_text("❌ Bekor qilindi.")
        await callback.message.answer("Asosiy menyu:", reply_markup=get_main_menu())
    await callback.answer()


# ============ CHEK RASMI (plastik to'lov) ============

@router.message(OrderStates.waiting_receipt, F.photo)
async def receive_receipt_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    summary = data.get('receipt_summary', '')
    user = await db.get_user(message.from_user.id)
    file_id = message.photo[-1].file_id
    caption = (
        f"🧾 <b>To'lov cheki</b>\n\n"
        f"👤 {user['full_name'] if user else message.from_user.full_name}\n"
        f"📱 {user['phone'] if user else ''}\n\n{summary}\n\n"
        f"⬆️ Yuqoridagi buyurtmadan tasdiqlang."
    )
    sent = False
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, file_id, caption=caption, parse_mode="HTML")
            sent = True
        except Exception as e:
            print(f"Chek xato: {e}")
    await state.clear()
    await message.answer(
        "✅ <b>Chek qabul qilindi!</b>\n\nAdmin tekshirib, buyurtmangizni tasdiqlaydi.\n"
        f"📞 {config.SHOP_PHONE}" if sent else
        f"⚠️ Chek yuborishda muammo. Aloqa: {config.SHOP_PHONE}",
        parse_mode="HTML", reply_markup=get_main_menu()
    )


@router.message(OrderStates.waiting_receipt, F.document)
async def receive_receipt_doc(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    summary = data.get('receipt_summary', '')
    user = await db.get_user(message.from_user.id)
    caption = (
        f"🧾 <b>To'lov cheki</b>\n\n"
        f"👤 {user['full_name'] if user else message.from_user.full_name}\n"
        f"📱 {user['phone'] if user else ''}\n\n{summary}"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_document(admin_id, message.document.file_id, caption=caption, parse_mode="HTML")
        except Exception as e:
            print(f"Chek xato: {e}")
    await state.clear()
    await message.answer(
        "✅ <b>Chek qabul qilindi!</b>\n\nAdmin tekshirib, buyurtmani tasdiqlaydi.",
        parse_mode="HTML", reply_markup=get_main_menu()
    )


# ============ BUYURTMALAR TARIXI (guruhlangan) ============

@router.message(F.text == "📋 Buyurtmalarim")
async def my_orders(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user['is_approved']:
        return

    orders = await db.get_user_orders(user['id'], limit=60)
    if not orders:
        await message.answer("📭 Sizda hali buyurtmalar yo'q.")
        return

    status_emoji = {"kutilmoqda": "⏳", "tasdiqlandi": "✅", "yakunlandi": "🎉", "bekor": "❌"}
    pstatus_emoji = {"paid": "✅", "debt": "📒", "partial": "💰"}

    # group_id bo'yicha guruhlash
    groups = {}
    for o in orders:
        gid = o.get('group_id') or f"S{o['id']}"
        groups.setdefault(gid, []).append(o)

    text = "📋 <b>Sizning buyurtmalaringiz:</b>\n\n"
    for gid, rows in list(groups.items())[:10]:
        first = rows[0]
        emoji = status_emoji.get(first['status'], "📦")
        pemoji = pstatus_emoji.get(first.get('payment_status'), "")
        g_total = sum(float(r['total_price']) for r in rows)
        g_debt = sum(float(r['total_price']) - float(r.get('paid_amount', 0) or 0) for r in rows)
        text += f"{emoji} <b>Buyurtma</b> · {first['status']} {pemoji}\n"
        for r in rows:
            pt = r.get('product_name', '?')
            if r.get('brand_name') and r.get('model_name'):
                pt = f"{r['brand_name']} {r['model_name']} — {pt}"
            text += f"   {r.get('category_icon','📦')} {pt} × {r['quantity']}\n"
        text += f"   💰 Jami: {int(g_total):,} so'm\n"
        if g_debt > 0:
            text += f"   📒 Qarz: <b>{int(g_debt):,} so'm</b>\n"
        text += f"   📅 {first['created_at'][:16]}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
