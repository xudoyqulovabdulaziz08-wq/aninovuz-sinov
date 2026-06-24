import logging
from typing import Any
from aiogram import Router, html, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Genre
from sqlalchemy import select
from services.user_service import UserService
from config import config
CREATOR_ID = config.CREATOR_ID

router = Router()

logger = logging.getLogger()



async def send_anime_card(message: Message, anime: dict, session: Any) -> bool:
    """
    Foydalanuvchiga animeni daxshat ramkali dizaynda va 
    kerakli tugmalar bilan ko'rsatuvchi yagona universal funksiya.
    """
    if not anime:
        return False
        
    anime_id = anime.get("anime_id")
    title = anime.get("title", "Nomsiz anime")
    year = anime.get("year", "—")
    description = anime.get("description") or "Tavsif kiritilmagan."
    episodes_count = len(anime.get("episodes", []))
    languages = anime.get("languages", [])
    languages_str = ", ".join(languages) if languages else "Mavjud emas"

    # 🛡️ VIP/Admin Dynamic statusni tekshirish qatlami
    user_service = UserService(session=session)
    user_data = await user_service.get_user(message.from_user.id)
    
    # Siz yozgan mantiq va CREATOR_ID o'zgarishsiz saqlandi
    is_vip_or_admin = user_data and (
        user_data.get("is_vip", False) or 
        user_data.get("status") == "admin" or 
        (message.from_user.id == CREATOR_ID if 'CREATOR_ID' in globals() else False)
    )

    # Janrlarni yuklash
    genres_str = "Mavjud emas"
    try:
        genre_ids = anime.get("genres", [])
        if genre_ids:
            res = await session.execute(select(Genre).where(Genre.id.in_(genre_ids)))
            genre_names = [g.name for g in res.scalars().all()]
            if genre_names:
                genres_str = ", ".join(genre_names)
    except Exception as genre_err:
        logger.error(f"❌ Janrlarni yuklashda xato: {genre_err}")

    # Siz taqdim etgan UX dizayn qolipi (UMUMAN O'ZGARTIRILMADI)
    caption = (
        f"╔══════════════════╗\n"
        f"    🎬 <b>{title}</b>\n"
        f"╚══════════════════╝\n\n"
        f"📌 <b>Anime haqida ma'lumot:</b>\n"
        f"╔══════════════════╗\n"
        f"├ 🆔 Kod: <code>#{anime_id}</code>\n"  
        f"├ 📅 Yil: <b>{year}</b>\n"
        f"├ ▶️ Qism: <b>{episodes_count}</b> \n"
        f"├ 🌐 Til: <b>{languages_str}</b>\n"
        f"╚══════════════════╝\n"
        f"╔══════════════════╗\n"
        f" 🔮 Janrlar: <i>{genres_str}</i>\n"
        f"╚══════════════════╝\n\n"
        f"📝 <b>Tavsif:</b>\n"
        f"<blockquote expandable>{description}</blockquote>"
    )

    # Inline tugmalar (style parametrlariga tegilmadi)
    user_anime_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 Qismlarni tomosha qilish", callback_data=f"show_episodes_user:{anime_id}", style="primary")],
        [InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="back_to_start", style="danger")]
    ])

    # Silliq o'chirish
    try:
        await message.delete()
    except:
        pass

    # Media turiga qarab jo'natish mantig'i + 🛡️ protect_content integratsiyasi
    poster_id = anime.get("poster_id")
    if poster_id:
        try:
            await message.answer_photo(
                photo=poster_id, 
                caption=caption, 
                reply_markup=user_anime_kb, 
                parse_mode="HTML",
                protect_content=not is_vip_or_admin  # 🔥 Oddiy foydalanuvchida daxshat blokirovka ishlaydi!
            )
            return True
        except Exception:
            try:
                await message.answer_video(
                    video=poster_id, 
                    caption=caption, 
                    reply_markup=user_anime_kb, 
                    parse_mode="HTML",
                    protect_content=not is_vip_or_admin  # 🔥 Videoda ham xavfsizlik muhrlanadi!
                )
                return True
            except Exception:
                pass

    # Agar rasmsiz/videosiz bo'lsa oddiy text xabarni himoyalash
    await message.answer(
        text=caption, 
        reply_markup=user_anime_kb, 
        parse_mode="HTML",
        protect_content=not is_vip_or_admin
    )
    return True