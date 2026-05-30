"""
Admin paneli handlerlari
Yangilangan: sotuv hisoboti, qarz boshqaruvi, kategoriyalar, Excel eksport
"""
import os
import tempfile
import aiosqlite
from datetime import datetime, timedelta, date
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.admin_kb import (
    get_admin_menu, get_products_menu,
    get_categories_admin_keyboard, get_brands_admin_keyboard,
    get_models_admin_keyboard, get_products_admin_keyboard,
    get_product_edit_keyboard, get_users_management_keyboard,
    get_user_action_keyboard, get_order_admin_keyboard,
    get_sales_period_keyboard, get_sales_report_actions,
    get_debtors_keyboard, get_debt_actions_keyboard, get_debt_orders_keyboard,
    get_low_stock_keyboard, get_sell_users_kb, get_sell_payment_kb,
    get_manage_brands_kb, get_brand_manage_kb, get_brand_delete_confirm_kb,
    get_manage_models_kb, get_model_manage_kb, get_model_delete_confirm_kb
)
from keyboards.user_kb import get_main_menu
from states import AdminStates, SalesReportStates, DebtStates, SellStates
from config import config, uz_now
from utils.excel_reports import generate_low_stock_report, generate_sales_report
from utils.excel_import import generate_template, parse_import_file

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


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


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
        f"  • Mahsulot turlari: {stats['total_products']}\n"
        f"  • Omborda jami: {stats['total_stock']} dona\n"
        f"  • ⚠️ Tugab qolayotgan: {stats['low_stock_count']} ta\n\n"
        f"🛒 <b>Buyurtmalar:</b>\n"
        f"  • Jami: {stats['total_orders']}\n"
        f"  • ⏳ Kutilmoqda: {stats['pending_orders']}\n"
        f"  • ✅ Tasdiqlangan: {stats['confirmed_orders']}\n"
        f"  • 🎉 Yakunlangan: {stats['completed_orders']}\n\n"
        f"💰 <b>Sotuv (jami): {int(stats['total_revenue']):,} so'm</b>\n"
        f"💳 <b>Qarz (jami): {int(stats['total_debt']):,} so'm</b>"
    )
    await message.answer(text, parse_mode="HTML")


# ============ SOTUV HISOBOTI ============

PERIOD_NAMES = {
    "today": "Bugun",
    "yesterday": "Kecha",
    "week": "Bu hafta",
    "month": "Bu oy",
    "last_month": "O'tgan oy",
    "3months": "3 oy",
}


def _date_range(period: str):
    """period nomidan (date_from, date_to) qaytaradi (YYYY-MM-DD)"""
    today = uz_now().date()
    if period == "today":
        return today.isoformat(), today.isoformat()
    if period == "yesterday":
        y = today - timedelta(days=1)
        return y.isoformat(), y.isoformat()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat()
    if period == "month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev.isoformat(), last_prev.isoformat()
    if period == "3months":
        start = today - timedelta(days=90)
        return start.isoformat(), today.isoformat()
    return today.isoformat(), today.isoformat()


@router.message(F.text == "💰 Sotuv")
async def sales_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "💰 <b>Sotuv hisoboti</b>\n\nQaysi oraliq uchun hisobot kerak?",
        parse_mode="HTML",
        reply_markup=get_sales_period_keyboard()
    )


@router.callback_query(F.data == "sales_back")
async def sales_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "💰 <b>Sotuv hisoboti</b>\n\nQaysi oraliq uchun hisobot kerak?",
        parse_mode="HTML",
        reply_markup=get_sales_period_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_({
    "sales_today", "sales_yesterday", "sales_week",
    "sales_month", "sales_last_month", "sales_3months"
}))
async def sales_quick_period(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    period = callback.data.replace("sales_", "")
    df, dt = _date_range(period)
    await _send_sales_summary(callback, df, dt, period_label=PERIOD_NAMES.get(period, period))


@router.callback_query(F.data == "sales_custom")
async def sales_custom(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SalesReportStates.waiting_date_from)
    await callback.message.edit_text(
        "📆 <b>Maxsus sana oralig'i</b>\n\n"
        "Boshlanish sanasini kiriting (format: <code>YYYY-MM-DD</code>)\n"
        "Masalan: <code>2026-04-01</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SalesReportStates.waiting_date_from, F.text)
async def custom_date_from(message: Message, state: FSMContext):
    try:
        df = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Noto'g'ri format. <code>YYYY-MM-DD</code> shaklida kiriting:", parse_mode="HTML")
        return
    await state.update_data(date_from=df.isoformat())
    await state.set_state(SalesReportStates.waiting_date_to)
    await message.answer(
        f"✅ Boshlanish: <b>{df.isoformat()}</b>\n\n"
        f"Endi tugash sanasini kiriting (<code>YYYY-MM-DD</code>):",
        parse_mode="HTML"
    )


@router.message(SalesReportStates.waiting_date_to, F.text)
async def custom_date_to(message: Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Noto'g'ri format. <code>YYYY-MM-DD</code>:", parse_mode="HTML")
        return
    data = await state.get_data()
    df = data['date_from']
    if dt.isoformat() < df:
        await message.answer("❌ Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas:")
        return
    await state.clear()
    await _send_sales_summary_msg(message, df, dt.isoformat(), period_label="Maxsus")


async def _send_sales_summary(callback: CallbackQuery, df: str, dt: str, period_label: str):
    summary = await db.get_sales_summary(df, dt)
    text = _format_sales_summary(summary, df, dt, period_label)
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=get_sales_report_actions(df, dt)
    )
    await callback.answer()


async def _send_sales_summary_msg(message: Message, df: str, dt: str, period_label: str):
    summary = await db.get_sales_summary(df, dt)
    text = _format_sales_summary(summary, df, dt, period_label)
    await message.answer(
        text, parse_mode="HTML",
        reply_markup=get_sales_report_actions(df, dt)
    )


def _format_sales_summary(s: dict, df: str, dt: str, label: str) -> str:
    revenue = float(s.get('revenue', 0) or 0)
    cost = float(s.get('cost', 0) or 0)
    profit = float(s.get('profit', 0) or 0)
    margin = float(s.get('margin_percent', 0) or 0)
    paid = float(s.get('paid_received', 0) or 0)
    debt_added = float(s.get('debt_added', 0) or 0)

    profit_emoji = "🟢" if profit >= 0 else "🔴"
    profit_word = "Foyda" if profit >= 0 else "Zarar"

    same_day = (df == dt)
    period_display = df if same_day else f"{df} → {dt}"

    return (
        f"💰 <b>Sotuv hisoboti — {label}</b>\n"
        f"📅 {period_display}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛒 Buyurtmalar: <b>{s.get('orders_count', 0)} ta</b>\n"
        f"📦 Sotilgan dona: <b>{int(s.get('units_sold', 0))}</b>\n\n"
        f"💵 Tushum (sotuv): <b>{int(revenue):,} so'm</b>\n"
        f"🏷 Tannarx (xarid): <b>{int(cost):,} so'm</b>\n"
        f"{profit_emoji} <b>{profit_word}: {int(profit):,} so'm</b>\n"
        f"📈 Marja: <b>{margin:.1f}%</b>\n\n"
        f"💰 Hozir tushgan: <b>{int(paid):,} so'm</b>\n"
        f"📒 Qarzga ketgan: <b>{int(debt_added):,} so'm</b>"
    )


@router.callback_query(F.data.startswith("sales_excel_"))
async def sales_excel(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    df = parts[2]
    dt = parts[3]
    await callback.answer("📊 Excel tayyorlanmoqda...")

    summary = await db.get_sales_summary(df, dt)
    by_cat = await db.get_sales_by_category(df, dt)
    details = await db.get_sales_details(df, dt)

    path = generate_sales_report(summary, by_cat, details, df, dt)
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=FSInputFile(path),
        caption=f"💰 Sotuv hisoboti: {df} → {dt}"
    )


# ============ QARZLAR ============

@router.message(F.text == "💳 Qarzlar")
async def debts_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()

    debtors = await db.get_all_debtors()
    if not debtors:
        await message.answer("✅ Qarzdor ustalar yo'q!")
        return

    total = sum(float(d['total_debt']) for d in debtors)
    text = (
        f"💳 <b>Qarzdor ustalar ({len(debtors)} ta)</b>\n"
        f"Jami qarz: <b>{int(total):,} so'm</b>\n\n"
        f"Tanlash uchun ustani bosing:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_debtors_keyboard(debtors))


@router.callback_query(F.data == "back_to_debtors")
async def back_to_debtors(callback: CallbackQuery):
    debtors = await db.get_all_debtors()
    if not debtors:
        await callback.message.edit_text("✅ Qarzdor ustalar yo'q!")
        await callback.answer()
        return
    total = sum(float(d['total_debt']) for d in debtors)
    text = (
        f"💳 <b>Qarzdor ustalar ({len(debtors)} ta)</b>\n"
        f"Jami qarz: <b>{int(total):,} so'm</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_debtors_keyboard(debtors))
    await callback.answer()


@router.callback_query(F.data.startswith("debtor_"))
async def show_debtor(callback: CallbackQuery):
    telegram_id = int(callback.data.split("_")[1])
    user = await db.get_user(telegram_id)
    debts = await db.get_user_debts(user['id'])
    total = await db.get_user_total_debt(user['id'])

    text = (
        f"💳 <b>{user['full_name']}</b>\n"
        f"📱 {user['phone']}\n"
        f"🆔 <code>{telegram_id}</code>\n\n"
        f"<b>Jami qarz: {int(total):,} so'm</b> ({len(debts)} ta buyurtma)\n\n"
    )
    for d in debts[:10]:
        product_title = d.get('product_name', '?')
        if d.get('brand_name') and d.get('model_name'):
            product_title = f"{d['brand_name']} {d['model_name']} — {product_title}"
        text += (
            f"📦 <b>#{d['id']}</b> — {product_title}\n"
            f"   Miqdor: {d['quantity']} dona | Jami: {int(d['total_price']):,} | "
            f"To'langan: {int(d['paid_amount']):,} | <b>Qarz: {int(d['debt_amount']):,} so'm</b>\n"
            f"   📅 {d['created_at'][:16]}\n\n"
        )

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=get_debt_actions_keyboard(telegram_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("debt_payall_"))
async def debt_pay_all(callback: CallbackQuery, bot: Bot):
    telegram_id = int(callback.data.split("_")[2])
    user = await db.get_user(telegram_id)
    paid_sum = await db.pay_user_full_debt(user['id'])

    await callback.message.edit_text(
        f"✅ <b>{user['full_name']}</b> ning barcha qarzlari to'langan deb belgilandi.\n"
        f"💰 Jami: <b>{int(paid_sum):,} so'm</b>",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            telegram_id,
            f"✅ Sizning barcha qarzlaringiz to'langan deb admin tomonidan belgilandi.\n"
            f"💰 Jami: <b>{int(paid_sum):,} so'm</b>\n\nRahmat! ❤️",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer("✅ Bajarildi")


@router.callback_query(F.data.startswith("debt_paypart_"))
async def debt_part_select(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split("_")[2])
    user = await db.get_user(telegram_id)
    debts = await db.get_user_debts(user['id'])

    if not debts:
        await callback.answer("Qarz yo'q", show_alert=True)
        return

    await callback.message.edit_text(
        f"💰 <b>{user['full_name']}</b> ning qarzdor buyurtmalari:\n\n"
        f"Qaysi buyurtmaga to'lov qo'shasiz?",
        parse_mode="HTML",
        reply_markup=get_debt_orders_keyboard(debts)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("debt_order_"))
async def debt_order_select(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    debt = float(order['total_price']) - float(order.get('paid_amount', 0) or 0)
    await state.set_state(DebtStates.waiting_payment_amount)
    await state.update_data(order_id=order_id, telegram_id=order['telegram_id'])
    await callback.message.edit_text(
        f"💰 <b>Buyurtma #{order_id}</b>\n"
        f"Jami: {int(order['total_price']):,} so'm\n"
        f"To'langan: {int(order.get('paid_amount', 0) or 0):,} so'm\n"
        f"<b>Qarz: {int(debt):,} so'm</b>\n\n"
        f"Qancha to'lov qo'shasiz? (so'mda raqam kiriting):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DebtStates.waiting_payment_amount, F.text)
async def debt_pay_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip().replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa. Faqat raqam kiriting:")
        return

    data = await state.get_data()
    result = await db.pay_order_debt(data['order_id'], amount)
    await state.clear()

    remaining = result['total_price'] - result['paid_amount']
    status_text = "to'liq to'langan" if result['payment_status'] == "paid" else "qisman to'langan"

    await message.answer(
        f"✅ <b>To'lov qo'shildi!</b>\n\n"
        f"Buyurtma #{data['order_id']}\n"
        f"To'langan: <b>{int(result['paid_amount']):,} so'm</b>\n"
        f"Qoldiq qarz: <b>{int(remaining):,} so'm</b>\n"
        f"Holat: <b>{status_text}</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )

    try:
        await bot.send_message(
            data['telegram_id'],
            f"💰 Buyurtma #{data['order_id']} uchun to'lov qabul qilindi: "
            f"<b>{int(amount):,} so'm</b>\n"
            f"Qoldiq qarz: <b>{int(remaining):,} so'm</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ============ TUGAB QOLAYOTGAN MAHSULOTLAR ============

@router.message(F.text == "📉 Tugab qolganlar")
async def low_stock_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    products = await db.get_low_stock_products()
    cnt = len(products)
    zero_cnt = sum(1 for p in products if p['quantity'] == 0)

    text = (
        f"📉 <b>Tugab qolayotgan mahsulotlar</b>\n\n"
        f"Jami: <b>{cnt}</b> ta\n"
        f"Tugab qolgan (0 dona): <b>{zero_cnt}</b> ta\n"
        f"Tugayotgan: <b>{cnt - zero_cnt}</b> ta\n\n"
        f"<i>Bu ro'yxat — Toshkentdan zakaz qilish uchun</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_low_stock_keyboard())


@router.callback_query(F.data == "lowstock_view")
async def low_stock_view(callback: CallbackQuery):
    products = await db.get_low_stock_products()
    if not products:
        await callback.message.edit_text("✅ Ombor to'la! Tugab qolayotgan mahsulot yo'q.")
        await callback.answer()
        return

    # Telegramda chiqarish (qisqacha, kategoriya bo'yicha)
    text = "📉 <b>Tugab qolayotgan mahsulotlar:</b>\n\n"
    current_cat = None
    cnt = 0
    for p in products[:60]:
        if p['category_name'] != current_cat:
            current_cat = p['category_name']
            text += f"\n<b>{p['category_icon']} {current_cat}</b>\n"
        emoji = "❌" if p['quantity'] == 0 else "⚠️"
        loc = ""
        if p.get('brand_name'):
            loc = f"{p['brand_name']} {p.get('model_name','')} — "
        text += f"{emoji} {loc}{p['name']}: <b>{p['quantity']}</b> dona (min: {p['min_quantity']})\n"
        cnt += 1

    if len(products) > 60:
        text += f"\n<i>... yana {len(products) - 60} ta. Excel orqali to'liq ko'ring.</i>"

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=get_low_stock_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "lowstock_excel")
async def low_stock_excel(callback: CallbackQuery, bot: Bot):
    products = await db.get_low_stock_products()
    if not products:
        await callback.answer("✅ Tugab qolayotgan yo'q", show_alert=True)
        return
    await callback.answer("📊 Excel tayyorlanmoqda...")
    path = generate_low_stock_report(products)
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=FSInputFile(path),
        caption=f"📉 Tugab qolayotgan mahsulotlar ({len(products)} ta)\n"
                f"Toshkentdan zakaz qilish uchun ro'yxat"
    )


@router.callback_query(F.data == "lowstock_by_cat")
async def low_stock_by_cat(callback: CallbackQuery):
    categories = await db.get_categories()
    await callback.message.edit_text(
        "📂 Qaysi kategoriyani ko'rmoqchisiz?",
        reply_markup=get_categories_admin_keyboard(categories, action="lowstockcat")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_lowstockcat_cat_"))
async def low_stock_one_cat(callback: CallbackQuery, bot: Bot):
    category_id = int(callback.data.split("_")[3])
    category = await db.get_category(category_id)
    products = await db.get_low_stock_products(category_id)

    if not products:
        await callback.message.edit_text(
            f"✅ <b>{category['icon']} {category['name']}</b> bo'yicha tugab qolayotgan yo'q.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"📉 <b>{category['icon']} {category['name']} — tugab qolayotganlar</b>\n\n"
    for p in products[:50]:
        loc = ""
        if p.get('brand_name'):
            loc = f"{p['brand_name']} {p.get('model_name','')} — "
        emoji = "❌" if p['quantity'] == 0 else "⚠️"
        text += f"{emoji} {loc}{p['name']}: <b>{p['quantity']}</b> dona\n"

    # Excel-ni ham yuborish taklifi
    await callback.message.edit_text(text, parse_mode="HTML")
    path = generate_low_stock_report(products)
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=FSInputFile(path),
        caption=f"📉 {category['name']} kategoriyasi — Excel"
    )
    await callback.answer()


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
    await message.answer(text, parse_mode="HTML", reply_markup=get_users_management_keyboard(users))


@router.callback_query(F.data.startswith("manage_user_"))
async def manage_one_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    telegram_id = int(callback.data.split("_")[2])
    user = await db.get_user(telegram_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    debt = await db.get_user_total_debt(user['id'])
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
    if debt > 0:
        text += f"\n💳 <b>Qarzi: {int(debt):,} so'm</b>"

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=get_user_action_keyboard(
            telegram_id, user['is_approved'], user['is_blocked'], has_debt=(debt > 0)
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("user_debts_"))
async def user_debts(callback: CallbackQuery):
    telegram_id = int(callback.data.split("_")[2])
    await show_debtor(callback)  # bir xil ko'rinish


@router.callback_query(F.data == "admin_back_users")
async def back_to_users(callback: CallbackQuery):
    users = await db.get_all_users()
    text = (
        f"👥 <b>Ustalar ro'yxati</b> ({len(users)} ta)\n\n"
        "✅ - tasdiqlangan | ⏳ - kutilmoqda | 🚫 - bloklangan"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
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


# ============ MAHSULOTLAR MENU ============

@router.message(F.text == "📦 Mahsulotlar")
async def products_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📦 <b>Mahsulotlarni boshqarish:</b>",
        parse_mode="HTML",
        reply_markup=get_products_menu()
    )


# === EXCEL IMPORT ===

def _to_number(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(" ", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def _to_int(v):
    n = _to_number(v)
    return int(n) if n is not None else None


@router.callback_query(F.data == "admin_import")
async def import_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_import_file)
    await callback.message.edit_text(
        "📥 <b>Excel orqali import</b>\n\n"
        "1️⃣ Pastdagi tugmadan shablonni yuklab oling\n"
        "2️⃣ Uni mahsulotlaringiz bilan to'ldiring\n"
        "3️⃣ To'ldirilgan <code>.xlsx</code> faylni shu yerga yuboring\n\n"
        "<i>Bir xil mahsulot bo'lsa — yangilanadi, takror qo'shilmaydi.\n"
        "Yangi brend/model avtomatik yaratiladi.</i>\n\n"
        "Bekor qilish: /admin",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Shablonni yuklab olish", callback_data="import_template")],
            [InlineKeyboardButton(text="❌ Bekor", callback_data="admin_cancel")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "import_template")
async def import_template(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer("📄 Shablon tayyorlanmoqda...")
    path = generate_template()
    await bot.send_document(
        callback.from_user.id,
        FSInputFile(path, filename="import_shablon.xlsx"),
        caption="📄 Shablonni to'ldirib, shu yerga (xabar sifatida) yuboring."
    )


@router.message(AdminStates.waiting_import_file, F.document)
async def import_file(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    doc = message.document
    if not doc.file_name.lower().endswith((".xlsx", ".xlsm")):
        await message.answer("❌ Faqat <code>.xlsx</code> fayl yuboring (shablon kabi).", parse_mode="HTML")
        return

    tmp_path = os.path.join(tempfile.gettempdir(), f"import_{message.from_user.id}.xlsx")
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=tmp_path)
    except Exception as e:
        await message.answer(f"❌ Faylni yuklab bo'lmadi: {e}")
        return

    rows, fatal = parse_import_file(tmp_path)
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    if fatal:
        await message.answer(f"❌ {fatal}", parse_mode="HTML")
        return
    if not rows:
        await message.answer("⚠️ Faylda mahsulot topilmadi.")
        return

    await message.answer(f"⏳ {len(rows)} ta qator qayta ishlanmoqda...")

    cats = await db.get_categories()
    catmap = {c["name"].lower(): c for c in cats}

    added = updated = skipped = 0
    errors = []

    for r in rows:
        cval = str(r["category"]).strip() if r["category"] else ""
        cat = catmap.get(cval.lower())
        if not cat:
            skipped += 1
            errors.append(f"{r['row']}-qator: kategoriya '{cval}' noto'g'ri")
            continue

        name = str(r["name"]).strip() if r["name"] else ""
        if not name:
            skipped += 1
            errors.append(f"{r['row']}-qator: nomi bo'sh")
            continue

        price = _to_number(r["price"])
        if price is None or price <= 0:
            skipped += 1
            errors.append(f"{r['row']}-qator: narx noto'g'ri")
            continue

        cost = _to_number(r["cost"]) or 0
        qty = _to_int(r["quantity"]) or 0
        minq = _to_int(r["min"])
        if minq is None:
            minq = 3
        desc = str(r["description"]).strip() if r["description"] else ""

        model_id = None
        if cat["requires_model"]:
            bval = str(r["brand"]).strip() if r["brand"] else ""
            mval = str(r["model"]).strip() if r["model"] else ""
            if not bval or not mval:
                skipped += 1
                errors.append(f"{r['row']}-qator: {cat['name']} uchun brend va model shart")
                continue
            brand_id = await db.get_or_create_brand(bval)
            model_id = await db.get_or_create_model(brand_id, mval)

        res = await db.upsert_product(cat["id"], model_id, name, cost, price, qty, minq, desc)
        if res == "added":
            added += 1
        else:
            updated += 1

    await state.clear()

    report = (
        f"✅ <b>Import yakunlandi!</b>\n\n"
        f"➕ Qo'shildi: <b>{added}</b>\n"
        f"♻️ Yangilandi: <b>{updated}</b>\n"
        f"⚠️ O'tkazib yuborildi: <b>{skipped}</b>"
    )
    if errors:
        report += "\n\n<b>Xatolar:</b>\n" + "\n".join(errors[:15])
        if len(errors) > 15:
            report += f"\n... yana {len(errors) - 15} ta"

    await message.answer(report, parse_mode="HTML", reply_markup=get_admin_menu())


# ============ TEZKOR SOTUV (do'kondan naqd, qo'lda qayd etish) ============

def _product_title(product: dict) -> str:
    title = product["name"]
    if product.get("model_name"):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"
    return title


@router.message(F.text == "🧾 Tezkor sotuv")
async def sell_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    cats = await db.get_categories()
    await message.answer(
        "🧾 <b>Tezkor sotuv</b> (do'kondan naqd, botsiz)\n\n"
        "Bu sotuv skladdan ayiriladi va hisobotga qo'shiladi.\n\n"
        "Kategoriyani tanlang:",
        parse_mode="HTML",
        reply_markup=get_categories_admin_keyboard(cats, action="sellcat")
    )


@router.callback_query(F.data.startswith("admin_sellcat_cat_"))
async def sell_select_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    cat_id = int(callback.data.split("_")[3])
    cat = await db.get_category(cat_id)
    await state.update_data(sell_category=cat_id)

    if not cat["requires_model"]:
        products = await db.get_universal_products(cat_id)
        if not products:
            await callback.answer("Bu bo'limda mahsulot yo'q", show_alert=True)
            return
        await callback.message.edit_text(
            f"{cat['icon']} <b>{cat['name']}</b>\n\nMahsulotni tanlang:",
            parse_mode="HTML",
            reply_markup=get_products_admin_keyboard(products, action="sell")
        )
        await callback.answer()
        return

    brands = await db.get_brands_with_products(cat_id)
    if not brands:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    await callback.message.edit_text(
        f"{cat['icon']} <b>{cat['name']}</b>\n\nBrendni tanlang:",
        parse_mode="HTML",
        reply_markup=get_brands_admin_keyboard(brands, action="sellbrand")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sellbrand_brand_"))
async def sell_select_brand(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    cat_id = data.get("sell_category")
    models = await db.get_models_with_products(brand_id, cat_id)
    if not models:
        await callback.answer("Model yo'q", show_alert=True)
        return
    brand = await db.get_brand(brand_id)
    await callback.message.edit_text(
        f"📱 <b>{brand['name']}</b>\n\nModelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_admin_keyboard(models, action="sellmodel")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sellmodel_model_"))
async def sell_select_model(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    cat_id = data.get("sell_category")
    products = await db.get_products_by_model(model_id, cat_id)
    if not products:
        await callback.answer("Mahsulot yo'q", show_alert=True)
        return
    model = await db.get_model(model_id)
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\nMahsulotni tanlang:",
        parse_mode="HTML",
        reply_markup=get_products_admin_keyboard(products, action="sell")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sell_prod_"))
async def sell_select_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    product_id = int(callback.data.split("_")[3])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if product["quantity"] <= 0:
        await callback.answer("❌ Bu mahsulot tugagan!", show_alert=True)
        return

    await state.update_data(sell_product_id=product_id)
    await state.set_state(SellStates.waiting_quantity)
    await callback.message.edit_text(
        f"{product.get('category_icon','📦')} <b>{_product_title(product)}</b>\n"
        f"💰 Narx: {int(product['price']):,} so'm\n"
        f"📦 Mavjud: {product['quantity']} dona\n\n"
        f"<b>Nechta dona sotildi?</b> Raqam kiriting:\n"
        f"<i>Bekor qilish: /admin</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SellStates.waiting_quantity, F.text)
async def sell_enter_quantity(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat butun son kiriting (yoki /admin):")
        return

    data = await state.get_data()
    product = await db.get_product(data.get("sell_product_id"))
    if not product:
        await state.clear()
        await message.answer("❌ Mahsulot topilmadi.", reply_markup=get_admin_menu())
        return
    if qty > product["quantity"]:
        await message.answer(f"❌ Omborda faqat {product['quantity']} dona bor. Kamroq kiriting:")
        return

    await state.update_data(sell_quantity=qty)
    await state.set_state(SellStates.choosing_user)
    users = await db.get_sellable_users()
    await message.answer(
        "👤 <b>Qaysi usta sotib oldi?</b>\n\n"
        "Ro'yxatdan tanlang yoki <b>🆕 Boshqa usta</b> bosing:",
        parse_mode="HTML",
        reply_markup=get_sell_users_kb(users)
    )


@router.callback_query(F.data.startswith("sellu_"), SellStates.choosing_user)
async def sell_pick_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split("_")[1])
    user = await db.get_user_by_id(user_id)
    await state.update_data(sell_user_id=user_id)
    await _ask_sell_payment(callback.message, state, edit=True,
                            buyer=user["full_name"] if user else "Usta")
    await callback.answer()


@router.callback_query(F.data == "sell_other_user", SellStates.choosing_user)
async def sell_other_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SellStates.waiting_other_name)
    await callback.message.edit_text(
        "✍️ <b>Ustaning ism-familiyasini kiriting:</b>\n\n"
        "<i>Qarz/qisman bo'lsa, qarz shu nom ostida saqlanadi va keyin "
        "'💳 Qarzlar' bo'limida ko'rinadi.\n"
        "Noma'lum bo'lsa '-' yuboring.</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SellStates.waiting_other_name, F.text)
async def sell_other_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if name == "-" or not name:
        user_id = await db.get_or_create_walkin_user()
        buyer = "🏪 Boshqa usta (noma'lum)"
    else:
        if len(name) > 100:
            await message.answer("❌ Juda uzun. Qisqaroq kiriting:")
            return
        user_id = await db.get_or_create_offline_user(name)
        buyer = name
    await state.update_data(sell_user_id=user_id)
    await _ask_sell_payment(message, state, edit=False, buyer=buyer)


async def _ask_sell_payment(target_message, state: FSMContext, edit: bool, buyer: str):
    data = await state.get_data()
    product = await db.get_product(data["sell_product_id"])
    qty = data["sell_quantity"]
    total = float(product["price"]) * qty
    profit = (float(product["price"]) - float(product["cost_price"])) * qty

    await state.update_data(sell_buyer=buyer)
    await state.set_state(SellStates.choosing_payment)
    text = (
        f"🧾 <b>Sotuv:</b>\n\n"
        f"👤 Usta: <b>{buyer}</b>\n"
        f"{product.get('category_icon','📦')} {_product_title(product)}\n"
        f"📦 {qty} dona\n"
        f"💰 Summa: <b>{int(total):,} so'm</b>\n"
        f"📈 Foyda: <b>{int(profit):,} so'm</b>\n"
        f"📦 Qoladi: <b>{product['quantity'] - qty} dona</b>\n\n"
        f"<b>To'lov holati?</b>"
    )
    if edit:
        await target_message.edit_text(text, parse_mode="HTML", reply_markup=get_sell_payment_kb())
    else:
        await target_message.answer(text, parse_mode="HTML", reply_markup=get_sell_payment_kb())


@router.callback_query(F.data == "sellpay_paid", SellStates.choosing_payment)
async def sell_pay_paid(callback: CallbackQuery, state: FSMContext):
    await _finalize_sale_cb(callback, state, "paid", None)


@router.callback_query(F.data == "sellpay_debt", SellStates.choosing_payment)
async def sell_pay_debt(callback: CallbackQuery, state: FSMContext):
    await _finalize_sale_cb(callback, state, "debt", None)


@router.callback_query(F.data == "sellpay_partial", SellStates.choosing_payment)
async def sell_pay_partial(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    product = await db.get_product(data["sell_product_id"])
    total = float(product["price"]) * data["sell_quantity"]
    await state.set_state(SellStates.waiting_partial)
    await callback.message.edit_text(
        f"💰 Jami: <b>{int(total):,} so'm</b>\n\n"
        f"Usta qancha to'ladi? Raqam kiriting:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SellStates.waiting_partial, F.text)
async def sell_partial_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = float(message.text.strip().replace(" ", "").replace(",", ""))
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Raqam kiriting:")
        return
    text = await _finalize_sale(state, "partial", amount)
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_menu())


async def _finalize_sale(state: FSMContext, payment_status: str, amount) -> str:
    """Sotuvni yakunlaydi va natija matnini qaytaradi."""
    data = await state.get_data()
    res = await db.add_manual_sale(
        data["sell_product_id"], data["sell_quantity"],
        data["sell_user_id"], payment_status, amount
    )
    buyer = data.get("sell_buyer", "")
    await state.clear()

    if res.get("error") == "stock":
        return f"❌ Omborda yetarli emas (faqat {res['available']} dona). Bekor qilindi."
    if res.get("error"):
        return "❌ Xato: mahsulot topilmadi."

    pstatus_txt = {"paid": "✅ To'liq to'ladi", "debt": "📒 Qarz", "partial": "💰 Qisman"}[payment_status]
    text = (
        f"✅ <b>Sotuv qayd etildi!</b>\n\n"
        f"🆔 #{res['order_id']}\n"
        f"👤 Usta: <b>{buyer}</b>\n"
        f"💰 Summa: <b>{int(res['total']):,} so'm</b>\n"
        f"📈 Foyda: <b>{int(res['profit']):,} so'm</b>\n"
        f"💼 To'lov: <b>{pstatus_txt}</b>\n"
    )
    if res["debt"] > 0:
        text += f"📒 Qarz qoldi: <b>{int(res['debt']):,} so'm</b>\n"
    text += f"📦 Omborda qoldi: <b>{res['remaining']} dona</b>\n\n<i>Hisobotga qo'shildi.</i>"
    return text


async def _finalize_sale_cb(callback: CallbackQuery, state: FSMContext, payment_status: str, amount):
    if not is_admin(callback.from_user.id):
        return
    text = await _finalize_sale(state, payment_status, amount)
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()
    await callback.message.answer("Admin paneli:", reply_markup=get_admin_menu())


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
        parse_mode="HTML", reply_markup=get_admin_menu()
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
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


# === MAHSULOT QO'SHISH (universal — har qanday kategoriya) ===

@router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    categories = await db.get_categories()
    await state.set_state(AdminStates.selecting_category_for_product)
    await callback.message.edit_text(
        "📂 Mahsulot kategoriyasini tanlang:",
        reply_markup=get_categories_admin_keyboard(categories, action="addprodcat")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_category_for_product, F.data.startswith("admin_addprodcat_cat_"))
async def select_category_for_product(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[3])
    category = await db.get_category(category_id)
    await state.update_data(category_id=category_id)

    # Aksessuar — brend/model yo'q
    if not category['requires_model']:
        await state.set_state(AdminStates.waiting_product_name)
        await callback.message.edit_text(
            f"{category['icon']} <b>{category['name']}</b>\n\n"
            f"Mahsulot nomini kiriting (masalan: <b>Universal kabel</b>, <b>Otvyortka to'plami</b>):",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("❌ Avval brend qo'shing!")
        await state.clear()
        await callback.answer()
        return

    await state.set_state(AdminStates.selecting_brand_for_product)
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b>\n\nQaysi brendga qo'shasiz?",
        parse_mode="HTML",
        reply_markup=get_brands_admin_keyboard(brands, action="addprodbrand")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_brand_for_product, F.data.startswith("admin_addprodbrand_brand_"))
async def select_brand_for_product(callback: CallbackQuery, state: FSMContext):
    brand_id = int(callback.data.split("_")[3])
    models = await db.get_models(brand_id)
    if not models:
        await callback.message.edit_text("❌ Bu brendda hali model yo'q. Avval model qo'shing!")
        await state.clear()
        await callback.answer()
        return
    await state.set_state(AdminStates.selecting_model_for_product)
    brand = await db.get_brand(brand_id)
    await callback.message.edit_text(
        f"📱 Brend: <b>{brand['name']}</b>\n\nQaysi modelga qo'shasiz?",
        parse_mode="HTML",
        reply_markup=get_models_admin_keyboard(models, action="addprodmodel")
    )
    await callback.answer()


@router.callback_query(AdminStates.selecting_model_for_product, F.data.startswith("admin_addprodmodel_model_"))
async def select_model_for_product(callback: CallbackQuery, state: FSMContext):
    model_id = int(callback.data.split("_")[3])
    model = await db.get_model(model_id)
    data = await state.get_data()
    category = await db.get_category(data['category_id'])

    await state.update_data(model_id=model_id)
    await state.set_state(AdminStates.waiting_product_name)

    examples = {
        "Ekran": "OLED Original, OLED Copy, IPS Copy",
        "Orqa krishka": "Original krishka, Copy krishka",
        "Batareya": "Original 3000mAh, Copy 3500mAh",
        "Kamera shisha": "Asosiy kamera shishasi, Old kamera shishasi",
        "Pastki plata": "Asosiy plata, Copy plata",
    }
    ex = examples.get(category['name'], "mahsulot turi")

    await callback.message.edit_text(
        f"{category['icon']} <b>{model['brand_name']} {model['name']}</b> uchun <b>{category['name']}</b>\n\n"
        f"Mahsulot turini kiriting:\nMasalan: <i>{ex}</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_product_name, F.text)
async def save_product_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer("❌ Nomi 2-100 belgi bo'lishi kerak.")
        return
    await state.update_data(product_name=name)
    await state.set_state(AdminStates.waiting_product_cost)
    await message.answer(
        "🏷 <b>Tannarx</b>ni kiriting (Toshkentdan necha pulga olib kelinadi, so'mda):\n"
        "Masalan: <code>500000</code>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_product_cost, F.text)
async def save_product_cost(message: Message, state: FSMContext):
    try:
        cost = float(message.text.strip().replace(" ", "").replace(",", ""))
        if cost < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri. Faqat raqam kiriting:")
        return
    await state.update_data(cost=cost)
    await state.set_state(AdminStates.waiting_product_price)
    await message.answer(
        "💰 <b>Sotish narxi</b>ni kiriting (ustalarga necha pulga sotiladi):\n"
        "Masalan: <code>750000</code>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_product_price, F.text)
async def save_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri narx. Faqat raqam kiriting:")
        return
    await state.update_data(price=price)
    await state.set_state(AdminStates.waiting_product_quantity)
    await message.answer("📦 Necha dona mavjud? (raqam):")


@router.message(AdminStates.waiting_product_quantity, F.text)
async def save_product_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri. Musbat raqam kiriting:")
        return
    await state.update_data(quantity=qty)
    await state.set_state(AdminStates.waiting_product_min_qty)
    await message.answer(
        "⚠️ Minimum miqdor (necha dona qolganda ogohlantirilsin, masalan: <code>3</code>):\n"
        "<i>O'tkazib yuborish uchun '-' yuboring (standart 3)</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_product_min_qty, F.text)
async def save_product_min_qty(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "-":
        min_qty = 3
    else:
        try:
            min_qty = int(txt)
            if min_qty < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Noto'g'ri. Musbat raqam yoki '-' yuboring:")
            return

    await state.update_data(min_quantity=min_qty)
    await state.set_state(AdminStates.waiting_product_description)
    await message.answer(
        "📝 Tavsif (ixtiyoriy). Tashlab ketish uchun <b>'-'</b> yuboring:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_product_description, F.text)
async def save_product_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    if len(desc) > 500:
        await message.answer("❌ Tavsif juda uzun. 500 belgidan kam bo'lsin:")
        return

    data = await state.get_data()
    await db.add_product(
        category_id=data['category_id'],
        model_id=data.get('model_id'),  # aksessuar uchun None
        name=data['product_name'],
        cost_price=data['cost'],
        price=data['price'],
        quantity=data['quantity'],
        min_quantity=data['min_quantity'],
        description=desc
    )

    category = await db.get_category(data['category_id'])
    location = ""
    if data.get('model_id'):
        model = await db.get_model(data['model_id'])
        location = f"{model['brand_name']} {model['name']} • "

    profit_unit = data['price'] - data['cost']

    await state.clear()
    await message.answer(
        f"✅ <b>Mahsulot qo'shildi!</b>\n\n"
        f"{category['icon']} {category['name']}\n"
        f"{location}<b>{data['product_name']}</b>\n\n"
        f"🏷 Tannarx: {int(data['cost']):,} so'm\n"
        f"💰 Sotish: {int(data['price']):,} so'm\n"
        f"📈 Bittasidan foyda: <b>{int(profit_unit):,} so'm</b>\n"
        f"📦 Mavjud: {data['quantity']} dona\n"
        f"⚠️ Min: {data['min_quantity']} dona",
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
        for m in models[:10]:
            text += f"   └ {m['name']}\n"
        if len(models) > 10:
            text += f"   └ <i>... yana {len(models) - 10} ta</i>\n"
        text += "\n"

    if len(text) > 3900:
        text = text[:3900] + "\n... (qisqartirildi)"
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


# === MAHSULOTNI TAHRIRLASH ===

@router.callback_query(F.data == "admin_edit_product")
async def edit_product_start(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    categories = await db.get_categories()
    await callback.message.edit_text(
        "📂 Kategoriyani tanlang:",
        reply_markup=get_categories_admin_keyboard(categories, action="editcat")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_editcat_cat_"))
async def edit_select_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[3])
    category = await db.get_category(category_id)
    await state.update_data(category_id=category_id)

    if not category['requires_model']:
        # Aksessuarlarni to'g'ridan-to'g'ri ko'rsatamiz
        products = await db.get_universal_products(category_id)
        if not products:
            await callback.message.edit_text("❌ Bu bo'limda mahsulot yo'q!")
            await callback.answer()
            return
        await callback.message.edit_text(
            f"{category['icon']} <b>{category['name']}</b>\n\nMahsulotni tanlang:",
            parse_mode="HTML",
            reply_markup=get_products_admin_keyboard(products, action="edit")
        )
        await callback.answer()
        return

    brands = await db.get_brands_with_products(category_id)
    if not brands:
        await callback.message.edit_text("❌ Bu kategoriyada mahsulot yo'q!")
        await callback.answer()
        return
    await callback.message.edit_text(
        f"{category['icon']} <b>{category['name']}</b>\n\nBrendni tanlang:",
        parse_mode="HTML",
        reply_markup=get_brands_admin_keyboard(brands, action="editbrand")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_editbrand_brand_"))
async def edit_select_brand(callback: CallbackQuery, state: FSMContext):
    brand_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    category_id = data.get('category_id')
    models = await db.get_models_with_products(brand_id, category_id)
    if not models:
        await callback.message.edit_text("❌ Bu brendda mahsulot yo'q!")
        await callback.answer()
        return
    brand = await db.get_brand(brand_id)
    await callback.message.edit_text(
        f"📱 <b>{brand['name']}</b>\n\nModelni tanlang:",
        parse_mode="HTML",
        reply_markup=get_models_admin_keyboard(models, action="editmodel")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_editmodel_model_"))
async def edit_select_model(callback: CallbackQuery, state: FSMContext):
    model_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    category_id = data.get('category_id')
    products = await db.get_products_by_model(model_id, category_id)
    if not products:
        await callback.message.edit_text("❌ Bu modelda mahsulot yo'q!")
        await callback.answer()
        return
    model = await db.get_model(model_id)
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\nMahsulotni tanlang:",
        parse_mode="HTML",
        reply_markup=get_products_admin_keyboard(products, action="edit")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_prod_"))
async def edit_select_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[3])
    product = await db.get_product(product_id)
    profit = product['price'] - product['cost_price']

    title = product['name']
    if product.get('model_name'):
        title = f"{product.get('brand_name','')} {product['model_name']} — {product['name']}"

    text = (
        f"{product.get('category_icon','📦')} <b>{title}</b>\n"
        f"📂 Kategoriya: {product.get('category_name','')}\n\n"
        f"🏷 Tannarx: <b>{int(product['cost_price']):,} so'm</b>\n"
        f"💰 Sotish: <b>{int(product['price']):,} so'm</b>\n"
        f"📈 Foyda/dona: <b>{int(profit):,} so'm</b>\n"
        f"📦 Mavjud: <b>{product['quantity']} dona</b>\n"
        f"⚠️ Min: <b>{product['min_quantity']} dona</b>\n\n"
        f"Nimani o'zgartirmoqchisiz?"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=get_product_edit_keyboard(product_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_name_"))
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_product_rename)
    await callback.message.edit_text("✏️ Yangi mahsulot nomini kiriting:")
    await callback.answer()


@router.message(AdminStates.waiting_product_rename, F.text)
async def save_product_rename(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer("❌ Nom 2-100 belgi bo'lishi kerak.")
        return
    data = await state.get_data()
    await db.rename_product(data['product_id'], name)
    await state.clear()
    await message.answer(
        f"✅ Mahsulot nomi o'zgartirildi: <b>{name}</b>",
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("edit_price_"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_new_price)
    await callback.message.edit_text("💰 Yangi <b>sotish narxi</b> (so'mda):", parse_mode="HTML")
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
    await db.update_product_price(data['product_id'], price)
    await state.clear()
    await message.answer(
        f"✅ Sotish narxi yangilandi: <b>{int(price):,} so'm</b>",
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("edit_cost_"))
async def edit_cost_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_new_cost)
    await callback.message.edit_text("🏷 Yangi <b>tannarx</b> (so'mda):", parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_new_cost, F.text)
async def save_new_cost(message: Message, state: FSMContext):
    try:
        cost = float(message.text.strip().replace(" ", "").replace(",", ""))
        if cost < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri:")
        return
    data = await state.get_data()
    await db.update_product_cost(data['product_id'], cost)
    await state.clear()
    await message.answer(
        f"✅ Tannarx yangilandi: <b>{int(cost):,} so'm</b>",
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_qty_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
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
    await db.update_product_quantity(data['product_id'], qty)
    await state.clear()
    await message.answer(
        f"✅ Yangi miqdor: <b>{qty} dona</b>",
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("edit_minqty_"))
async def edit_minqty_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_new_min_qty)
    await callback.message.edit_text("⚠️ Yangi minimum miqdor (necha qolganda ogohlantirilsin):")
    await callback.answer()


@router.message(AdminStates.waiting_new_min_qty, F.text)
async def save_new_min_qty(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri:")
        return
    data = await state.get_data()
    await db.update_product_min_quantity(data['product_id'], qty)
    await state.clear()
    await message.answer(
        f"✅ Minimum miqdor: <b>{qty} dona</b>",
        parse_mode="HTML", reply_markup=get_admin_menu()
    )


@router.callback_query(F.data.startswith("delete_prod_"))
async def delete_product_cb(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    await db.delete_product(product_id)
    await callback.message.edit_text("🗑 Mahsulot o'chirildi.")
    await callback.answer("O'chirildi!")


# ============ TO'LIQ BOSHQARUV: BREND / MODEL ============

@router.callback_query(F.data == "mng_brands")
async def mng_brands(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    brands = await db.get_brands()
    if not brands:
        await callback.message.edit_text("📭 Brendlar yo'q. Avval brend qo'shing.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "🗂 <b>Brend / Model boshqarish</b>\n\nBrendni tanlang:",
        parse_mode="HTML", reply_markup=get_manage_brands_kb(brands)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngb_"))
async def mng_brand_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    if not brand:
        await callback.answer("Brend topilmadi", show_alert=True)
        return
    cnt = await db.count_brand_children(brand_id)
    await callback.message.edit_text(
        f"📱 <b>{brand['name']}</b>\n\n"
        f"📂 Modellar: {cnt['models']} ta\n"
        f"📦 Mahsulotlar: {cnt['products']} ta\n\n"
        f"Amalni tanlang:",
        parse_mode="HTML", reply_markup=get_brand_manage_kb(brand_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngbren_"))
async def mng_brand_rename_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    await state.update_data(brand_id=brand_id)
    await state.set_state(AdminStates.waiting_brand_rename)
    await callback.message.edit_text(
        f"✏️ <b>{brand['name']}</b> uchun yangi nom kiriting:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_brand_rename, F.text)
async def mng_brand_rename_save(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Nom 2-50 belgi bo'lishi kerak.")
        return
    data = await state.get_data()
    ok = await db.rename_brand(data['brand_id'], name)
    await state.clear()
    if ok:
        await message.answer(
            f"✅ Brend nomi o'zgartirildi: <b>{name}</b>",
            parse_mode="HTML", reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            f"❌ <b>{name}</b> nomi band yoki xato. Boshqa nom tanlang.",
            parse_mode="HTML", reply_markup=get_admin_menu()
        )


@router.callback_query(F.data.startswith("mngbdel_"))
async def mng_brand_delete_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    cnt = await db.count_brand_children(brand_id)
    await callback.message.edit_text(
        f"🗑 <b>{brand['name']}</b> brendini o'chirasizmi?\n\n"
        f"⚠️ Bu bilan birga <b>{cnt['models']} ta model</b> va "
        f"<b>{cnt['products']} ta mahsulot</b> ham o'chadi!\n"
        f"Buni ortga qaytarib bo'lmaydi.",
        parse_mode="HTML", reply_markup=get_brand_delete_confirm_kb(brand_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngbdy_"))
async def mng_brand_delete_yes(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    name = brand['name'] if brand else "?"
    await db.delete_brand(brand_id)
    brands = await db.get_brands()
    if brands:
        await callback.message.edit_text(
            f"🗑 <b>{name}</b> o'chirildi.\n\n🗂 Qolgan brendlar:",
            parse_mode="HTML", reply_markup=get_manage_brands_kb(brands)
        )
    else:
        await callback.message.edit_text(
            f"🗑 <b>{name}</b> o'chirildi. Boshqa brend qolmadi.",
            parse_mode="HTML"
        )
    await callback.answer("O'chirildi")


@router.callback_query(F.data.startswith("mngml_"))
async def mng_models_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    brand_id = int(callback.data.split("_")[1])
    brand = await db.get_brand(brand_id)
    models = await db.get_all_models_of_brand(brand_id)
    if not models:
        await callback.message.edit_text(
            f"📂 <b>{brand['name']}</b> da model yo'q.",
            parse_mode="HTML", reply_markup=get_brand_manage_kb(brand_id)
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"📂 <b>{brand['name']}</b> modellari:\n\nBoshqarish uchun tanlang:",
        parse_mode="HTML", reply_markup=get_manage_models_kb(models, brand_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngm_"))
async def mng_model_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split("_")[1])
    model = await db.get_model(model_id)
    if not model:
        await callback.answer("Model topilmadi", show_alert=True)
        return
    pcount = await db.count_model_products(model_id)
    await callback.message.edit_text(
        f"📱 <b>{model['brand_name']} {model['name']}</b>\n\n"
        f"📦 Mahsulotlar: {pcount} ta\n\nAmalni tanlang:",
        parse_mode="HTML", reply_markup=get_model_manage_kb(model_id, model['brand_id'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngmren_"))
async def mng_model_rename_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split("_")[1])
    model = await db.get_model(model_id)
    await state.update_data(model_id=model_id)
    await state.set_state(AdminStates.waiting_model_rename)
    await callback.message.edit_text(
        f"✏️ <b>{model['brand_name']} {model['name']}</b> uchun yangi model nomi:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_model_rename, F.text)
async def mng_model_rename_save(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await message.answer("❌ Nom 1-50 belgi bo'lishi kerak.")
        return
    data = await state.get_data()
    ok = await db.rename_model(data['model_id'], name)
    await state.clear()
    if ok:
        await message.answer(
            f"✅ Model nomi o'zgartirildi: <b>{name}</b>",
            parse_mode="HTML", reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            f"❌ <b>{name}</b> nomi shu brendda band. Boshqa nom tanlang.",
            parse_mode="HTML", reply_markup=get_admin_menu()
        )


@router.callback_query(F.data.startswith("mngmdel_"))
async def mng_model_delete_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split("_")[1])
    model = await db.get_model(model_id)
    pcount = await db.count_model_products(model_id)
    await callback.message.edit_text(
        f"🗑 <b>{model['brand_name']} {model['name']}</b> modelini o'chirasizmi?\n\n"
        f"⚠️ Bu bilan <b>{pcount} ta mahsulot</b> ham o'chadi!\n"
        f"Ortga qaytarib bo'lmaydi.",
        parse_mode="HTML", reply_markup=get_model_delete_confirm_kb(model_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mngmdy_"))
async def mng_model_delete_yes(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split("_")[1])
    model = await db.get_model(model_id)
    brand_id = model['brand_id'] if model else None
    name = f"{model['brand_name']} {model['name']}" if model else "?"
    await db.delete_model(model_id)
    if brand_id:
        brand = await db.get_brand(brand_id)
        models = await db.get_all_models_of_brand(brand_id)
        if models:
            await callback.message.edit_text(
                f"🗑 <b>{name}</b> o'chirildi.\n\n📂 {brand['name']} qolgan modellari:",
                parse_mode="HTML", reply_markup=get_manage_models_kb(models, brand_id)
            )
        else:
            await callback.message.edit_text(
                f"🗑 <b>{name}</b> o'chirildi. Bu brendda model qolmadi.",
                parse_mode="HTML", reply_markup=get_brand_manage_kb(brand_id)
            )
    else:
        await callback.message.edit_text(f"🗑 <b>{name}</b> o'chirildi.", parse_mode="HTML")
    await callback.answer("O'chirildi")


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
    payment_names = {"naqd": "💵 Naqd", "plastik": "💳 Plastik"}
    pickup_names = {"shop": "🏪 Do'kondan", "delivery": "🚚 Yetkazib berish"}
    pstatus_names = {"paid": "✅", "debt": "📒", "partial": "💰"}

    for o in orders[:10]:
        product_title = o.get('product_name', '?')
        if o.get('brand_name') and o.get('model_name'):
            product_title = f"{o['brand_name']} {o['model_name']} — {product_title}"
        ps = pstatus_names.get(o.get('payment_status'), '')
        text += (
            f"📦 <b>Buyurtma #{o['id']}</b> {ps}\n"
            f"👤 {o['full_name']} | {o['phone']}\n"
            f"{o.get('category_icon','📦')} {product_title}\n"
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
        product_title = order.get('product_name', '?')
        if order.get('brand_name') and order.get('model_name'):
            product_title = f"{order['brand_name']} {order['model_name']} — {product_title}"
        await bot.send_message(
            order['telegram_id'],
            f"✅ <b>Buyurtmangiz tasdiqlandi!</b>\n\n"
            f"🆔 #{order_id}\n"
            f"{order.get('category_icon','📦')} {product_title}\n"
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
    if order.get('product_id'):
        product = await db.get_product(order['product_id'])
        if product:
            await db.update_product_quantity(
                order['product_id'], product['quantity'] + order['quantity']
            )

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


# ============ BACKUP / RESTORE ============

@router.message(F.text == "💾 Backup")
async def backup_db(message: Message, bot: Bot):
    """Bazani .db fayl sifatida adminning Telegram'iga yuboradi."""
    if not is_admin(message.from_user.id):
        return

    if not os.path.exists(db.DB_NAME):
        await message.answer("❌ Baza fayli topilmadi.")
        return

    ts = uz_now().strftime("%Y%m%d_%H%M")
    await message.answer_document(
        FSInputFile(db.DB_NAME, filename=f"shop_backup_{ts}.db"),
        caption=(
            f"💾 <b>Baza zaxira nusxasi</b>\n"
            f"📅 {uz_now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⚠️ Bu faylni saqlab qo'ying! Boshqa serverga ko'chganda yoki "
            f"baza buzilganda <b>♻️ Restore</b> orqali shu fayldan tiklaysiz."
        ),
        parse_mode="HTML"
    )


@router.message(F.text == "♻️ Restore")
async def restore_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_restore_file)
    await message.answer(
        "♻️ <b>Bazani tiklash</b>\n\n"
        "⚠️ <b>Diqqat:</b> hozirgi baza to'liq almashtiriladi "
        "(barcha hozirgi ma'lumotlar backup bilan almashadi)!\n\n"
        "Backup <code>.db</code> faylni shu yerga yuboring.\n"
        "Bekor qilish uchun: /admin",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_restore_file, F.document)
async def restore_file(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    doc = message.document
    if not doc.file_name.lower().endswith(".db"):
        await message.answer("❌ Faqat <code>.db</code> fayl yuboring.", parse_mode="HTML")
        return

    # Vaqtinchalik faylga yuklab olamiz (xuddi shu papkada — atomik almashtirish uchun)
    tmp_path = db.DB_NAME + ".restore_tmp"
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=tmp_path)
    except Exception as e:
        await message.answer(f"❌ Faylni yuklab bo'lmadi: {e}")
        return

    # Yuklangan fayl haqiqiy SQLite bazasimi — tekshiramiz
    try:
        async with aiosqlite.connect(tmp_path) as testdb:
            cursor = await testdb.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [r[0] for r in await cursor.fetchall()]
        if "users" not in tables or "products" not in tables:
            raise ValueError("kerakli jadvallar topilmadi")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        await message.answer(
            f"❌ Yaroqsiz baza fayli: {e}\n\nTo'g'ri backup faylni yuboring.",
            parse_mode="HTML"
        )
        return

    # Almashtiramiz va migratsiyani qo'llaymiz
    try:
        os.replace(tmp_path, db.DB_NAME)
        await db.init_db()  # eski backup bo'lsa ham sxemani yangilaydi
    except Exception as e:
        await message.answer(f"❌ Tiklashda xato: {e}")
        return

    await state.clear()
    stats = await db.get_statistics()
    await message.answer(
        f"✅ <b>Baza muvaffaqiyatli tiklandi!</b>\n\n"
        f"👥 Ustalar: {stats['total_users']}\n"
        f"📦 Mahsulotlar: {stats['total_products']}\n"
        f"🛒 Buyurtmalar: {stats['total_orders']}\n"
        f"💳 Qarz: {int(stats['total_debt']):,} so'm",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@router.message(AdminStates.waiting_restore_file)
async def restore_wrong_input(message: Message):
    """Restore kutilayotganda fayl emas, boshqa narsa yuborilsa."""
    await message.answer(
        "📎 Iltimos, backup <code>.db</code> faylni yuboring "
        "(matn emas, fayl sifatida).\nBekor qilish: /admin",
        parse_mode="HTML"
    )


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
