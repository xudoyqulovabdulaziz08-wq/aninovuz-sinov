from aiogram import Router, html, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger
from aiogram.fsm.context import FSMContext
router = Router()




@router.callback_query(lambda c: c.data == "admin_channel_menu")
async def admin_channel(callback: CallbackQuery, state: FSMContext):
    # Tugma bosilganda yuqoridagi soat belgisini darhol o'chiramiz
    await callback.answer()
    await state.clear()
    
    # Botingizning umumiy dizayniga mos, chiroyli sarlavhali matn (Imlosi to'g'rilandi)
    text = (
        f"📢 {html.bold('Kanal boshqaruvi bo‘limi')}\n\n"
        f"Ushbu bo‘lim orqali bazadagi majburiy obuna kanallarini tahrirlashingiz, "
        f"yangi kanal qo‘shishingiz yoki o‘chirishingiz mumkin.\n\n"
        f"Kerakli amalni tanlang:"
    )
    
    # Tugmalar iyerarxiyasi (style="danger" o'z o'rnida qoldi)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="add_channel")],
            [InlineKeyboardButton(text="📃 Kanallar ro‘yxati", callback_data="list_channel")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_panel", style="danger")]  
        ]
    )
    
    # Try-except bloki
    try:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Xabar o'zgarmagan bo'lsa, indamay o'tkazib yuboramiz
            pass
        else:
            logger.error(f"❌ Kanal bo'limida Telegram xatoligi: {e}")
    except Exception as e:
        logger.error(f"❌ Kanal bo'limida kutilmagan xatolik: {e}")