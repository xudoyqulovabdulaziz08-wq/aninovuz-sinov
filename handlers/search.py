from aiogram import Router, html, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv.main import logger
from aiogram.fsm.context import FSMContext
router = Router()

@router.callback_query(lambda c: c.data == "search_menu")
async def search_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    # 🖼 Qidiruv bo'limi uchun rasm (Startdagi rasmni qoldirdik, o'zgartirmoqchi bo'lsangiz yangi file_id qo'yasiz)
    search_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 🔍 ═════════╗\n"
        "   <b>ANIME QIDIRISH</b>\n"
        "╚═════════ 🔍 ═════════╝\n\n"
        "Qidiruv menyusiga xush kelibsiz! 🌟\n\n"
        "<blockquote expandable><b>Nomi bo'yicha qidirish</b></blockquote>\n"
        "<blockquote expandable><b>ID bo'yicha qidirish</b></blockquote>\n"
        "<blockquote expandable><b>Janr bo'yicha qidirish</b></blockquote>\n"
        
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Nomi bo'yicha qidirish", callback_data="search_by_name", style="primary")],
            [InlineKeyboardButton(text="🔢 ID bo'yicha qidirish", callback_data="search_by_id", style="primary")],
            [InlineKeyboardButton(text="🎭 Janr bo'yicha qidirish", callback_data="search_by_genre", style="primary")],
            # ⬇️ "Orqaga" tugmasi start.py faylidagi 'back_to_start' handleriga ulandi!
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_start", style="danger")]
        ]
    )
    
    try:
        # Matn o'rniga Media va Klaviatura birga chiroyli edit bo'ladi
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
        # Agar xabar allaqachon o'zgargan bo'lsa, xato bermaymiz, shunchaki o'tkazib yuboramiz
            pass
        else:
            # Boshqa jiddiy xatolik bo'lsa logga yozamiz
            logger.error(f"❌ Kutilmagan xatolik: {e}")
    except Exception as e:
        logger.error(f"❌ Tizimda xatolik yuz berdi: {e}")




@router.callback_query(lambda c: c.data == "search_by_name")
async def search_by_name(callback: CallbackQuery):
    await callback.answer()
    
    # O'sha asosiy rasmingiz ID si (barcha qidiruvlarda bir xil tursa interfeys silliq chiqadi)
    search_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 🔍 ═════════╗\n"
        "   <b>NOMI BO'YICHA QIDIRISH</b>\n"
        "╚═════════ 🔍 ═════════╝\n\n"
        "✍️ Iltimos, qidirayotgan anime nomini  yozib yuboring.\n\n"
        "⚠️ <b>Eslatma:</b> Nomni qanchalik to'g'ri va aniq yozsangiz, uni topish shunchalik oson bo'ladi!"
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            # Orqaga bosganda boyagi qidiruv bosh menyusiga ('search_menu') qaytadi
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_menu", style="danger")]
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
        # Agar xabar allaqachon o'zgargan bo'lsa, xato bermaymiz, shunchaki o'tkazib yuboramiz
            pass
        else:
            # Boshqa jiddiy xatolik bo'lsa logga yozamiz
            logger.error(f"❌ Kutilmagan xatolik: {e}")
    except Exception as e:
        logger.error(f"❌ Tizimda xatolik yuz berdi: {e}")





@router.callback_query(lambda c: c.data == "search_by_genre")
async def search_by_genre(callback: CallbackQuery):
    await callback.answer()
    
    search_image_file_id = "AgACAgIAAxkBAAI8pmo2wwmGj_SoELEjURiyUyabzhwoAAI5GWsbZ6WxSUf3FNSMy6ajAQADAgADdwADPAQ"
    
    text = (
        "╔═════════ 🔍 ═════════╗\n"
        "   <b>JANR BO'YICHA QIDIRISH</b>\n"
        "╚═════════ 🔍 ═════════╝\n\n"
        "🎭 Iltimos, qidirayotgan anime janrini yozib yuboring.\n\n"
        "⚠️ <b>Eslatma:</b> Janr nomini aniq yozsangiz, sizga mos keladigan animelarni topish osonroq bo'ladi!"
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_menu", style="danger")]
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
        await callback.message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")