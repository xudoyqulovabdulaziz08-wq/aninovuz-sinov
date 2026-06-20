from aiogram import Router, html, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger

router = Router()


@router.callback_query(lambda c: c.data == "guide")
async def guide_menu(callback: CallbackQuery):
    await callback.answer()
    
    guide_image_file_id = "AgACAgIAAxkBAAI8r2o2yqRxEiN_ZhKFQPu58i9D0s13AAJyGWsbZ6WxSZJ088Ot-5S2AQADAgADdwADPAQ"
    
    welcome_text = (
        "╔═════════ 📚 ═════════╗\n"
        "   <b>FOYDALANISH QO'LLANMASI</b>\n"
        "╚═════════ 📚 ═════════╝\n\n"
        "Bot imkoniyatlaridan to'g'ri foydalanish bo'yicha qisqacha yo'riqnoma: 🌟\n\n"
        "<b>1️⃣ Asosiy menyu</b>\n"
        "<blockquote expandable>Bu yerda qidiruv, reklama, VIP va aloqa bo'limlari mavjud. Har bir bo'lim loyihadan to'liq foydalanish imkonini beradi.</blockquote>\n\n"
        "<b>2️⃣ Qidiruv tizimi</b>\n"
        "<blockquote expandable>Animelarni nomi, maxsus ID raqami yoki sevimli janrlaringiz bo'yicha tez va oson qidirib topishingiz mumkin.</blockquote>\n\n"
        "<b>3️⃣ VIP imtiyozlar</b>\n"
        "<blockquote expandable>VIP bo'lim orqali maxsus statusga ega bo'ling hamda botdagi eksklyuziv bonus va qulayliklarni birinchilardan bo'lib faollashtiring!</blockquote>\n\n"
        "⚠️ Agar biror savol yoki muammo yuzaga kelsa, quyidagi tugma orqali yordam markaziga bog'laning."
    )
    
    guide_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                
                InlineKeyboardButton(text="💬 Aloqa", callback_data="support")
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_start", style="danger")
            ]
        ]
    )
    
    try:
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