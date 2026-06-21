from aiogram.fsm.state import State, StatesGroup

from typing import Any
from aiogram import Router, F, html
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import math

from database.models import Genre
from services.anime_service import AnimeService
from .anime_menu import admin_anime_kb

router = Router()













class AddAnimeStates(StatesGroup):
    poster = State()       # 1. Birinchi poster (Rasm/Video)
    info_line = State()    # 2. Nomi | Yili | Tili (Bitta qatorda)
    genres = State()       # 3. Janrlar (Paginatsiya + Multi-select + style="success")
    description = State()  # 4. Tasnif (Description)
    confirm_save = State() # 5. Bazaga saqlashni tasdiqlash






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
        style_type = "success" if is_selected else "default"
        
        row.append(InlineKeyboardButton(
            text=f"{tick}{genre.name}", 
            callback_data=f"g_tog:{genre.id}:{page}" # Sahifani yo'qotmaslik uchun callbackga qo'shamiz
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
        InlineKeyboardButton(text="📥 Janrlarni tasdiqlash", callback_data="g_submit")
    ])
    keyboard.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_anime_add")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= 1. PROCESSSNI BOSHLASH: POSTER SO‘RASH =================
@router.callback_query(F.data == "add_anime")
async def start_add_anime(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddAnimeStates.poster)
    
    await callback.message.edit_text(
        text=f"🎬 {html.bold('Yangi anime qo‘shish bosqichi')}\n\n"
             f"1️⃣ Birinchi bo‘lib, animening {html.underline('Posterini')} (Rasm yoki Video xabar) yuboring:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_anime_add")]
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
    await message.answer(
        text=f"2️⃣ Endi anime ma'lumotlarini quyidagi {html.bold('formatda, bitta qatorda')} yuboring:\n\n"
             f"👉 {html.bold('Nomi | Yili | Tili')}\n\n"
             f"📌 Masalan: {example}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_anime_add")]
        ]),
        parse_mode="HTML"
    )

# ================= 3. INFO LINE'NI AJRATIB OLISH -> JANR TANLASHGA O‘TISH =================
@router.message(AddAnimeStates.info_line, F.text)
async def process_info_line(message: Message, state: FSMContext, session: Any):
    text_data = message.text
    if "|" not in text_data:
        await message.answer("❌ Noto‘g‘ri format! Iltimos, ma'lumotlarni so‘ralganidek `|` belgisi orqali ajratib yuboring.")
        return
        
    parts = [p.strip() for p in text_data.split("|")]
    if len(parts) < 3:
        await message.answer("❌ Ma'lumotlar kam! Nomi, Yili va Tilini to‘liq kiriting.")
        return
        
    title, year_str, languages_str = parts[0], parts[1], parts[2]
    
    if not year_str.isdigit():
        await message.answer("❌ Yili qismi faqat raqamlardan iborat bo‘lishi kerak!")
        return
        
    # Tillarni vergul orqali ajratib list qilib olamiz
    languages = [l.strip() for l in languages_str.split(",")]
    
    await state.update_data(
        title=title,
        year=int(year_str),
        languages=languages,
        selected_genres=[] # Janrlar uchun bo'sh ro'yxat ochamiz
    )
    
    await state.set_state(AddAnimeStates.genres)
    markup = await get_genres_paginated_markup(session, selected_genres=[], page=1)
    
    await message.answer(
        text=f"3️⃣ {html.bold('Janrlarni tanlash bosqichi')}\n\n"
             f"Quyidagi tugmalardan anime janrlarini tanlang (Har bir sahifada 20 tadan janr bor). "
             f"Tanlangan janrlar yashil rangga kiradi. Tugatgach {html.underline('Janrlarni tasdiqlash')} tugmasini bosing:",
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
@router.callback_query(AddAnimeStates.genres, F.data == "g_submit")
async def submit_genres(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddAnimeStates.description)
    
    await callback.message.edit_text(
        text=f"4️⃣ Endi anime uchun {html.bold('Tasnif (Description / Hikoya matni)')} yuboring:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_anime_add")]
        ]),
        parse_mode="HTML"
    )

# ================= 7. TASNIF QABUL QILINDI -> BAZAGA SAQLASH RUXSATI (CONFIRMATION) =================
@router.message(AddAnimeStates.description, F.text)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddAnimeStates.confirm_save)
    
    data = await state.get_data()
    
    preview_text = (
        f"⚠️ {html.bold('Malumotlarni tekshiring va saqlashga ruxsat bering:')}\n\n"
        f"🎬 {html.bold('Nomi:')} {data['title']}\n"
        f"📅 {html.bold('Yili:')} {data['year']}\n"
        f"🌐 {html.bold('Tillari:')} {', '.join(data['languages'])}\n"
        f"📁 {html.bold('Tanlangan janrlar IDsi:')} {data['selected_genres']}\n"
        f"📝 {html.bold('Tasnif:')} {data['description'][:100]}...\n\n"
        f"Bazaga saqlashga ruxsat berasizmi?"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Ha, saqlansin", callback_data="db_save_anime"),
            InlineKeyboardButton(text="🔴 Yo‘q, bekor qilish", callback_data="cancel_anime_add")
        ]
    ])
    
    await message.answer_photo(photo=data['poster_id'], caption=preview_text, reply_markup=kb, parse_mode="HTML")

# ================= 8. YAKUNIY SAQLASH -> QISM QO‘SHISH YOKI ORQAGA TUGMALARI =================
@router.callback_query(AddAnimeStates.confirm_save, F.data == "db_save_anime")
async def save_anime_to_db(callback: CallbackQuery, state: FSMContext, session: Any):
    data = await state.get_data()
    await state.clear() # FSMni tozalaymiz
    
    service = AnimeService(session=session)
    
    try:
        # AnimeService mantiqan tranzaksiyani saqlaydi va keshni invalidatsiya qiladi
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
            f"🎉 {html.bold('Anime muvaffaqiyatli bazaga saqlandi!')}\n\n"
            f"🆔 {html.bold('Anime Kodi (ID):')} {html.code(anime_id)}\n"
            f"🎬 {html.bold('Nomi:')} {anime['title']}\n\n"
            f"Endi ushbu anime uchun qismlar (seriyalar) yuklashingiz mumkin."
        )
        
        # Qism qo'shish va Ortga qaytish tugmalari
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 Qism qo‘shish", callback_data=f"add_episode:{anime_id}"),
                InlineKeyboardButton(text="⬅️ Anime menyusiga", callback_data="admin_anime_menu")
            ]
        ])
        
        # photo xabaridagi inline tugmani yangilaymiz
        await callback.message.edit_caption(caption=success_text, reply_markup=kb, parse_mode="HTML")
        
    except Exception as e:
        await callback.message.edit_caption(
            caption=f"❌ Xatolik yuz berdi: {html.code(str(e))}",
            reply_markup=admin_anime_kb,
            parse_mode="HTML"
        )

# ================= BEKOR QILISH HANDLERI =================
@router.callback_query(F.data == "cancel_anime_add")
async def cancel_anime_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Amal bekor qilindi", show_alert=True)
    # Agar xabar rasm xabari bo'lsa uni o'chirib yuboramiz va menyuni qayta chiqaramiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("🎬 Anime boshqaruvi bosh menyusiga qaytdingiz.", reply_markup=admin_anime_kb)