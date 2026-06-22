import logging

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Genre
from sqlalchemy import select



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

    # Siz taqdim etgan UX dizayn qolipi
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
        f"  🔮 Janrlar: <i>{genres_str}</i>\n"
        f"╚══════════════════╝\n\n"
        f"📝 <b>Tavsif:</b>\n"
        f"<blockquote expandable>{description}</blockquote>"
    )

    # Inline tugmalar (style olingan, chunki url/callback tugmalarda style bo'lmaydi)
    user_anime_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 Qismlarni tomosha qilish", callback_data=f"show_episodes_user:{anime_id}")],
        [InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="back_to_start")]
    ])

    # Silliq o'chirish (agar iloji bo'lsa)
    try:
        await message.delete()
    except:
        pass

    # Media turiga qarab jo'natish mantig'i
    poster_id = anime.get("poster_id")
    if poster_id:
        try:
            await message.answer_photo(photo=poster_id, caption=caption, reply_markup=user_anime_kb, parse_mode="HTML")
            return True
        except Exception:
            try:
                await message.answer_video(video=poster_id, caption=caption, reply_markup=user_anime_kb, parse_mode="HTML")
                return True
            except Exception:
                pass

    await message.answer(text=caption, reply_markup=user_anime_kb, parse_mode="HTML")
    return True