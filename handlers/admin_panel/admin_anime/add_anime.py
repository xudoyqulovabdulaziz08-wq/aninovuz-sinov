from aiogram.fsm.state import State, StatesGroup

from typing import Any
from aiogram import Router, F, html
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import math

from database.models import Genre
from services.anime_service import AnimeService


router = Router()













class AddAnimeStates(StatesGroup):
    poster = State()       # 1. Birinchi poster (Rasm/Video)
    info_line = State()    # 2. Nomi | Yili | Tili (Bitta qatorda)
    genres = State()       # 3. Janrlar (Paginatsiya + Multi-select + style="success")
    description = State()  # 4. Tasnif (Description)
    confirm_save = State() # 5. Bazaga saqlashni tasdiqlash






# ================= PAGINATSIYALIK JANRLAR KEYBOARDY =================
# ================= PAGINATSIYALIK JANRLAR KEYBOARDY =================
async def get_genres_paginated_markup(
    session: Any, 
    selected_genres: list[int], 
    page: int = 1, 
    per_page: int = 20
) -> InlineKeyboardMarkup:
    """Janrlarni 20 tadan bo'lib, 2 qatorda chiqaradi. Tanlanganlar yashil (success) bo'ladi."""
    stmt = select(Genre).order_by(Genre.name)
    result = await session.execute(stmt)
    genres = result.scalars().all()
    
    total_items = len(genres)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    # Joriy sahifadagi janrlarni kesib olamiz
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_genres = genres[start_idx:end_idx]
    
    keyboard = []
    row = []
    
    # Janr tugmalarini 2 qatordan joylashtirish (Jami max 20 ta)
    for genre in current_genres:
        is_selected = genre.id in selected_genres
        tick = "✅ " if is_selected else ""
        
        # Agar tanlangan bo'lsa style="success" (yashil), bo'lmasa standart (default)
        btn_style = "success" if is_selected else "default"
        
        row.append(InlineKeyboardButton(
            text=f"{tick}{genre.name}",  # Ortiqcha vergul olib tashlandi
            callback_data=f"g_tog:{genre.id}:{page}", # Sahifani yo'qotmaslik uchun callbackga qo'shamiz
            style=btn_style  # Siz aytgandek argument sifatida uzatildi
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    # Paginatsiya boshqaruvi (Oldingi | Keyingi)
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"g_page:{page-1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"g_page:{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    # Tasdiqlash va Bekor qilish boshqaruvi
    keyboard.append([
        InlineKeyboardButton(text="📥 Janrlarni tasdiqlash", callback_data="g_submit", style="success")
    ])
    keyboard.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_anime", style="danger")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)








# ================= 1. PROCESSSNI BOSHLASH: POSTER SO‘RASH =================
@router.callback_query(F.data == "add_anime")
async def start_add_anime(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddAnimeStates.poster)
    
    text = (
        f"🎬 {html.bold('Yangi anime qo‘shish bosqichi')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ Birinchi bo‘lib, animening {html.bold('Posterini')} (Rasm yoki Video xabar) yuboring.\n\n"
        f"⚠️ {html.bold('Muhim tavsiyalar (UX):')}\n"
        f"• Imkon qadar faqat {html.underline('portret')} formatdagi ({html.bold('3:4')} yoki {html.bold('2:3')} nisbatda) rasmlardan foydalaning.\n"
        f"• Gorizontal yoki kvadrat rasmlar bot interfeysida chiroyli chiqmasligi mumkin.\n"
        f"• Yuklanayotgan fayl sifati yuqori ekanligiga ishonch hosil qiling."
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_anime", style="danger")]
        ]),
        parse_mode="HTML"
    )




# ================= 2. POSTERNI QABUL QILISH -> INFO LINE SO‘RASH =================
@router.message(AddAnimeStates.poster, F.photo | F.video)
async def process_poster(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(poster_id=file_id)
    
    await state.set_state(AddAnimeStates.info_line)
    
    example = html.code("Naruto | 2002 | O‘zbekcha, Yaponcha")
    
    text = (
        f"📸 {html.bold('Poster qabul qilindi!')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"2️⃣ Endi anime asosiy ma'lumotlarini quyidagi {html.underline('shablonda')} bitta qator qilib yuboring:\n\n"
        f"👉 {html.bold('Nomi | Yili | Tili')}\n\n"
        f"⚠️ {html.bold('Eslatma:')} Har bir ma'lumotni ajratish uchun {html.bold('|')} (tik chiziq) belgisidan foydalaning. "
        f"Tillarni esa vergul bilan ajratishingiz mumkin.\n\n"
        f"📌 {html.bold('Namuna:')} {example}"
    )
    
    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_anime", style="danger")]
        ]),
        parse_mode="HTML"
    )






# ================= 3. INFO LINE'NI AJRATIB OLISH -> JANR TANLASHGA O‘TISH =================
# ================= 3. INFO LINE'NI AJRATIB OLISH -> JANR TANLASHGA O‘TISH =================
@router.message(AddAnimeStates.info_line, F.text)
async def process_info_line(message: Message, state: FSMContext, session: Any):
    text_data = message.text
    
    # Xatolik yuz berganda qayta-qayta ishlatiladigan bekor qilish tugmasi
    error_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_anime", style="danger")]
    ])
    
    if "|" not in text_data:
        await message.answer(
            text=f"❌ {html.bold('Format noto‘g‘ri!')}\n\n"
                 f"Iltimos, ma'lumotlarni so‘ralganidek {html.code('|')} belgisi orqali ajratib yuboring.\n"
                 f"📌 Namuna: {html.code('Naruto | 2002 | O‘zbekcha')}",
            reply_markup=error_kb,
            parse_mode="HTML"
        )
        return
        
    parts = [p.strip() for p in text_data.split("|")]
    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        await message.answer(
            text=f"❌ {html.bold('Ma’lumotlar yetarli emas!')}\n\n"
                 f"Nomi, Yili va Tilini to‘liq va bo‘sh joy qoldirmasdan kiriting.\n"
                 f"📌 Namuna: {html.code('Naruto | 2002 | O‘zbekcha')}",
            reply_markup=error_kb,
            parse_mode="HTML"
        )
        return
        
    title, year_str, languages_str = parts[0], parts[1], parts[2]
    
    # Yil faqat raqamdan iboratligini tekshirish
    if not year_str.isdigit():
        await message.answer(
            text=f"❌ {html.bold('Yil noto‘g‘ri kiritildi!')}\n\n"
                 f"Yil qismiga faqat raqam yozilishi kerak! (Masalan: {html.code('2024')})",
            reply_markup=error_kb,
            parse_mode="HTML"
        )
        return
        
    year = int(year_str)
    # Yil chegarasini tekshirish (1900 - 2050)
    if not (1900 <= year <= 2050):
        await message.answer(
            text=f"❌ {html.bold('Yil chegarasi xato!')}\n\n"
                 f"Kiritilgan yil {html.bold('1900')} va {html.bold('2050')} oralig‘ida bo‘lishi shart!",
            reply_markup=error_kb,
            parse_mode="HTML"
        )
        return
        
    # Tillarni vergul orqali ajratib list qilib olamiz
    languages = [l.strip() for l in languages_str.split(",") if l.strip()]
    
    await state.update_data(
        title=title,
        year=year,
        languages=languages,
        selected_genres=[]  # Janrlar uchun bo'sh ro'yxat ochamiz
    )
    
    await state.set_state(AddAnimeStates.genres)
    markup = await get_genres_paginated_markup(session, selected_genres=[], page=1)
    
    text = (
        f"📝 {html.bold('Asosiy ma’lumotlar tasdiqlandi!')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"3️⃣ {html.bold('Janrlarni tanlash bosqichi')}\n\n"
        f"Quyidagi ro‘yxatdan anime janrlarini tanlang (Har bir sahifada 20 tadan janr bor). "
        f"Tanlangan janrlar {html.italic('yashil rangga')} kiradi.\n\n"
        f"⏳ Tugatgach, pastdagi {html.underline('Janrlarni tasdiqlash')} tugmasini bosing:"
    )
    
    await message.answer(
        text=text,
        reply_markup=markup,
        parse_mode="HTML"
    )






# ================= 4. JANRLAR DINAMIK TOGGLE (MULTIPLE SELECT) =================
@router.callback_query(AddAnimeStates.genres, F.data.startswith("g_tog:"))
async def toggle_genre(callback: CallbackQuery, state: FSMContext, session: Any):
    await callback.answer()
    _, genre_id_str, page_str = callback.data.split(":")
    genre_id = int(genre_id_str)
    page = int(page_str)
    
    state_data = await state.get_data()
    selected_genres: list[int] = state_data.get("selected_genres", [])
    
    if genre_id in selected_genres:
        selected_genres.remove(genre_id)
    else:
        selected_genres.append(genre_id)
        
    await state.update_data(selected_genres=selected_genres)
    
    # O'sha turgan sahifasidagi keyboardni yangilaymiz
    markup = await get_genres_paginated_markup(session, selected_genres, page=page)
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass

# ================= 5. JANRLAR PAGINATSIYASI (PAGE ALMASHISH) =================
@router.callback_query(AddAnimeStates.genres, F.data.startswith("g_page:"))
async def change_genre_page(callback: CallbackQuery, state: FSMContext, session: Any):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    
    state_data = await state.get_data()
    selected_genres: list[int] = state_data.get("selected_genres", [])
    
    markup = await get_genres_paginated_markup(session, selected_genres, page=page)
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass



# ================= 6. JANRLAR TASDIQLANDI -> TASNIF (DESCRIPTION) SO‘RASH =================
# ================= 6. JANRLAR TASDIQLANDI -> TASNIF (DESCRIPTION) SO‘RASH =================
@router.callback_query(AddAnimeStates.genres, F.data == "g_submit")
async def submit_genres(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddAnimeStates.description)
    
    text = (
        f"🏁 {html.bold('Janrlar muvaffaqiyatli tanlandi!')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"4️⃣ Endi anime uchun {html.bold('Tasnif (Description / Hikoya matni)')} yuboring:\n\n"
        f"💡 {html.italic('Tavsiya: Ko‘p wall-of-text (uzun matn) qilib yubormaslikka harakat qiling, foydalanuvchiga o‘qishli bo‘lsin.')}"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_anime", style="danger")]
        ]),
        parse_mode="HTML"
    )


# ================= 7. TASNIF QABUL QILINDI -> BAZAGA SAQLASH RUXSATI (CONFIRMATION) =================
@router.message(AddAnimeStates.description, F.text)
async def process_description(message: Message, state: FSMContext, session: Any):
    await state.update_data(description=message.text)
    await state.set_state(AddAnimeStates.confirm_save)
    
    data = await state.get_data()
    selected_genre_ids = data.get("selected_genres", [])
    
    # Janr nomlarini bazadan olish
    genre_names = []
    if selected_genre_ids:
        stmt = select(Genre).where(Genre.id.in_(selected_genre_ids))
        res = await session.execute(stmt)
        genres = res.scalars().all()
        genre_names = [g.name for g in genres]
    
    genres_str = ", ".join(genre_names) if genre_names else "Tanlanmagan ⚠️"
    languages_str = ", ".join(data['languages'])

    # Eski UX uslubida ramkali mukammal dizayn (Status va ID olib tashlandi)
    preview_text = (
        f"╔══════════════════╗\n"
        f"     🎬 <b>{data['title']}</b>\n"
        f"╚══════════════════╝\n\n"
        f"📌 <b>Anime haqida ma'lumot:</b>\n"
        f"╔══════════════════╗\n"
        f"├ 📅 Yil: <b>{data['year']}</b>\n"
        f"├ ▶️ Qism: <b>Yangi (0)</b> \n"
        f"├ 🌐 Til: <b>{languages_str}</b>\n"
        f"╚══════════════════╝\n"
        f"╔══════════════════╗\n"
        f"  🔮 Janrlar: <i>{genres_str}</i>\n"
        f"╚══════════════════╝\n\n"
        f"📝 <b>Tavsif:</b>\n"
        f"<blockquote expandable>{data['description']}</blockquote>\n\n"
        f"❓ <b>Barcha ma’lumotlar to‘g‘rimi? Bazaga saqlansinmi?</b>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Ha, saqlansin", callback_data="db_save_anime", style="success"),
            InlineKeyboardButton(text="🔴 Yo‘q, bekor qilinsin", callback_data="admin_anime", style="danger")
        ]
    ])
    
    try:
        await message.answer_photo(
            photo=data['poster_id'], 
            caption=preview_text, 
            reply_markup=kb, 
            parse_mode="HTML"
        )
    except Exception:
        await message.answer_video(
            video=data['poster_id'], 
            caption=preview_text, 
            reply_markup=kb, 
            parse_mode="HTML"
        )
# ================= 8. YAKUNIY SAQLASH -> QISM QO‘SHISH YOKI ORQAGA TUGMALARI =================
# ================= 8. YAKUNIY SAQLASH -> QISM QO‘SHISH YOKI ORTGA TUGMALARI =================
@router.callback_query(AddAnimeStates.confirm_save, F.data == "db_save_anime")
async def save_anime_to_db(callback: CallbackQuery, state: FSMContext, session: Any):
    data = await state.get_data()
    await state.clear()  # FSMni tozalaymiz
    
    service = AnimeService(session=session)
    
    try:
        # AnimeService mantiqan tranzaksiyani saqlaydi va keshni yangilaydi
        anime = await service.create_anime(
            title=data["title"],
            poster_id=data["poster_id"],
            year=data["year"],
            is_completed=False,
            genres=data["selected_genres"],
            description=data["description"],
            languages=data["languages"]
        )
        
        anime_id = anime["anime_id"]
        
        success_text = (
            f"🎉 {html.bold('Muvaffaqiyatli saqlandi!')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 {html.bold('Anime bazaga muvaffaqiyatli qo‘shildi.')}\n\n"
            f"🆔 {html.bold('Anime kodi:')} {html.code(anime_id)}\n"
            f"🎬 {html.bold('Nomi:')} {html.underline(anime['title'])}\n\n"
            f"👇 Quyidagi tugma orqali ushbu animega seriyalarni (qismlarni) ketma-ket yuklashingiz mumkin:"
        )
        
        # UX Yaxshilanishi: Qism qo'shish yashil rangda, orqaga qaytish standart formatda
        success_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 Qism qo‘shish", callback_data=f"add_episode:{anime_id}", style="success"),
                InlineKeyboardButton(text="⬅️ Anime menyusi", callback_data="admin_anime")
            ]
        ])
        
        await callback.message.edit_caption(
            caption=success_text, 
            reply_markup=success_kb, 
            parse_mode="HTML"
        )
        
    except Exception as e:
        # Xatolik yuz berganda adminga qayta harakat qilish tugmasi chiqariladi
        error_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Bosh menyuga", callback_data="admin_anime", style="danger")]
        ])
        
        await callback.message.edit_caption(
            caption=f"❌ {html.bold('Bazaga saqlashda xatolik yuz berdi:')}\n\n"
                    f"⚠️ {html.code(str(e))}",
            reply_markup=error_kb,
            parse_mode="HTML"
        )

# ================= BEKOR QILISH HANDLERI =================
