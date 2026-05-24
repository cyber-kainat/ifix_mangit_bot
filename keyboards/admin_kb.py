"""
Admin uchun tugmalar
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Admin asosiy menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Ustalar")],
            [KeyboardButton(text="📦 Mahsulotlar"), KeyboardButton(text="🛍 Buyurtmalar")],
            [KeyboardButton(text="🔙 Asosiy menyuga")]
        ],
        resize_keyboard=True
    )


def get_products_menu() -> InlineKeyboardMarkup:
    """Mahsulotlarni boshqarish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Brend qo'shish", callback_data="admin_add_brand")],
        [InlineKeyboardButton(text="➕ Model qo'shish", callback_data="admin_add_model")],
        [InlineKeyboardButton(text="➕ Ekran qo'shish", callback_data="admin_add_screen")],
        [InlineKeyboardButton(text="📋 Brendlar ro'yxati", callback_data="admin_list_brands")],
        [InlineKeyboardButton(text="✏️ Narx/miqdorni o'zgartirish", callback_data="admin_edit_screen")]
    ])


def get_brands_admin_keyboard(brands: list, action: str = "select") -> InlineKeyboardMarkup:
    """Adminga brendlar ro'yxati"""
    buttons = []
    for brand in brands:
        buttons.append([InlineKeyboardButton(
            text=f"📱 {brand['name']}",
            callback_data=f"admin_{action}_brand_{brand['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_models_admin_keyboard(models: list, action: str = "select") -> InlineKeyboardMarkup:
    """Adminga modellar ro'yxati"""
    buttons = []
    for model in models:
        buttons.append([InlineKeyboardButton(
            text=model['name'],
            callback_data=f"admin_{action}_model_{model['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_screens_admin_keyboard(screens: list, action: str = "edit") -> InlineKeyboardMarkup:
    """Adminga ekranlar ro'yxati"""
    buttons = []
    for screen in screens:
        text = f"{screen['screen_type']} - {int(screen['price']):,} so'm ({screen['quantity']} dona)"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"admin_{action}_screen_{screen['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_screen_edit_keyboard(screen_id: int) -> InlineKeyboardMarkup:
    """Ekranni tahrirlash menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"edit_price_{screen_id}")],
        [InlineKeyboardButton(text="📦 Miqdorni o'zgartirish", callback_data=f"edit_qty_{screen_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_screen_{screen_id}")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data="admin_cancel")]
    ])


def get_approve_user_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Foydalanuvchini tasdiqlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{telegram_id}"),
            InlineKeyboardButton(text="🚫 Rad etish", callback_data=f"reject_{telegram_id}")
        ]
    ])


def get_users_management_keyboard(users: list) -> InlineKeyboardMarkup:
    """Ustalarni boshqarish"""
    buttons = []
    for u in users[:20]:
        status = "✅" if u['is_approved'] else ("🚫" if u['is_blocked'] else "⏳")
        buttons.append([InlineKeyboardButton(
            text=f"{status} {u['full_name']} - {u['phone']}",
            callback_data=f"manage_user_{u['telegram_id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_action_keyboard(telegram_id: int, is_approved: bool, is_blocked: bool) -> InlineKeyboardMarkup:
    """Bitta foydalanuvchini boshqarish"""
    buttons = []
    if not is_approved:
        buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{telegram_id}")])
    if not is_blocked:
        buttons.append([InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"reject_{telegram_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="admin_back_users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Buyurtmani boshqarish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"order_confirm_{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"order_cancel_{order_id}")
        ],
        [InlineKeyboardButton(text="🎉 Yakunlangan", callback_data=f"order_complete_{order_id}")]
    ])
