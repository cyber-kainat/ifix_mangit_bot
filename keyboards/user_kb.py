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
            [KeyboardButton(text="ℹ️ Ma'lumot"), KeyboardButton(text="📞 Aloqa")]
        ],
        resize_keyboard=True
    )


def get_brands_keyboard(brands: list) -> InlineKeyboardMarkup:
    """Brendlar ro'yxati"""
    buttons = []
    # Brendlarni 2 ta qatorga joylash
    row = []
    for brand in brands:
        row.append(InlineKeyboardButton(
            text=f"📱 {brand['name']}",
            callback_data=f"brand_{brand['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_models_keyboard(models: list, brand_id: int) -> InlineKeyboardMarkup:
    """Modellar ro'yxati"""
    buttons = []
    row = []
    for model in models:
        row.append(InlineKeyboardButton(
            text=model['name'],
            callback_data=f"model_{model['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_to_brands")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_screens_keyboard(screens: list, model_id: int) -> InlineKeyboardMarkup:
    """Ekran turlari ro'yxati"""
    buttons = []
    for screen in screens:
        stock_emoji = "✅" if screen['quantity'] > 0 else "❌"
        text = f"{stock_emoji} {screen['screen_type']} - {int(screen['price']):,} so'm"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"screen_{screen['id']}"
        )])
    
    model = screens[0] if screens else None
    if model:
        buttons.append([InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"back_to_models_{model.get('model_id', 0)}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quantity_keyboard(screen_id: int, current: int = 1, max_qty: int = 1) -> InlineKeyboardMarkup:
    """Miqdor tanlash"""
    row1 = [
        InlineKeyboardButton(text="➖", callback_data=f"qty_minus_{screen_id}_{current}"),
        InlineKeyboardButton(text=f"{current} dona", callback_data="ignore"),
        InlineKeyboardButton(text="➕", callback_data=f"qty_plus_{screen_id}_{current}_{max_qty}")
    ]
    row2 = [
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"qty_ok_{screen_id}_{current}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order")
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def get_payment_keyboard() -> InlineKeyboardMarkup:
    """To'lov usulini tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Naqd pul", callback_data="pay_naqd")],
        [InlineKeyboardButton(text="💳 Click", callback_data="pay_click")],
        [InlineKeyboardButton(text="💳 Payme", callback_data="pay_payme")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])


def get_pickup_keyboard() -> InlineKeyboardMarkup:
    """Olib ketish usulini tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Do'kondan olib ketaman", callback_data="pickup_shop")],
        [InlineKeyboardButton(text="🚚 Yetkazib berish kerak", callback_data="pickup_delivery")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order")]
    ])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Buyurtmani tasdiqlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])
