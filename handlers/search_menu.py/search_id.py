
from aiogram import Router, html, types
from aiogram.fsm.state import StatesGroup, State

from services.anime_service import AnimeService
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger
from aiogram.fsm.context import FSMContext




router = Router()
# Qidiruv holatlarini belgilash
class SearchStates(StatesGroup):
    waiting_for_anime_id = State()






@router.callback_query(lambda c: c.data == "search_by_id")
async def search_by_id(callback: CallbackQuery, state: FSMContext): # state qo'shildi
    await callback.answer()
    
    search_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 🔍 ═════════╗\n"
        "   <b>ID BO'YICHA QIDIRISH</b>\n"
        "╚═════════ 🔍 ═════════╝\n\n"
        "🔢 Iltimos, qidirayotgan anime ID sini yozib yuboring.\n\n"
        "⚠️ <b>Eslatma:</b> ID raqamlardan iborat bo'lib, har bir anime uchun yagona bo'ladi!"
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_menu")] # style="danger" olib tashlandi (inline buttonda style bo'lmaydi)
        ]
    )
    
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=search_image_file_id,
                caption=text,
                parse_mode="HTML"
            ),
            reply_markup=kb
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logger.error(f"❌ Kutilmagan xatolik: {e}")
    except Exception as e:
        logger.error(f"❌ Tizimda xatolik yuz berdi: {e}")

    # 🚀 MANA SHU QATOR QO'SHILDI: Bot foydalanuvchidan ID kelishini kutadi
    await state.set_state(SearchStates.waiting_for_anime_id)