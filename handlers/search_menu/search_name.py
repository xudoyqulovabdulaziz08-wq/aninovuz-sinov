
from typing import Any
from aiogram import Router, html, types, F
from aiogram.fsm.state import StatesGroup, State

from services.anime_service import AnimeService
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, Message
from dotenv.main import logger
from aiogram.fsm.context import FSMContext
from handlers.search_menu.anime_card import send_anime_card



router = Router()




class SearchStates(StatesGroup):
    
    waiting_for_anime_name = State()

















@router.callback_query(lambda c: c.data == "search_by_name")
async def search_by_name(callback: CallbackQuery, state: FSMContext): # state argumenti qo'shildi
    await callback.answer()
    
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

    # 🚀 MANA SHU QATOR QO'SHILDI: Bot foydalanuvchidan nom kelishini kutadi
    await state.set_state(SearchStates.waiting_for_anime_name)









@router.message(SearchStates.waiting_for_anime_name, F.text)
async def process_anime_name_search(message: Message, state: FSMContext, session: Any):
    search_query = message.text.strip().lower()
    
    # 🌟 Foydalanuvchiga jarayon ketayotganini bildirish
    waiting_msg = await message.answer("🔍 Qidirilmoqda...")
    
    # 1. Keshdan barcha animelarning qidiruv xaritasi (ID va Nomlari) olinadi
    from services.anime_service import AnimeService
    anime_service = AnimeService(session=session)
    search_map = await anime_service.get_search_map()
    
    # 2. Foydalanuvchi yozgan so'z qatnashgan barcha animelarni qidiramiz (Index bo'yicha)
    found_animes = []
    for anime_id, anime_title in search_map.items():
        if search_query in anime_title.lower():
            found_animes.append((anime_id, anime_title))
            
    # Xabarlarni o'chirib chatni tozalaymiz
    try:
        await waiting_msg.delete()
        await message.delete()
    except:
        pass

    # 3. Agar hech qanday anime topilmasa
    if not found_animes:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Qayta urinish", callback_data="search_by_name", style="success")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_menu", style="danger")]
            ]
        )
        await message.answer(
            text=f"🔍 <b>\"{message.text}\"</b> bo'yicha hech qanday anime topilmadi.\n\nQayta tekshirib ko'ring yoki boshqa nom kiriting.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    # 4. Agar anime(lar) topilsa, ularni tugma ko'rinishida generatsiya qilamiz
    buttons = []
    for anime_id, anime_title in found_animes[:10]: # Maksimal 10 ta natija chiqadi (Telegram cheklovi u/n)
        # Deep-link yoki inline bosilganda o'sha anime kartasini ochadigan callback_data
        buttons.append([InlineKeyboardButton(text=f"🎬 {anime_title}", callback_data=f"view_anime_detals_{anime_id}")])
        
    # Pastiga bosh menyuga qaytish tugmasi
    buttons.append([InlineKeyboardButton(text="⬅️ Qidiruv menyusi", callback_data="search_menu", style="danger")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        text=f"🎯 <b>Natijalar (Topildi: {len(found_animes)} ta):</b>\n\nQuyidagilardan o'zingizga kerakli fasl yoki filmni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    # Qidiruv yakunlangani uchun stateni tozalaymiz
    await state.clear()









@router.callback_query(F.data.startswith("view_anime_detals_"))
async def view_anime_details(callback: CallbackQuery, session: Any):
    """
    Nomi bo'yicha qidiruvdan so'ng tanlangan animeni universal dizaynda ko'rsatadi.
    Admin bo'limidagi funksiyalar bilan chalkashmasligi uchun alohida nomlandi.
    """
    # Callback ma'lumotidan anime_id ni ajratib olamiz
    try:
        anime_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("⚠️ Ma'lumotni o'qishda xatolik yuz berdi!", show_alert=True)
        return

    # Foydalanuvchiga jarayon ketayotganini bildirish (Ekran qotib qolmasligi uchun)
    waiting_msg = await callback.message.answer("🔍 Yuborilmoqda...")
    await callback.answer()

    # Biznes mantiq qatlami orqali anime ma'lumotlarini keshdan yoki bazadan olamiz
    from services.anime_service import AnimeService
    anime_service = AnimeService(session=session)
    anime = await anime_service.get_anime(anime_id)

    if not anime:
        await callback.message.answer("❌ Kechirasiz, ushbu anime ma'lumotlar bazasidan topilmadi.")
        await waiting_msg.delete()
        return

    # 🚀 DAXSHAT UNIVERSAL DIZAYNGA YUBORAMIZ:
    # waiting_msg berib yuboriladi, send_anime_card ichidagi .delete() uni silliq o'chirib tashlaydi!
    await send_anime_card(waiting_msg, anime, session)