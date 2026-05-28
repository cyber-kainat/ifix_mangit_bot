# 📱 Telefon Ekranlari Do'koni - Telegram Bot

Telefon servis ustalari uchun ekran buyurtma qilish boti. Adminlar mahsulotlarni boshqaradi, ustalar bot orqali xarid qilishadi.

## 🎯 Imkoniyatlar

### Ustalar uchun:
- ✅ Ism va telefon orqali ro'yxatdan o'tish
- ✅ Admin tasdig'ini kutish
- ✅ **Kategoriya** → Brend → Model → Mahsulot bo'yicha katalog
- ✅ Mahsulot turlari: **Ekran, Orqa krishka, Batareya, Kamera shisha, Pastki plata, Aksessuar**
- ✅ Miqdorni tanlab buyurtma berish
- ✅ 3 xil to'lov: Naqd, Click, Payme
- ✅ **To'liq / Qarz / Qisman to'lov** tanlash
- ✅ Do'kondan olib ketish yoki yetkazib berish
- ✅ Buyurtmalar tarixi va o'z qarzlarini ko'rish

### Adminlar uchun:
- 👑 To'liq statistika (ustalar, mahsulotlar, sotuvlar, qarzlar)
- 💰 **Sotuv bo'limi** — sana oralig'i bo'yicha foyda/zarar hisoboti (Excel eksport)
- 💳 **Qarzlar** — har bir ustaning qarzini ko'rish va to'lov qabul qilish
- 📉 **Tugab qolayotgan mahsulotlar** — Toshkentdan zakaz uchun Excel ro'yxat
- 👥 Ustalarni tasdiqlash/bloklash, qarzlarini ko'rish
- 📦 Kategoriya bo'yicha mahsulot qo'shish (tannarx + sotish narxi)
- 💰 Narx, tannarx, miqdor va minimum miqdorni yangilash
- 🛍 Buyurtmalarni boshqarish (tasdiqlash, bekor qilish, yakunlash)
- 🔔 Yangi buyurtma va ro'yxatdan o'tish haqida xabarnomalar

## 🛠 Texnologiyalar

- **Python 3.10+** - dasturlash tili
- **aiogram 3.13** - eng tezkor Telegram Bot framework
- **SQLite + aiosqlite** - asinxron ma'lumotlar bazasi
- **FSM** - dialoglarni boshqarish uchun
- **openpyxl** - Excel hisobotlar uchun

## 📦 O'rnatish

### 1. Kerakli kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 2. Bot tokenini olish

[@BotFather](https://t.me/BotFather) ga `/newbot` buyrug'ini yuboring va botingiz tokenini oling.

### 3. Konfiguratsiya

`config.py` faylini oching va sozlang:

```python
BOT_TOKEN = "siz_olgan_token_shu_yerga"

# Admin Telegram ID raqamlari (@userinfobot dan oling)
admin_str = os.getenv("ADMIN_IDS", "123456789")  # O'z ID raqamingizni qo'ying

# To'lov kartalari
CLICK_CARD = "8600 1234 5678 9012"
PAYME_CARD = "8600 9876 5432 1098"

# Do'kon ma'lumotlari
SHOP_ADDRESS = "Toshkent sh., ..."
SHOP_PHONE = "+998 90 123 45 67"
```

**Yoki environment variable orqali:**
```bash
export BOT_TOKEN="your_token"
export ADMIN_IDS="123456789,987654321"
```

### 4. Test ma'lumotlarini yuklash (ixtiyoriy)

Bazani iPhone, Samsung, Xiaomi va boshqa brendlar bilan to'ldirish:

```bash
python seed_data.py
```

### 5. Botni ishga tushirish

```bash
python main.py
```

## 📂 Loyiha tuzilishi

```
telegram_bot/
├── main.py                  # Asosiy ishga tushirish fayli
├── config.py                # Sozlamalar (token, admin, kartalar)
├── seed_data.py             # Test ma'lumotlarini yuklash
├── requirements.txt         # Kutubxonalar
├── shop.db                  # SQLite baza (avtomatik yaratiladi)
│
├── database/
│   └── db.py                # Barcha DB funksiyalari
│
├── handlers/
│   ├── user_handlers.py     # /start, ro'yxat
│   ├── catalog_handlers.py  # Katalog va buyurtma
│   └── admin_handlers.py    # Admin paneli
│
├── keyboards/
│   ├── user_kb.py           # Foydalanuvchi tugmalari
│   └── admin_kb.py          # Admin tugmalari
│
└── states/
    └── states.py            # FSM holatlari
```

## 🚀 Foydalanish

### Birinchi ishga tushganda:

1. `/start` - Yangi usta ro'yxatdan o'tadi
2. Admin xabar oladi va tasdiqlaydi
3. Usta katalogni ko'rib, buyurtma beradi

### Admin buyruqlari:

- `/admin` - Admin panelni ochish
- 📊 **Statistika** - umumiy ko'rsatkichlar
- 👥 **Ustalar** - foydalanuvchilarni boshqarish
- 📦 **Mahsulotlar** - brend/model/ekran qo'shish va tahrirlash
- 🛍 **Buyurtmalar** - kutilayotgan buyurtmalar

### Mahsulot qo'shish tartibi:

1. **Brend qo'shish** (iPhone, Samsung...)
2. **Model qo'shish** (15 Pro Max, S24 Ultra...)
3. **Ekran qo'shish** (turi: OLED/IPS/AMOLED, narxi, miqdori)

## 🗄 Ma'lumotlar bazasi tuzilishi

- **users** - ustalar (ID, ism, telefon, tasdiq/blok holati)
- **brands** - brendlar (iPhone, Samsung...)
- **models** - modellar (har bir brendga bog'langan)
- **categories** - kategoriyalar (Ekran, Krishka, Batareya, Kamera shisha, Pastki plata, Aksessuar)
- **products** - mahsulotlar (kategoriya, model, tannarx, sotish narxi, miqdor, min_quantity)
- **orders** - buyurtmalar (mijoz, mahsulot, to'lov, qarz, holat, tannarx)
- **screens** - eski jadval (legacy; products ga migratsiya qilingan)

## 📊 Yangi imkoniyatlar (v2)

### 💰 Sotuv hisoboti
Admin panelida **💰 Sotuv** tugmasi bosib, sana oralig'ini tanlang:
- Bugun, Kecha, Bu hafta, Bu oy, O'tgan oy, 3 oy yoki maxsus oraliq
- Hisobot: Tushum, Tannarx, **Foyda/Zarar**, Marja %
- Excel formatda yuklab olish (3 ta varaq: umumiy, kategoriya, buyurtmalar)

### 💳 Qarz tizimi
- Buyurtma berishda usta **To'liq / Qarz / Qisman** to'lov tanlashi mumkin
- Admin har bir qarzdor ustani ko'radi (jami qarz miqdori bilan)
- Qisman to'lov qabul qilish yoki barcha qarzni "to'langan" deb belgilash
- Usta o'z qarzini "💳 Qarzlarim" tugmasi orqali ko'radi

### 📉 Tugab qolayotganlar (Toshkentdan zakaz uchun)
- Admin panelida **📉 Tugab qolganlar** tugmasi
- `quantity <= min_quantity` bo'lgan barcha mahsulotlar
- Kategoriya bo'yicha filter
- **Excel eksport**: 0 dona qizil rang, oz qolganlar sariq rang
- Toshkentdan Amudaryo tumani Mangit shahriga zakaz qilish uchun qulay ro'yxat

### 🧰 Yangi kategoriyalar
- 📱 Ekran (mavjud edi)
- 🪞 Orqa krishka (yangi)
- 🔋 Batareya (yangi)
- 📷 Kamera shisha (yangi)
- 🔌 Pastki plata (yangi)
- 🧰 Aksessuar (brend/modelsiz — universal mahsulotlar)

## ⚡ Performance

- **Asinxron** kod (asyncio) - bir vaqtda yuzlab so'rovlarni eplay oladi
- **SQLite indekslar** - tez qidiruv
- **MemoryStorage FSM** - lightning-tezkor dialoglar
- **Bitta jarayonda 1000+ ustaga xizmat ko'rsata oladi**

## 🔒 Xavfsizlik

- Admin huquqlari `ADMIN_IDS` orqali tekshiriladi
- Bloklangan foydalanuvchilar xarid qila olmaydi
- Tasdiqlanmagan ustalar faqat /start ko'ra oladi
- Buyurtma yaratilganda mahsulot mavjudligi qayta tekshiriladi

## 📞 Yordam

Savollar bo'lsa, kod ichidagi izohlarni o'qing. Har bir funksiya tushuntirilgan.

---

**Muvaffaqiyatli ishlatish!** 🚀
