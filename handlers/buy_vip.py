from aiogram import Router, html, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger

router = Router()


@router.callback_query(lambda c: c.data == "buy_vip")
async def buy_vip_menu(callback: CallbackQuery):
    await callback.answer()
    
    vip_image_file_id = "AgACAgIAAxkBAAI8tmo2zpXedWfk2pHIT5yhD3bo3ksoAAKFGWsbZ6WxSZsBcZaddInXAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 💎 ═════════╗\n"
        "   <b>VIP IMTIYOZLAR</b>\n"
        "╚═════════ 💎 ═════════╝\n\n"
        "VIP bolimi tez orada ishga tushadi! 🌟\n\n"
        
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_start", style="danger")]
        ]
    )
    
    try:
        # Matn o'rniga Media va Klaviatura birga chiroyli edit bo'ladi
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=vip_image_file_id,
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
        logger.error(f"❌ Umumiy xatolik: {e}")