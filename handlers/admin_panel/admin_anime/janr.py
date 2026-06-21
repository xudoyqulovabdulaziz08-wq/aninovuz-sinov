from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.models import Genre

router = Router(name="admin_temp_genres")

class TempGenreStates(StatesGroup):
    waiting_genres = State()  # Janrlarni matn sifatida kutish holati
    confirm_save = State()    # Tasdiqlash holati


# ================= 1. /genre BUYRUG‘I ORQALI BOSHLASH =================
@router.message(Command("genre", "janr"))
async def start_quick_genres(message: Message, state: FSMContext):
    await state.set_state(TempGenreStates.waiting_genres)
    
    text = (
        f"📁 {html.bold('Vaqtinchalik tezkor janr qo‘shish bo‘limi')}\n\n"
        f"Iltimos, bazaga qo‘shmoqchi bo‘lgan janrlaringizni {html.underline('vergul')} orqali ajratib yuboring.\n\n"
        f"📌 Masalan: {html.code('Komediyya, Boevik, Sarguzasht, Fantastika')}"
    )
    
    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_genre_add")]
        ]),
        parse_mode="HTML"
    )

# ================= 2. VERGUL BILAN AJRATILGAN MATNNI QABUL QILISH =================
@router.message(TempGenreStates.waiting_genres, F.text)
async def process_raw_genres(message: Message, state: FSMContext):
    raw_text = message.text
    
    # Vergul orqali ajratamiz, bo'sh joylarni tozalaymiz va bo'sh elementlarni olib tashlaymiz
    genres_list = [g.strip() for g in raw_text.split(",") if g.strip()]
    
    if not genres_list:
        await message.answer("❌ Hech qanday janr aniqlanmadi. Iltimos, qaytadan to‘g‘ri formatda yuboring!")
        return
        
    # Dublikatlarni (takrorlanganlarini) tozalaymiz
    genres_list = list(set(genres_list))
    
    await state.update_data(parsed_genres=genres_list)
    await state.set_state(TempGenreStates.confirm_save)
    
    # Adminga vizual ko'rsatish
    preview_genres = "\n".join([f"🔹 {g}" for g in genres_list])
    
    text = (
        f"📝 {html.bold('Quyidagi janrlar bazaga saqlashga tayyorlandi:')}\n\n"
        f"{preview_genres}\n\n"
        f"👇 Tasdiqlash uchun quyidagi tugmani bosing:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Bazaga yuborish", callback_data="db_save_quick_genres")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_genre_add")
        ]
    ])
    
    await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

# ================= 3. YAKUNIY BAZAGA SAQLASH (TRANSACTION SAFE) =================
@router.callback_query(TempGenreStates.confirm_save, F.data == "db_save_quick_genres")
async def save_genres_to_db(callback: CallbackQuery, state: FSMContext, session: Any):
    data = await state.get_data()
    genres_list: list[str] = data.get("parsed_genres", [])
    await state.clear()
    
    added_count = 0
    skipped_genres = []
    
    try:
        for genre_name in genres_list:
            # Avval bazada bor yoki yo'qligini tekshiramiz (dublikat bo'lmasligi uchun)
            stmt = select(Genre).where(Genre.name == genre_name)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            
            if not existing:
                # Agar bazada yo'q bo'lsa, yangi ob'ekt yaratamiz
                new_genre = Genre(name=genre_name)
                session.add(new_genre)
                added_count += 1
            else:
                skipped_genres.append(genre_name)
                
        # Tranzaksiyani saqlaymiz (Commit)
        await session.commit()
        
        # Natija matnini shakllantiramiz
        result_text = f"✅ {html.bold('Janrlar muvaffaqiyatli yakunlandi!')}\n\n"
        result_text += f"➕ {html.bold('Yangi qo‘shilganlar:')} {added_count} ta\n"
        
        if skipped_genres:
            result_text += f"⚠️ {html.bold('Bazada allaqachon bor bo‘lganlar (tashlab ketildi):')}\n"
            result_text += f"{html.code(', '.join(skipped_genres))}\n"
            
        result_text += f"\n💡 Endi bemalol anime qo‘shish bo‘limiga o‘tib janrlarni tanlashingiz mumkin."
        
        await callback.message.edit_text(text=result_text, reply_markup=None, parse_mode="HTML")
        
    except Exception as e:
        await session.rollback()
        await callback.message.edit_text(
            text=f"❌ Bazaga yozishda xatolik: {html.code(str(e))}",
            reply_markup=None,
            parse_mode="HTML"
        )

# ================= BEKOR QILISH =================
@router.callback_query(F.data == "cancel_genre_add")
async def cancel_genre(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Amal bekor qilindi", show_alert=True)
    await callback.message.edit_text("❌ Janr qo‘shish jarayoni bekor qilindi.")