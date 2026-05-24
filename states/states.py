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
    selecting_quantity = State()
    selecting_payment = State()
    selecting_pickup = State()
    confirming = State()


class AdminStates(StatesGroup):
    """Admin paneli holatlari"""
    # Brend
    waiting_brand_name = State()
    
    # Model
    waiting_model_name = State()
    selecting_brand_for_model = State()
    
    # Ekran
    selecting_brand_for_screen = State()
    selecting_model_for_screen = State()
    waiting_screen_type = State()
    waiting_screen_price = State()
    waiting_screen_quantity = State()
    waiting_screen_description = State()
    
    # Yangilash
    waiting_new_price = State()
    waiting_new_quantity = State()
