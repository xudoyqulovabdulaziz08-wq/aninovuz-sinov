from aiogram import Router, html, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger

router = Router()

@router.callback_query(lambda c: c.data == "advertise")
async def advertise_menu(callback: CallbackQuery):
    await callback.answer()
    
    # 🖼 Reklama bo'limi uchun rasm (Startdagi rasmni qoldirdik, o'zgartirmoqchi bo'lsangiz yangi file_id qo'yasiz)
    advertise_image_file_id = "AgACAgIAAxkBAAI8rWo2yOOJrbYjf6oN-0buXgcqrr91AAJqGWsbZ6WxSdfP89-yJYeKAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 📢 ═════════╗\n"
        "   <b>REKLAMA BO'LIMI</b>\n"
        "╚═════════ 📢 ═════════╝\n\n"
        "Reklama bo'limiga xush kelibsiz! 🌟\n\n"
        "<blockquote expandable><b>Reklama berish</b></blockquote>\n"
        "<blockquote expandable><b>Reklama narxlari</b></blockquote>\n"
        "<blockquote expandable><b>Reklama shartlari</b></blockquote>\n"
        
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Reklama berish", callback_data="advertise_submit")],
            
            # ⬇️ "Orqaga" tugmasi start.py faylidagi 'back_to_start' handleriga ulandi!
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_start", style="danger")]
        ]
    )
    
    try:
        # Matn o'rniga Media va Klaviatura birga chiroyli edit bo'ladi
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=advertise_image_file_id,
                caption=text,
                parse_mode="HTML"
            ),
            reply_markup=kb
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
        # Agar xabar allaqachon o'zgargan bo'lsa, xato bermaymiz, shunchaki o'tkazib yuboramiz
            pass
        else:
            # Boshqa jiddiy xatolik bo'lsa logga yozamiz
            logger.error(f"❌ Kutilmagan xatolik: {e}")
    except Exception as e:
        logger.error(f"❌ Tizimda xatolik yuz berdi: {e}")








@router.callback_query(lambda c: c.data == "advertise_submit")
async def advertise_submit(callback: CallbackQuery):
    await callback.answer()
    advertise_image_file_id = "AgACAgIAAxkBAAI8rWo2yOOJrbYjf6oN-0buXgcqrr91AAJqGWsbZ6WxSdfP89-yJYeKAQADAgADdwADPAQ"

    text = (
        "╔═════════ 📢 ═════════╗\n"
        "   <b>REKLAMA BERISH</b>\n"
        "╚═════════ 📢 ═════════╝\n\n"
        "Reklama berish bo'limiga xush kelibsiz! 🌟\n\n"
        "<blockquote expandable> Agar siz botimizda reklama berishni xohlasangiz, iltimos, quyidagi tugmani bosing va biz bilan bog'laning. </blockquote>\n"
        "<b>🛑 Reklama berish shartlari</b>\n"
        "<blockquote expandable> 1️⃣ Reklama 18+ kontentni o'z ichiga olmasligi kerak.</blockquote>\n"
        "<blockquote expandable> 2️⃣ Qimor, noqonuniy faoliyat yoki zararli dasturlarni targ'ib qilmasligi kerak.</blockquote>\n"
        "<blockquote expandable> 3️⃣ Reklama mazmuni foydalanuvchilarni aldaydigan yoki zarar etkazadigan bo'lmasligi kerak.</blockquote>\n"
        "<blockquote expandable> 4️⃣ Reklama mazmuni Telegramning xizmat ko'rsatish shartlariga zid bo'lmasligi kerak.</blockquote>\n"
        "<blockquote expandable> 5️⃣ Reklama mazmuni boshqa foydalanuvchilarni tahqirlash yoki kamsitish bo'lmasligi kerak.</blockquote>\n"
    )

    url_admin = "https://t.me/Khudoyqulov_pg"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗Bog'lanish", url=url_admin, style="success")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="advertise", style="danger")]
        ]

    )
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=advertise_image_file_id,
                caption=text,
                parse_mode="HTML"
            ),
            reply_markup=kb
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
        # Agar xabar allaqachon o'zgargan bo'lsa, xato bermaymiz, shunchaki o'tkazib yuboramiz
            pass
        else:
            # Boshqa jiddiy xatolik bo'lsa logga yozamiz
            logger.error(f"❌ Kutilmagan xatolik: {e}")
