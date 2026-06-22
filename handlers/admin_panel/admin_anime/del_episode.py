from aiogram.types import InputMediaPhoto
import math
import logging
from typing import Any
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from services.anime_service import AnimeService

from aiogram.types import InputMediaVideo
from handlers.admin_panel.admin_anime.list_anime import get_episode_list_markup


from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
router = Router()

logger = logging.getLogger(__name__)



@router.callback_query(F.data.startswith("burn_ep:"))
async def confirm_delete_episode_handler(callback: CallbackQuery, session: Any):
    await callback.answer()
    
    _, anime_id_str, ep_num_str, back_page_str = callback.data.split(":")
    anime_id = int(anime_id_str)
    ep_num = int(ep_num_str)
    back_page = int(back_page_str)

    service = AnimeService(session=session)
    anime = await service.get_anime(anime_id)
    
    if not anime:
        await callback.message.answer("❌ Anime topilmadi!")
        return

    title = anime.get("title", "Nomsiz anime")
    poster_id = anime.get("poster_id")

    # Qizil ogohlantirish matni
    caption = (
        f"⚠️ {html.bold('DIQQAT! QISMNI O‘CHIRISH')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎬 Anime: <b>{title}</b>\n"
        f"🔢 O‘chirilayotgan qism: {html.bold(f'{ep_num}-qism')}\n\n"
        f"🛑 {html.italic('Ushbu amalni ortga qaytarib bo‘lmaydi! Ushbu qism ma’lumotlar bazasidan hamda kesh xotirasidan butunlay o‘chib ketadi.')}\n\n"
        f"Haqiqatdan ham ushbu qismni o‘chirmoqchimisiz?"
    )

    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            # Tasdiqlash tugmasi: maxsus 'real_burn_ep' callbackiga yo'naltiriladi
            InlineKeyboardButton(text="✅ Ha, o‘chirilsin", callback_data=f"real_burn_ep:{anime_id}:{ep_num}:{back_page}"),
            # Bekor qilish: qaytadan boyagi videoli ko'rish sahifasiga qaytaradi
            InlineKeyboardButton(text="❌ Yo‘q, bekor qilish", callback_data=f"show_ep:{anime_id}:{ep_num}:{back_page}")
        ]
    ])

    # Videoni pleeridan rasmli (posterli) ogohlantirish holatiga o'tkazamiz
    try:
        if poster_id:
            new_media = InputMediaPhoto(media=poster_id, caption=caption, parse_mode="HTML")
            await callback.message.edit_media(media=new_media, reply_markup=kb)
        else:
            await callback.message.edit_text(text=caption, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Ogohlantirish panelini ko'rsatishda xato: {e}")






@router.callback_query(F.data.startswith("real_burn_ep:"))
async def execute_delete_episode_handler(callback: CallbackQuery, session: Any):
    _, anime_id_str, ep_num_str, back_page_str = callback.data.split(":")
    anime_id = int(anime_id_str)
    ep_num = int(ep_num_str)
    back_page = int(back_page_str)

    service = AnimeService(session=session)
    
    # 1. Metodni chaqirib bazadan va keshdan o'chiramiz
    try:
        ok = await service.delete_episode(anime_id=anime_id, episode_num=ep_num)
    except Exception as e:
        logger.error(f"❌ Epizod o'chirish handlerida xato: {e}")
        ok = False

    if ok:
        await callback.answer(f"🗑 {ep_num}-qism muvaffaqiyatli o‘chirildi!", show_alert=True)
    else:
        await callback.answer("❌ Xatolik: Qism allaqachon o‘chirilgan bo‘lishi mumkin!", show_alert=True)

    # 2. O'chgandan keyin adminni chalg'itmasdan o'zi turgan qismlar ro'yxatiga qaytaramiz
    # Yangilangan kesh tufayli o'chgan qism ro'yxatdan g'oyib bo'ladi
    anime = await service.get_anime(anime_id)
    episodes = anime.get("episodes", []) if anime else []
    title = anime.get("title", "Nomsiz anime") if anime else ""

    caption = (
        f"╔══════════════════╗\n"
        f"  🎬 <b>{title}</b>\n"
        f"╚══════════════════╝\n\n"
        f"📹 Ro‘yxatdan kerakli qismni tanlang.\n"
        f"💡 {html.italic('Tanlangan qism videosi va uni boshqarish tugmalari shu yerning o‘zida ochiladi.')}"
    )

    # Boyagi paginatsiyali markup funksiyangizni chaqiramiz
    markup = await get_episode_list_markup(anime_id=anime_id, episodes=episodes, page=back_page)

    try:
        poster_id = anime.get("poster_id") if anime else None
        if poster_id:
            new_media = InputMediaPhoto(media=poster_id, caption=caption, parse_mode="HTML")
            await callback.message.edit_media(media=new_media, reply_markup=markup)
        else:
            await callback.message.edit_text(text=caption, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Ro'yxatga qaytarishda xatolik: {e}")