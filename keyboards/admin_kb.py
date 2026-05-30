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
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="💰 Sotuv")],
            [KeyboardButton(text="🧾 Tezkor sotuv"), KeyboardButton(text="🛍 Buyurtmalar")],
            [KeyboardButton(text="👥 Ustalar"), KeyboardButton(text="💳 Qarzlar")],
            [KeyboardButton(text="📦 Mahsulotlar"), KeyboardButton(text="📉 Tugab qolganlar")],
            [KeyboardButton(text="💾 Backup"), KeyboardButton(text="♻️ Restore")],
            [KeyboardButton(text="🔙 Asosiy menyuga")]
        ],
        resize_keyboard=True
    )


def get_products_menu() -> InlineKeyboardMarkup:
    """Mahsulotlarni boshqarish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Brend qo'shish", callback_data="admin_add_brand")],
        [InlineKeyboardButton(text="➕ Model qo'shish", callback_data="admin_add_model")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="📦 Tovar qabul qilish (sklad+tannarx)", callback_data="admin_receive")],
        [InlineKeyboardButton(text="📋 Kelgan tovarlar tarixi", callback_data="admin_receipts")],
        [InlineKeyboardButton(text="📥 Excel'dan import", callback_data="admin_import")],
        [InlineKeyboardButton(text="✏️ Mahsulotni tahrirlash", callback_data="admin_edit_product")],
        [InlineKeyboardButton(text="🗂 Brend / Model boshqarish", callback_data="mng_brands")],
        [InlineKeyboardButton(text="📋 Brendlar ro'yxati", callback_data="admin_list_brands")]
    ])


# ============ TO'LIQ BOSHQARUV (brend/model o'chirish, nomini o'zgartirish) ============

def get_manage_brands_kb(brands: list) -> InlineKeyboardMarkup:
    """Barcha brendlar (boshqarish uchun)"""
    buttons = []
    for b in brands:
        buttons.append([InlineKeyboardButton(
            text=f"📱 {b['name']}", callback_data=f"mngb_{b['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_brand_manage_kb(brand_id: int) -> InlineKeyboardMarkup:
    """Bitta brend uchun amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Modellarini ko'rish", callback_data=f"mngml_{brand_id}")],
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"mngbren_{brand_id}")],
        [InlineKeyboardButton(text="🗑 Brendni o'chirish", callback_data=f"mngbdel_{brand_id}")],
        [InlineKeyboardButton(text="⬅️ Brendlar", callback_data="mng_brands")]
    ])


def get_brand_delete_confirm_kb(brand_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"mngbdy_{brand_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"mngb_{brand_id}")
        ]
    ])


def get_manage_models_kb(models: list, brand_id: int) -> InlineKeyboardMarkup:
    """Brendning barcha modellari (boshqarish uchun)"""
    buttons = []
    for m in models:
        buttons.append([InlineKeyboardButton(
            text=m['name'], callback_data=f"mngm_{m['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"mngb_{brand_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_model_manage_kb(model_id: int, brand_id: int) -> InlineKeyboardMarkup:
    """Bitta model uchun amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"mngmren_{model_id}")],
        [InlineKeyboardButton(text="🗑 Modelni o'chirish", callback_data=f"mngmdel_{model_id}")],
        [InlineKeyboardButton(text="⬅️ Modellar", callback_data=f"mngml_{brand_id}")]
    ])


def get_model_delete_confirm_kb(model_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"mngmdy_{model_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"mngm_{model_id}")
        ]
    ])


def get_categories_admin_keyboard(categories: list, action: str = "select") -> InlineKeyboardMarkup:
    """Adminga kategoriyalar ro'yxati"""
    buttons = []
    for c in categories:
        buttons.append([InlineKeyboardButton(
            text=f"{c['icon']} {c['name']}",
            callback_data=f"admin_{action}_cat_{c['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def get_products_admin_keyboard(products: list, action: str = "edit") -> InlineKeyboardMarkup:
    """Adminga mahsulotlar ro'yxati"""
    buttons = []
    for p in products:
        text = f"{p['name']} - {int(p['price']):,} so'm ({p['quantity']} dona)"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"admin_{action}_prod_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_edit_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Mahsulotni tahrirlash menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"edit_name_{product_id}")],
        [InlineKeyboardButton(text="💰 Sotish narxi", callback_data=f"edit_price_{product_id}")],
        [InlineKeyboardButton(text="🏷 Tannarx", callback_data=f"edit_cost_{product_id}")],
        [InlineKeyboardButton(text="📦 Miqdor", callback_data=f"edit_qty_{product_id}")],
        [InlineKeyboardButton(text="⚠️ Minimum miqdor", callback_data=f"edit_minqty_{product_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_prod_{product_id}")],
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


def get_user_action_keyboard(telegram_id: int, is_approved: bool, is_blocked: bool, has_debt: bool = False) -> InlineKeyboardMarkup:
    """Bitta foydalanuvchini boshqarish"""
    buttons = []
    if not is_approved:
        buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{telegram_id}")])
    if not is_blocked:
        buttons.append([InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"reject_{telegram_id}")])
    if has_debt:
        buttons.append([InlineKeyboardButton(text="💳 Qarzini ko'rish", callback_data=f"user_debts_{telegram_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="admin_back_users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


ORDER_STATUS_EMOJI = {"kutilmoqda": "⏳", "tasdiqlandi": "✅", "yakunlandi": "🎉", "bekor": "❌"}


def get_group_actions_kb(group_id: str, status: str = None, with_back: bool = False) -> InlineKeyboardMarkup:
    """Buyurtma guruhini boshqarish (yangi buyurtma xabarida va boshqaruvda)."""
    rows = []
    if status not in ("tasdiqlandi", "yakunlandi"):
        rows.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ordconf_{group_id}")])
    if status != "yakunlandi":
        rows.append([InlineKeyboardButton(text="🎉 Yakunlash (hisobotga)", callback_data=f"ordcomp_{group_id}")])
    rows.append([
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"ordcanc_{group_id}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"orddel_{group_id}")
    ])
    if with_back:
        rows.append([InlineKeyboardButton(text="⬅️ Ro'yxat", callback_data="ord_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_orders_filter_kb() -> InlineKeyboardMarkup:
    """Buyurtmalarni status bo'yicha filtr"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏳ Kutilmoqda", callback_data="ordlist_kutilmoqda"),
            InlineKeyboardButton(text="✅ Tasdiqlangan", callback_data="ordlist_tasdiqlandi")
        ],
        [
            InlineKeyboardButton(text="🎉 Yakunlangan", callback_data="ordlist_yakunlandi"),
            InlineKeyboardButton(text="❌ Bekor qilingan", callback_data="ordlist_bekor")
        ],
        [InlineKeyboardButton(text="📋 Hammasi", callback_data="ordlist_all")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")]
    ])


def get_order_groups_kb(groups: list) -> InlineKeyboardMarkup:
    """Buyurtma guruhlari ro'yxati"""
    buttons = []
    for g in groups[:25]:
        emoji = ORDER_STATUS_EMOJI.get(g['status'], "📦")
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {g['full_name']} · {int(g['total']):,} so'm ({g['items']} ta)",
            callback_data=f"ordgrp_{g['group_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Filtr", callback_data="ord_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_delete_confirm_kb(group_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"orddelyes_{group_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"ordgrp_{group_id}")
        ]
    ])


# ============ SOTUV / HISOBOT ============

def get_sales_period_keyboard() -> InlineKeyboardMarkup:
    """Sotuv hisoboti uchun sana oralig'i tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Bugun", callback_data="sales_today"),
            InlineKeyboardButton(text="📅 Kecha", callback_data="sales_yesterday")
        ],
        [
            InlineKeyboardButton(text="🗓 Bu hafta", callback_data="sales_week"),
            InlineKeyboardButton(text="🗓 Bu oy", callback_data="sales_month")
        ],
        [
            InlineKeyboardButton(text="📆 O'tgan oy", callback_data="sales_last_month"),
            InlineKeyboardButton(text="📅 3 oy", callback_data="sales_3months")
        ],
        [InlineKeyboardButton(text="✏️ Maxsus oraliq", callback_data="sales_custom")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")]
    ])


def get_sales_report_actions(date_from: str, date_to: str) -> InlineKeyboardMarkup:
    """Hisobotdan keyin amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Excel hisobot yuklab olish",
            callback_data=f"sales_excel_{date_from}_{date_to}"
        )],
        [InlineKeyboardButton(text="🔄 Boshqa oraliq", callback_data="sales_back")]
    ])


# ============ QARZLAR ============

def get_debtors_keyboard(debtors: list) -> InlineKeyboardMarkup:
    """Qarzdor ustalar ro'yxati"""
    buttons = []
    for d in debtors[:20]:
        text = f"💳 {d['full_name']} - {int(d['total_debt']):,} so'm ({d['debt_orders_count']} ta)"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"debtor_{d['telegram_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_debt_actions_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Bitta qarzdor uchun amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Hammasini to'langan deb belgilash",
                              callback_data=f"debt_payall_{telegram_id}")],
        [InlineKeyboardButton(text="💰 Qisman to'lov qo'shish",
                              callback_data=f"debt_paypart_{telegram_id}")],
        [InlineKeyboardButton(text="⬅️ Qarzdorlar ro'yxati", callback_data="back_to_debtors")]
    ])


def get_debt_orders_keyboard(orders: list) -> InlineKeyboardMarkup:
    """Bitta foydalanuvchining qarzdor buyurtmalari (qaysi biriga to'lov qo'shish)"""
    buttons = []
    for o in orders[:15]:
        debt = int(o['debt_amount'])
        buttons.append([InlineKeyboardButton(
            text=f"#{o['id']} - {debt:,} so'm qarz",
            callback_data=f"debt_order_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_to_debtors")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============ TUGAB QOLAYOTGAN MAHSULOTLAR ============

def get_sell_users_kb(users: list) -> InlineKeyboardMarkup:
    """Tezkor sotuv: qaysi usta sotib oldi (yoki boshqa usta)"""
    buttons = [[InlineKeyboardButton(text="🆕 Boshqa usta (tizimda yo'q)", callback_data="sell_other_user")]]
    for u in users[:90]:
        buttons.append([InlineKeyboardButton(
            text=f"👤 {u['full_name']} - {u['phone']}",
            callback_data=f"sellu_{u['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_sell_payment_kb() -> InlineKeyboardMarkup:
    """Tezkor sotuv: to'lov holati"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'liq to'ladi", callback_data="sellpay_paid")],
        [InlineKeyboardButton(text="📒 Qarzga oldi", callback_data="sellpay_debt")],
        [InlineKeyboardButton(text="💰 Qisman to'ladi", callback_data="sellpay_partial")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")]
    ])


def get_low_stock_keyboard() -> InlineKeyboardMarkup:
    """Tugab qolayotgan mahsulotlar bo'limi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Ro'yxat ko'rish", callback_data="lowstock_view")],
        [InlineKeyboardButton(text="📊 Excel yuklab olish", callback_data="lowstock_excel")],
        [InlineKeyboardButton(text="📂 Kategoriya bo'yicha", callback_data="lowstock_by_cat")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")]
    ])
