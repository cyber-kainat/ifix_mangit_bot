"""
Foydalanuvchi (usta) uchun tugmalar
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamni so'rash uchun klaviatura"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_main_menu() -> ReplyKeyboardMarkup:
    """Asosiy menyu (tasdiqlangan ustalar uchun)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Katalog"), KeyboardButton(text="📋 Buyurtmalarim")],
            [KeyboardButton(text="💳 Qarzlarim"), KeyboardButton(text="📞 Aloqa")],
            [KeyboardButton(text="ℹ️ Ma'lumot")]
        ],
        resize_keyboard=True
    )


def get_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Mahsulot turlari (Ekran / Krishka / Batareya / Aksessuar...)"""
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            text=f"{cat['icon']} {cat['name']}",
            callback_data=f"cat_{cat['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_brands_keyboard(brands: list, category_id: int) -> InlineKeyboardMarkup:
    """Brendlar ro'yxati"""
    buttons = []
    row = []
    for brand in brands:
        row.append(InlineKeyboardButton(
            text=f"📱 {brand['name']}",
            callback_data=f"brand_{category_id}_{brand['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_models_keyboard(models: list, brand_id: int, category_id: int) -> InlineKeyboardMarkup:
    """Modellar ro'yxati"""
    buttons = []
    row = []
    for model in models:
        row.append(InlineKeyboardButton(
            text=model['name'],
            callback_data=f"model_{category_id}_{model['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="⬅️ Brendlar",
        callback_data=f"back_to_brands_{category_id}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_products_keyboard(products: list, model_id: int, category_id: int) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati (ekran/krishka/batareya turlari yoki aksessuarlar)"""
    buttons = []
    for p in products:
        stock_emoji = "✅" if p['quantity'] > 0 else "❌"
        text = f"{stock_emoji} {p['name']} - {int(p['price']):,} so'm"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"prod_{p['id']}"
        )])

    if model_id:
        buttons.append([InlineKeyboardButton(
            text="⬅️ Modellar",
            callback_data=f"back_to_models_{category_id}_{model_id}"
        )])
    else:
        # Aksessuarlar — to'g'ridan-to'g'ri kategoriyaga
        buttons.append([InlineKeyboardButton(
            text="⬅️ Kategoriyalar",
            callback_data="back_to_categories"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quantity_keyboard(product_id: int, current: int = 1, max_qty: int = 1) -> InlineKeyboardMarkup:
    """Miqdor tanlash"""
    row1 = [
        InlineKeyboardButton(text="➖", callback_data=f"qty_minus_{product_id}_{current}"),
        InlineKeyboardButton(text=f"{current} dona", callback_data="ignore"),
        InlineKeyboardButton(text="➕", callback_data=f"qty_plus_{product_id}_{current}_{max_qty}")
    ]
    row2 = [
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"qty_ok_{product_id}_{current}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order")
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def get_payment_keyboard() -> InlineKeyboardMarkup:
    """To'lov usulini tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Naqd", callback_data="pay_naqd")],
        [InlineKeyboardButton(text="💳 Plastik (karta)", callback_data="pay_plastik")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])


def get_pickup_keyboard() -> InlineKeyboardMarkup:
    """Olib ketish usulini tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Do'kondan olib ketaman", callback_data="pickup_shop")],
        [InlineKeyboardButton(text="🚚 Yetkazib berish kerak", callback_data="pickup_delivery")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order")]
    ])


def get_payment_status_keyboard() -> InlineKeyboardMarkup:
    """To'lov holati (to'liq / qarz / qisman)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'liq to'layman", callback_data="pstatus_paid")],
        [InlineKeyboardButton(text="📒 Qarzga olaman", callback_data="pstatus_debt")],
        [InlineKeyboardButton(text="💰 Qisman to'layman", callback_data="pstatus_partial")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order")]
    ])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Buyurtmani tasdiqlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])
