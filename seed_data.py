"""
Test ma'lumotlarni bazaga to'ldirish skripti.
Botni birinchi marta ishga tushirgandan keyin bir marta ishlatiladi.

Ishga tushirish:
    python seed_data.py
"""
import asyncio
from database.db import init_db, add_brand, add_model, add_screen, get_brands, get_models


async def seed():
    await init_db()
    print("🌱 Test ma'lumotlar qo'shilmoqda...\n")
    
    # Brendlar
    brands_data = ["iPhone", "Samsung", "Xiaomi", "Huawei", "Oppo", "Realme"]
    brand_ids = {}
    for name in brands_data:
        bid = await add_brand(name)
        brands = await get_brands()
        for b in brands:
            if b['name'] == name:
                brand_ids[name] = b['id']
                break
        print(f"✅ Brend: {name}")
    
    # iPhone modellari va ekranlari
    iphone_models = {
        "11": [("OLED Original", 850000, 15), ("OLED Copy", 450000, 30), ("IPS Copy", 280000, 50)],
        "12": [("OLED Original", 1100000, 10), ("OLED Copy", 600000, 25), ("IPS Copy", 350000, 40)],
        "13": [("Super Retina OLED Original", 1500000, 8), ("OLED Copy", 750000, 20), ("IPS Copy", 420000, 35)],
        "14": [("Super Retina OLED Original", 1800000, 5), ("OLED Copy", 900000, 15), ("IPS Copy", 500000, 25)],
        "15 Pro": [("Super Retina XDR Original", 2500000, 3), ("OLED Copy", 1200000, 10)],
        "15 Pro Max": [("Super Retina XDR Original", 2900000, 2), ("OLED Copy", 1400000, 8)],
    }
    
    for model_name, screens in iphone_models.items():
        await add_model(brand_ids["iPhone"], model_name)
        models = await get_models(brand_ids["iPhone"])
        model_id = next(m['id'] for m in models if m['name'] == model_name)
        for s_type, price, qty in screens:
            await add_screen(model_id, s_type, price, qty, f"iPhone {model_name} uchun {s_type} ekran")
        print(f"✅ iPhone {model_name} - {len(screens)} ta ekran")
    
    # Samsung modellari
    samsung_models = {
        "Galaxy A52": [("AMOLED Original", 650000, 12), ("AMOLED Copy", 380000, 25), ("IPS Copy", 220000, 40)],
        "Galaxy S22": [("Dynamic AMOLED Original", 1200000, 7), ("AMOLED Copy", 580000, 18)],
        "Galaxy S23 Ultra": [("Dynamic AMOLED 2X Original", 1900000, 4), ("AMOLED Copy", 850000, 12)],
        "Galaxy A54": [("Super AMOLED Original", 720000, 10), ("AMOLED Copy", 420000, 22)],
        "Galaxy Note 20": [("Dynamic AMOLED Original", 1350000, 6), ("AMOLED Copy", 650000, 14)],
    }
    
    for model_name, screens in samsung_models.items():
        await add_model(brand_ids["Samsung"], model_name)
        models = await get_models(brand_ids["Samsung"])
        model_id = next(m['id'] for m in models if m['name'] == model_name)
        for s_type, price, qty in screens:
            await add_screen(model_id, s_type, price, qty, "")
        print(f"✅ Samsung {model_name} - {len(screens)} ta ekran")
    
    # Xiaomi modellari
    xiaomi_models = {
        "Redmi Note 11": [("AMOLED Original", 450000, 15), ("AMOLED Copy", 280000, 30), ("IPS Copy", 180000, 50)],
        "Redmi Note 12 Pro": [("AMOLED Original", 580000, 10), ("AMOLED Copy", 340000, 25)],
        "Redmi Note 13": [("AMOLED Original", 650000, 8), ("AMOLED Copy", 380000, 20)],
        "Mi 11": [("AMOLED Original", 780000, 6), ("AMOLED Copy", 450000, 15)],
        "Poco X5": [("AMOLED Original", 520000, 12), ("AMOLED Copy", 310000, 22)],
    }
    
    for model_name, screens in xiaomi_models.items():
        await add_model(brand_ids["Xiaomi"], model_name)
        models = await get_models(brand_ids["Xiaomi"])
        model_id = next(m['id'] for m in models if m['name'] == model_name)
        for s_type, price, qty in screens:
            await add_screen(model_id, s_type, price, qty, "")
        print(f"✅ Xiaomi {model_name} - {len(screens)} ta ekran")
    
    # Huawei modellari (qisqartirilgan)
    huawei_models = {
        "P30": [("OLED Original", 720000, 5), ("OLED Copy", 420000, 12)],
        "P40 Pro": [("OLED Original", 950000, 4), ("OLED Copy", 560000, 10)],
        "Nova 9": [("OLED Original", 580000, 8), ("OLED Copy", 340000, 15)],
    }
    
    for model_name, screens in huawei_models.items():
        await add_model(brand_ids["Huawei"], model_name)
        models = await get_models(brand_ids["Huawei"])
        model_id = next(m['id'] for m in models if m['name'] == model_name)
        for s_type, price, qty in screens:
            await add_screen(model_id, s_type, price, qty, "")
        print(f"✅ Huawei {model_name} - {len(screens)} ta ekran")
    
    print("\n🎉 Test ma'lumotlar muvaffaqiyatli qo'shildi!")


if __name__ == "__main__":
    asyncio.run(seed())
