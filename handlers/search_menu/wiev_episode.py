import logging
from typing import Any
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from aiogram.exceptions import TelegramBadRequest

from services.anime_service import AnimeService
from services.user_service import UserService

logger = logging.getLogger("PlayerHandler")
router = Router()

# Bir sahifada nechta qism tugmasi chiqishi (4 tadan 3 qator = 12 ta)
EPISODES_PER_PAGE = 12

@router.callback_query(F.data.startswith("show_episodes_user:") | F.data.startswith("play_ep_page:"))
async def process_anime_streaming_player(callback: CallbackQuery, session: Any):
    await callback.answer()
    
    # 1. Kelgan callback ma'lumotlarini ajratib olamiz
    # Formatlar: "show_episodes_user:anime_id" yoki "play_ep_page:anime_id:current_episode:page"
    data_parts = callback.data.split(":")
    
    if data_parts[0] == "show_episodes_user":
        anime_id = int(data_parts[1])
        current_ep_num = 1  # Birinchi marta kirganda avtomat 1-qism
        current_page = 1
    else:
        anime_id = int(data_parts[1])
        current_ep_num = int(data_parts[2])
        current_page = int(data_parts[3])

    # 2. Xizmat qatlamlarini chaqiramiz
    anime_service = AnimeService(session=session)
    user_service = UserService(session=session)
    
    # Kesh-First tizimidan epizodlarni yuklaymiz
    episodes = await anime_service.get_anime_episodes_cache(anime_id)
    anime = await anime_service.get_anime(anime_id)
    user = await user_service.get_user(callback.from_user.id) # VIP statusni tekshirish uchun
    
    if not episodes or not anime:
        await callback.message.answer("⚠️ Kechirasiz, ushbu animening qismlari yuklanmagan yoki topilmadi.")
        return

    # Foydalanuvchi statusi (is_vip dynamic property orqali tekshiriladi)
    is_vip_or_admin = user.get("is_vip", False) or user.get("status") == "admin"

    # 3. Joriy ko'rilayotgan epizod obyektini topamiz
    current_episode = next((e for e in episodes if e["episode"] == current_ep_num), episodes[0])
    current_ep_num = current_episode["episode"] # Agar so'ralgan qism topilmasa birinchisiga qaytadi
    
    video_file_id = current_episode["video_file_id"]
    poster_id = anime.get("poster_id") # Thumbnail uchun asosiy anime poster ID-si

    # 4. Premium UX dizayn qatlamidagi matn (Caption)
    caption = (
        f"╔══════════════════════╗\n"
        f"   🎬 <b>{anime['title']}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"📌 <b>Joriy tomosha:</b>\n"
        f"╔══════════════════════╗\n"
        f"├ 📹 Qism: <b>{current_ep_num}-qism</b>\n"
        f"├ 🌐 Platforma: <a href='https://t.me/Aninovuz_Bot'>AniNowuz</a>\n"
        f"╚══════════════════════╝\n\n"
        f"📢 Kanal @AniNowuz  "
    )

    # 5. Pleyer tugmalari (Pult) arxitekturasini quramiz
    buttons = []
    
    # Paginatsiya uchun epizodlarni bo'laklaymiz
    start_idx = (current_page - 1) * EPISODES_PER_PAGE
    end_idx = start_idx + EPISODES_PER_PAGE
    page_episodes = episodes[start_idx:end_idx]
    
    # Qismlar tugmalarini 4 tadan qatorga joylash mantig'i
    row = []
    for ep in page_episodes:
        ep_num = ep["episode"]
        if ep_num == current_ep_num:
            # Aktiv ko'rilayotgan qism yashil rangda va [] qavs ichida bo'ladi
            row.append(InlineKeyboardButton(text=f"[ {ep_num} ]", callback_data="noop", style="success"))
        else:
            row.append(InlineKeyboardButton(
                text=str(ep_num), 
                callback_data=f"play_ep_page:{anime_id}:{ep_num}:{current_page}"
            ))
            
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Navigatsiya (Oldingi sahifa | Keyingi sahifa) tugmalari
    nav_row = []
    total_pages = (len(episodes) + EPISODES_PER_PAGE - 1) // EPISODES_PER_PAGE
    
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi sahifa", callback_data=f"play_ep_page:{anime_id}:{current_ep_num}:{current_page - 1}"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi sahifa ➡️", callback_data=f"play_ep_page:{anime_id}:{current_ep_num}:{current_page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    # VIP va Adminlar uchun maxsus funksiyalar
    if is_vip_or_admin:
        buttons.append([InlineKeyboardButton(text="📥 Barcha qismlarni yuklab olish (VIP)", callback_data=f"download_all_vip:{anime_id}")])
    
    # Orqaga qaytish tugmasi (Asosiy anime kartasiga qaytaradi)
    buttons.append([InlineKeyboardButton(text="⬅️ Anime kartasiga qaytish", callback_data=f"user_g_view_{anime_id}", style="danger")])
    
    player_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 6. SILLIQ EDIT MEDIA MANTIQI (NETFLIX EFFECT)
    # Oddiy foydalanuvchilarga protect_content=True, VIP/Adminga False bo'ladi!
    media_player = InputMediaVideo(
        media=video_file_id,
        thumbnail=poster_id,  # Rasm muqova sifatida ishlatiladi (Thumbnail hiylasi)
        caption=caption,
        parse_mode="HTML"
    )

    try:
        # Eski xabarni o'chirmasdan turib joyida pleyerni va cheklovni yangilaymiz
        await callback.message.edit_media(
            media=media_player,
            reply_markup=player_kb
        )
        
        # Telegram xabarni tahrirlayotganda protect_contentni o'zgartirishga ba'zan ruxsat bermaydi, 
        # shuning uchun xabarning joriy holatiga qarab xavfsiz moslashtiramiz.
        callback.message.protect_content = not is_vip_or_admin

    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            pass
        elif "message to edit not found" in error_msg or "cannot edit" in error_msg:
            # Agar edit_media qilish ilojisi bo'lmasa (masalan eski xabar butunlay matnli bo'lsa), 
            # eski xabarni o'chirib, yangidan video pleyer qilib yuboramiz.
            try:
                await callback.message.delete()
            except:
                pass
            await callback.message.answer_video(
                video=video_file_id,
                thumbnail=poster_id,
                caption=caption,
                reply_markup=player_kb,
                parse_mode="HTML",
                protect_content=not is_vip_or_admin
            )
        else:
            logger.error(f"❌ Pleyer tahrirlanishida kutilmagan xato: {e}")