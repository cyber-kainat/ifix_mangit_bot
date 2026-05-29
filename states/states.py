"""
FSM (Finite State Machine) holatlari - foydalanuvchi dialoglarini boshqarish
"""
from aiogram.fsm.state import State, StatesGroup


class RegisterStates(StatesGroup):
    """Ro'yxatdan o'tish holatlari"""
    waiting_for_name = State()
    waiting_for_phone = State()


class OrderStates(StatesGroup):
    """Buyurtma berish holatlari"""
    selecting_category = State()
    selecting_brand = State()
    selecting_model = State()
    selecting_product = State()
    selecting_quantity = State()
    selecting_payment = State()
    selecting_pickup = State()
    selecting_payment_status = State()   # to'liq / qarz / qisman
    waiting_partial_amount = State()     # qisman to'lov summasi
    confirming = State()


class AdminStates(StatesGroup):
    """Admin paneli holatlari"""
    # Brend
    waiting_brand_name = State()

    # Model
    waiting_model_name = State()
    selecting_brand_for_model = State()

    # Mahsulot qo'shish (universal — har qanday kategoriya uchun)
    selecting_category_for_product = State()
    selecting_brand_for_product = State()
    selecting_model_for_product = State()
    waiting_product_name = State()         # masalan "OLED Original", "Original Krishka"
    waiting_product_cost = State()         # tannarx
    waiting_product_price = State()        # sotish narxi
    waiting_product_quantity = State()
    waiting_product_min_qty = State()
    waiting_product_description = State()

    # Mahsulotni tahrirlash
    waiting_new_price = State()
    waiting_new_cost = State()
    waiting_new_quantity = State()
    waiting_new_min_qty = State()

    # Bazani tiklash (restore)
    waiting_restore_file = State()


class SalesReportStates(StatesGroup):
    """Sotuv hisoboti uchun sana oralig'i"""
    waiting_date_from = State()
    waiting_date_to = State()


class DebtStates(StatesGroup):
    """Qarz to'lash"""
    waiting_payment_amount = State()
