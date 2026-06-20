from aiogram import Router, html, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger

router = Router()


@router.callback_query(lambda c: c.data == "guide")
async def guide_menu(callback: CallbackQuery):
    await callback.answer()
    
    # 🖼 Qo'llanma bo'limi uchun rasm (Startdagi rasmni qoldirdik, o'zgartirmoqchi bo'lsangiz yangi file_id qo'yasiz)
    guide_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
    welcome_text = (
        "╔═════════ 📚 ═════════╗\n"
        "   <b>FOYDALANISH QO'LLANMASI</b>\n"
        "╚═════════ 📚 ═════════╝\n\n"
        "Salom! Bu yerda botimizning barcha imkoniyatlari va funksiyalaridan qanday foydalanishni o'rganishingiz mumkin. 🌟\n\n"
        "<b>1️⃣ Asosiy menyu</b>\n"
        "<blockquote expandable>Asosiy menyuda siz qidiruv, reklama, VIP va boshqa bo'limlarga kirishingiz mumkin. Har bir bo'limda o'ziga xos imkoniyatlar mavjud.</blockquote>\n\n"
        "<b>2️⃣ Qidiruv</b>\n"
        "<blockquote expandable>Qidiruv bo'limida siz animelarni nomi, ID raqami yoki janri bo'yicha qidirishingiz mumkin. Har bir qidiruv turi sizga kerakli natijalarni tezda topishga yordam beradi.</blockquote>\n\n"
        "<b>3️⃣ Vip olish</b>\n"
        "<blockquote expandable>VIP bo'limida siz maxsus imtiyozlar va bonuslarga ega bo'lishingiz mumkin. VIP foydalanuvchilarimizga doimiy ravishda yangi imkoniyatlar qo'shib boramiz!</blockquote>\n\n"
        "<b>4️⃣ Yordam markazi</b>\n\n"
        "<blockquote expandable>Har bir bo'limda sizga kerakli ma'lumotlar va amallar mavjud. Agar biror narsani tushunmasangiz yoki yordam kerak bo'lsa, pastdagi tugmani bosib biz bilan bog'laning!</blockquote>"
    
        "Har bir bo'limda sizga kerakli ma'lumotlar va amallar mavjud. Agar biror narsani tushunmasangiz yoki yordam kerak bo'lsa, pastdagi tugmani bosib biz bilan bog'laning!"
    )
    
    guide_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_start", style="danger")],
            [InlineKeyboardButton(text="💬 Aloqa", callback_data="support", style="primary")]
        ]
    )
    try:
        # Matn o'rniga Media va Klaviatura birga chiroyli edit bo'ladi
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=guide_image_file_id,
                caption=welcome_text,
                parse_mode="HTML"
            ),
            reply_markup=guide_keyboard
        )
    except Exception as e:
        logger.error(f"❌ Qo'llanma menyusini yuborishda xatolik: {e}")
        await callback.message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")