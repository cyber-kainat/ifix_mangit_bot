"""
Admin: mahsulotga rasm qo'yish — /rasm
Admin ID raqamni yuboradi, keyin rasmni yuboradi. Rasm Telegram'da qoladi,
backend uni /tgphoto/<file_id> orqali ilovaga ko'rsatadi (alohida ombor shart emas).
"""
import os
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import config

router = Router()


class PhotoStates(StatesGroup):
    waiting_id = State()
    waiting_photo = State()


def _is_admin(uid: int) -> bool:
    return uid in getattr(config, "ADMIN_IDS", [])


@router.message(Command("rasm"))
async def rasm_start(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(PhotoStates.waiting_id)
    await message.answer(
        "📷 Qaysi mahsulotga rasm qo'yamiz?\n"
        "Mahsulot <b>ID</b> raqamini yuboring (ilovada \"ID: ...\" ko'rinadi):",
        parse_mode="HTML")


@router.message(PhotoStates.waiting_id, F.text)
async def rasm_id(message: Message, state: FSMContext):
    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("Iltimos, faqat raqam yuboring (mahsulot ID).")
        return
    await state.update_data(pid=int(txt))
    await state.set_state(PhotoStates.waiting_photo)
    await message.answer("✅ Endi <b>rasmni</b> yuboring:", parse_mode="HTML")


@router.message(PhotoStates.waiting_photo, F.photo)
async def rasm_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("pid")
    file_id = message.photo[-1].file_id
    backend = os.getenv("BACKEND_URL", "").rstrip("/")
    url = f"{backend}/tgphoto/{file_id}"
    ok = await db.set_product_image(pid, url)
    await state.clear()
    await message.answer(
        f"✅ {pid}-mahsulotga rasm qo'yildi! Ilovada ko'rinadi."
        if ok else "❌ Bunday ID li mahsulot topilmadi.")


@router.message(PhotoStates.waiting_photo)
async def rasm_not_photo(message: Message):
    await message.answer("Iltimos, rasm yuboring (yoki /rasm bilan qaytadan boshlang).")


# ============ CHEGIRMA ============

class DiscountStates(StatesGroup):
    waiting_id = State()
    waiting_percent = State()
    waiting_days = State()


@router.message(Command("chegirma"))
async def disc_start(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(DiscountStates.waiting_id)
    await message.answer("💸 Qaysi mahsulotga chegirma? Mahsulot <b>ID</b> raqamini yuboring:",
                         parse_mode="HTML")


@router.message(DiscountStates.waiting_id, F.text)
async def disc_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Raqam yuboring.")
        return
    pid = int(message.text.strip())
    p = await db.get_product(pid)
    if not p:
        await state.clear()
        await message.answer("❌ Bunday ID topilmadi. Qaytadan /chegirma")
        return
    await state.update_data(pid=pid, price=float(p['price']))
    await state.set_state(DiscountStates.waiting_percent)
    await message.answer(
        f"Mahsulot narxi: {int(p['price'])} so'm.\nChegirma <b>foizini</b> yuboring (masalan 9):",
        parse_mode="HTML")


@router.message(DiscountStates.waiting_percent, F.text)
async def disc_percent(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isdigit() or not (1 <= int(t) <= 99):
        await message.answer("1-99 oralig'ida raqam yuboring.")
        return
    await state.update_data(percent=int(t))
    await state.set_state(DiscountStates.waiting_days)
    await message.answer("Necha <b>kun</b> davom etsin? (masalan 12). 0 = muddatsiz:",
                         parse_mode="HTML")


@router.message(DiscountStates.waiting_days, F.text)
async def disc_days(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isdigit():
        await message.answer("Raqam yuboring (0 = muddatsiz).")
        return
    days = int(t)
    data = await state.get_data()
    old = float(data['price'])
    percent = data['percent']
    new = round(old * (1 - percent / 100))
    until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d") if days > 0 else ""
    await db.set_product_discount(data['pid'], old, new, until)
    await state.clear()
    msg = (f"✅ {data['pid']}-mahsulotga {percent}% chegirma!\n"
           f"Eski narx: {int(old)} → yangi: {int(new)} so'm")
    if days > 0:
        msg += f"\n⏳ {days} kun davom etadi."
    await message.answer(msg)


@router.message(Command("chegirma_ochir"))
async def disc_clear(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /chegirma_ochir <mahsulot_ID>")
        return
    ok = await db.clear_product_discount(int(parts[1]))
    await message.answer("✅ Chegirma bekor qilindi (narx qaytdi)." if ok else "❌ Topilmadi.")


# ============ BANNER ============

class BannerStates(StatesGroup):
    waiting_photo = State()


@router.message(Command("banner"))
async def banner_start(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(BannerStates.waiting_photo)
    await message.answer("📢 Banner uchun <b>rasm</b> yuboring (bosh sahifada chiqadi):",
                         parse_mode="HTML")


@router.message(BannerStates.waiting_photo, F.photo)
async def banner_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    backend = os.getenv("BACKEND_URL", "").rstrip("/")
    bid = await db.add_banner(f"{backend}/tgphoto/{file_id}")
    await state.clear()
    await message.answer(
        f"✅ Banner qo'shildi (№{bid}). Bosh sahifada chiqadi.\nO'chirish: /banner_ochir {bid}")


@router.message(BannerStates.waiting_photo)
async def banner_not_photo(message: Message):
    await message.answer("Iltimos, rasm yuboring.")


@router.message(Command("bannerlar"))
async def banner_list(message: Message):
    if not _is_admin(message.from_user.id):
        return
    bs = await db.get_banners()
    if not bs:
        await message.answer("Banner yo'q. /banner bilan qo'shing.")
        return
    txt = "📢 <b>Bannerlar:</b>\n" + "\n".join(
        f"№{b['id']} — o'chirish: /banner_ochir {b['id']}" for b in bs)
    await message.answer(txt, parse_mode="HTML")


@router.message(Command("banner_ochir"))
async def banner_delete(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /banner_ochir <banner_ID>")
        return
    await db.delete_banner(int(parts[1]))
    await message.answer("✅ Banner o'chirildi.")


# ===== Aloqa / ijtimoiy tarmoq sozlamalari =====

async def _set_setting_cmd(message: Message, key: str, label: str):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        cur = (await db.get_settings()).get(key, "—")
        await message.answer(
            f"Hozirgi {label}: {cur}\n\n"
            f"O'zgartirish uchun yangi qiymatni yozing.\n"
            f"Masalan: {parts[0]} +998901234567")
        return
    await db.set_setting(key, parts[1].strip())
    await message.answer(f"✅ {label} yangilandi: {parts[1].strip()}")


@router.message(Command("aloqa"))
async def set_contact(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await _set_setting_cmd(message, "contact_phone", "aloqa telefoni")


@router.message(Command("telegram"))
async def set_telegram(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await _set_setting_cmd(message, "telegram_url", "Telegram havolasi")


@router.message(Command("instagram"))
async def set_instagram(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await _set_setting_cmd(message, "instagram_url", "Instagram havolasi")
