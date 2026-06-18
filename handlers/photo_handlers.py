"""
Admin: mahsulotga rasm qo'yish — /rasm
Admin ID raqamni yuboradi, keyin rasmni yuboradi. Rasm Telegram'da qoladi,
backend uni /tgphoto/<file_id> orqali ilovaga ko'rsatadi (alohida ombor shart emas).
"""
import os
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
