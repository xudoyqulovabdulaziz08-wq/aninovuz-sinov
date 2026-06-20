from aiogram import Router, html, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger

router = Router()

@router.callback_query(lambda c: c.data == "advertise")
async def advertise_menu(callback: CallbackQuery):
    await callback.answer()
    
    # 🖼 Reklama bo'limi uchun rasm (Startdagi rasmni qoldirdik, o'zgartirmoqchi bo'lsangiz yangi file_id qo'yasiz)
    advertise_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
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
            [InlineKeyboardButton(text="📢 Reklama berish", callback_data="advertise_submit", style="primary")],
            [InlineKeyboardButton(text="💰 Reklama narxlari", callback_data="advertise_prices", style="primary")],
            [InlineKeyboardButton(text="📜 Reklama shartlari", callback_data="advertise_terms", style="primary")],
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
    except Exception as e:
        logger.error(f"❌ Reklama menyusini yuborishda xatolik: {e}")
        await callback.message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")