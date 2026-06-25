import logging
from typing import Any
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from services.anime_service import AnimeService



class EditAnimeStates(StatesGroup):
    waiting_for_new_name = State()       # Yangi nomni kiritish holati
    waiting_for_new_lang = State()       # 🌐 Yangi tilni kiritish holati
    waiting_for_new_desc = State()       # 📝 Yangi tasnifni kiritish holati
    waiting_for_new_year = State()       # 📅 Yangi yilni kiritish holati
    waiting_for_new_poster = State()     # 🖼 Yangi poster qabul qilish holati
    waiting_for_confirmation = State()   # Ha/Yo'q tasdiqlash holati








logger = logging.getLogger("EditAnimeMenu")
router = Router()

@router.callback_query(F.data.startswith("edit_anime:"))
async def process_edit_anime_menu(callback: CallbackQuery, session: Any):
    # 1. Callback datadan anime_id ni ajratib olamiz
    try:
        anime_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("🚨 Noto'g'ri anime ID!", show_alert=True)
        return

    # 2. Anime xizmatini chaqirib, joriy ma'lumotlarni tekshiramiz (nomini sarlavhada ko'rsatish uchun)
    from services.anime_service import AnimeService
    service = AnimeService(session=session)
    
    try:
        anime = await service.get_anime(anime_id)
    except Exception as e:
        logger.error(f"❌ Tahrirlash menyusida animeni yuklashda xato: {e}")
        anime = None

    if not anime:
        await callback.answer("❌ Anime topilmadi yoki o‘chirilgan!", show_alert=True)
        return

    anime_title = anime.get("title", "Nomsiz anime")

    # 3. Siz aytgan toza va siqilib ketmaydigan qisqa tugmalar paneli (UX Optimized)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Nomi", callback_data=f"edit_field:title:{anime_id}", style="primary" ),
            InlineKeyboardButton(text="📅 Yili", callback_data=f"edit_field:year:{anime_id}", style="primary")
        ],
        [
            InlineKeyboardButton(text="🌐 Tili", callback_data=f"edit_field:lang:{anime_id}", style="primary"),
            InlineKeyboardButton(text="🔮 Janr", callback_data=f"edit_genre_menu:{anime_id}", style="primary")
        ],
        [
            InlineKeyboardButton(text="📝 Tasnif", callback_data=f"edit_field:desc:{anime_id}", style="primary"),
            InlineKeyboardButton(text="🖼 Poster", callback_data=f"edit_field:poster:{anime_id}", style="primary")
        ],
        [
            # Orqaga bosganda eski daxshatli chiroyli ramkali vizual menyuga qaytaradi (page=1 default)
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"v_anime:{anime_id}:1",  style="danger")
        ]
    ])

    # 4. Sarlavha matni (Admin aniq qayerdaligini bilishi uchun)
    text = (
        f"⚙️ <b>Siz anime tahrirlash bo'limidasiz!</b>\n"
        f"🎬 Tanlangan anime: <u>{anime_title}</u>\n\n"
        f"<i>Iltimos, o'zgartirmoqchi bo'lgan ma'lumotingizni quyidagi qisqa tugmalardan tanlang:</i>"
    )

    await callback.answer("Tahrirlash menyusi...")

    # 5. 🖼 MEDIA EDIT MANTIQI (Poster rasm yoki video bo'lishiga qarab silliq edit qilish)
    try:
        # Eski xabarning caption (matn) va reply_markup (tugmalar) qismini silliq yangilaymiz
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        # Agar qandaydir sabab bilan caption yangilanmasa (masalan matnsiz media bo'lsa), xabarni qayta yuboramiz
        if "message to edit not found" in str(e) or "there is no caption" in str(e):
            try:
                await callback.message.delete()
            except:
                pass
            
            poster_id = anime.get("poster_id")
            if poster_id:
                try:
                    await callback.message.answer_photo(photo=poster_id, caption=text, reply_markup=kb, parse_mode="HTML")
                except TelegramBadRequest:
                    await callback.message.answer_video(video=poster_id, caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await callback.message.answer(text=text, reply_markup=kb, parse_mode="HTML")
                






# =====================================================================
# 📑 1-QADAM: "📝 Nomi" tugmasi bosilganda holatga (State) o'tkazish
# =====================================================================
@router.callback_query(F.data.startswith("edit_field:title:"))
async def edit_anime_title_start(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split(":")[2])
    
    # Kelajakda kerak bo'lishi uchun anime_id va eski pleer xabarining ID sini holatga saqlaymiz
    await state.update_data(edit_anime_id=anime_id, main_msg_id=callback.message.message_id)
    
    # State-ni o'zgartiramiz
    await state.set_state(EditAnimeStates.waiting_for_new_name)
    
    # Media joyida qoladi, faqat matn o'zgaradi va tugmalar yo'qoladi
    text = (
        "✍️ <b>Yangi nom kiritish:</b>\n\n"
        "Iltimos, animening yangi nomini to'g'ri yozib, botga xabar shaklida yuboring..."
    )
    
    await callback.answer("Nom tahrirlash boshlandi")
    try:
        await callback.message.edit_caption(caption=text, reply_markup=None, parse_mode="HTML")
    except TelegramBadRequest:
        pass


# =====================================================================
# 📑 2-QADAM: Admin yangi nom yuborganda uni ushlash va Ha/Yo'q so'rash
# =====================================================================
@router.message(EditAnimeStates.waiting_for_new_name, F.text)
async def process_new_anime_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    main_msg_id = state_data.get("main_msg_id")
    
    # 🗑 Admin yuborgan matnli xabarni darhol o'chirib tashlaymiz (Toza UX uchun)
    try:
        await message.delete()
    except Exception:
        pass
        
    # Kelajakda saqlash uchun yangi nomni ham state-ga yozamiz
    await state.update_data(new_anime_title=new_name)
    
    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_edit:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_edit:no")
        ]
    ])
    
    confirm_text = (
        f"❓ <b>Haqiqatdan ham anime nomi o'zgartirilsinmi?</b>\n\n"
        f"📝 Yangi nom: <u>{new_name}</u>"
    )
    
    # Asosiy media xabarining matnini tasdiqlash rejimiga o'tkazamiz
    await state.set_state(EditAnimeStates.waiting_for_confirmation)
    try:
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            caption=confirm_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Tasdiqlash xabarini chiqarishda xato: {e}")


# =====================================================================
# 📑 3-QADAM: Tasdiqlash (Ha yoki Yo'q) tugmalari bosilganda (TUZATILDI)
# =====================================================================
@router.callback_query(EditAnimeStates.waiting_for_confirmation, F.data.startswith("confirm_edit:"))
async def save_or_cancel_anime_title(callback: CallbackQuery, state: FSMContext, session: Any):
    action = callback.data.split(":")[1]
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    new_name = state_data.get("new_anime_title")
    
    # ❌ AGAR ADMIN "YO'Q" DEB RAD ETSA
    if action == "no":
        await callback.answer("Tahrirlash bekor qilindi.", show_alert=True)
        await state.clear()
        
        try:
            await callback.message.delete()
        except:
            pass
            
        # 🔥 Pydantic frozen xatosini chetlab o'tish uchun ob'ekt nusxasini (copy) yaratamiz
        cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
        
        from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
        await process_edit_anime_menu(cloned_callback, session)
        return

    # ✅ AGAR ADMIN "HA" DEB TASDIQLASA
    await callback.answer("Saqlanmoqda...")
    
    try:
        service = AnimeService(session=session)
        success = await service.update_anime(anime_id=anime_id, update_data={"title": new_name})
    except Exception as e:
        logger.error(f"DB Update error: {e}")
        success = False

    if not success:
        await callback.message.edit_caption(
            caption="❌ <b>Xatolik:</b> Ma'lumotni bazaga saqlashda texnik xato yuz berdi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⚙️ Tahrirlash bo'limiga qaytish", callback_data=f"force_refresh_edit:{anime_id}")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tahrirlashga qaytish", callback_data=f"force_refresh_edit:{anime_id}")]
    ])
    
    await callback.message.edit_caption(
        caption=f"✅ <b>Anime nomi muvaffaqiyatli o'zgartirildi!</b>\n\n✨ Yangi nom: <u>{new_name}</u>",
        reply_markup=success_kb,
        parse_mode="HTML"
    )
    await state.clear()


# =====================================================================
# 📑 4-QADAM: Majburiy qaytish handler (TUZATILDI)
# =====================================================================
@router.callback_query(F.data.startswith("force_refresh_edit:"))
async def force_refresh_edit_menu(callback: CallbackQuery, session: Any):
    anime_id = int(callback.data.split(":")[1])
    
    try:
        await callback.message.delete()
    except:
        pass
        
    # 🔥 Pydantic frozen xatosini chetlab o'tish uchun model_copy dan foydalanamiz
    cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
    
    from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
    await process_edit_anime_menu(cloned_callback, session)














# =====================================================================
# 📑 1-QADAM: "🌐 Tili" tugmasi bosilganda holatga (State) o'tkazish
# =====================================================================
@router.callback_query(F.data.startswith("edit_field:lang:"))
async def edit_anime_lang_start(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split(":")[2])
    
    # Ma'lumotlarni holat keshiga yozib qo'yamiz
    await state.update_data(edit_anime_id=anime_id, main_msg_id=callback.message.message_id)
    
    # State-ni til kutish holatiga o'tkazamiz
    await state.set_state(EditAnimeStates.waiting_for_new_lang)
    
    text = (
        "🌐 <b>Yangi til (tarjima) formatini kiritish:</b>\n\n"
        "Iltimos, animening yangi tillarini kiriting (Masalan: <code>O'zbekcha</code> yoki <code>Subtitr</code>).\n"
        "Matn ko'rinishida botga yuboring:"
    )
    
    await callback.answer("Til tahrirlash boshlandi")
    try:
        await callback.message.edit_caption(caption=text, reply_markup=None, parse_mode="HTML")
    except TelegramBadRequest:
        pass


# =====================================================================
# 📑 2-QADAM: Admin yangi til yuborganda uni ushlash va Ha/Yo'q so'rash
# =====================================================================
@router.message(EditAnimeStates.waiting_for_new_lang, F.text)
async def process_new_anime_lang(message: Message, state: FSMContext):
    new_lang = message.text.strip()
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    main_msg_id = state_data.get("main_msg_id")
    
    # 🗑 Toza interfeys uchun admin yuborgan xabarni darhol o'chiramiz
    try:
        await message.delete()
    except Exception:
        pass
        
    # Yangi kiritilgan tilni state-ga saqlaymiz
    await state.update_data(new_anime_lang=new_lang)
    
    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_lang_edit:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_lang_edit:no")
        ]
    ])
    
    confirm_text = (
        f"❓ <b>Anime tili o'zgartirilsinmi?</b>\n\n"
        f"🌐 Yangi til ma'lumoti: <u>{new_lang}</u>"
    )
    
    # Tasdiqlash holatiga o'tkazib, tepadagi poster matnini o'zgartiramiz
    await state.set_state(EditAnimeStates.waiting_for_confirmation)
    try:
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            caption=confirm_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Tilni tasdiqlash xabarida xato: {e}")


# =====================================================================
# 📑 3-QADAM: Til tasdiqlanganda (Ha yoki Yo'q) bosilishi
# =====================================================================
@router.callback_query(EditAnimeStates.waiting_for_confirmation, F.data.startswith("confirm_lang_edit:"))
async def save_or_cancel_anime_lang(callback: CallbackQuery, state: FSMContext, session: Any):
    action = callback.data.split(":")[1]
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    new_lang = state_data.get("new_anime_lang")
    
    # ❌ AGAR ADMIN "YO'Q" DESB REJANI BEKOR QILSA
    if action == "no":
        await callback.answer("Tahrirlash bekor qilindi.", show_alert=True)
        await state.clear()
        
        try:
            await callback.message.delete()
        except:
            pass
            
        # Pydantic muzlatilgan ob'ekt xatosini chetlab o'tib, toza nusxa bilan bosh menyuga qaytamiz
        cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
        from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
        await process_edit_anime_menu(cloned_callback, session)
        return

    # ✅ AGAR ADMIN "HA" DEB TASDIQLASA
    await callback.answer("Bazaga yozilmoqda...")
    
    # Models.py dagi 'languages' ustuniga moslab yangilaymiz.
    # Agar bazada tillar massiv (List) formatida bo'lsa: [new_lang] ko'rinishida yuboramiz.
    try:
        service = AnimeService(session=session)
        # Loyihangiz arxitekturasidagi ARRAY mosligi uchun [new_lang] formatida saqlaymiz
        success = await service.update_anime(anime_id=anime_id, update_data={"languages": [new_lang]})
    except Exception as e:
        logger.error(f"DB Update Lang error: {e}")
        success = False

    if not success:
        await callback.message.edit_caption(
            caption="❌ <b>Xatolik:</b> Til ma'lumotini saqlashda texnik xato yuz berdi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⚙️ Tahrirlash bo'limiga qaytish", callback_data=f"force_refresh_edit:{anime_id}")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Muvaffaqiyatli xabar va refresh tugmasi
    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tahrirlashga qaytish", callback_data=f"force_refresh_edit:{anime_id}")]
    ])
    
    await callback.message.edit_caption(
        caption=f"✅ <b>Anime tili muvaffaqiyatli yangilandi!</b>\n\n🌐 Yangi til: <u>{new_lang}</u>",
        reply_markup=success_kb,
        parse_mode="HTML"
    )
    await state.clear()












# =====================================================================
# 📑 1-QADAM: "📝 Tasnif" tugmasi bosilganda holatga (State) o'tkazish
# =====================================================================
@router.callback_query(F.data.startswith("edit_field:desc:"))
async def edit_anime_desc_start(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split(":")[2])
    
    # Ma'lumotlarni holat keshiga yozib qo'yamiz
    await state.update_data(edit_anime_id=anime_id, main_msg_id=callback.message.message_id)
    
    # State-ni tasnif kutish holatiga o'tkazamiz
    await state.set_state(EditAnimeStates.waiting_for_new_desc)
    
    text = (
        "📝 <b>Yangi tasnif (tavsif) kiritish:</b>\n\n"
        "Iltimos, animening yangi tasnifini botga xabar shaklida yuboring.\n"
        "<i>(Xohlasangiz uzun matn yuborishingiz mumkin)</i>"
    )
    
    await callback.answer("Tasnif tahrirlash boshlandi")
    try:
        await callback.message.edit_caption(caption=text, reply_markup=None, parse_mode="HTML")
    except TelegramBadRequest:
        pass


# =====================================================================
# 📑 2-QADAM: Admin yangi tasnif yuborganda uni ushlash va Ha/Yo'q so'rash
# =====================================================================
@router.message(EditAnimeStates.waiting_for_new_desc, F.text)
async def process_new_anime_desc(message: Message, state: FSMContext):
    new_desc = message.text.strip()
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    main_msg_id = state_data.get("main_msg_id")
    
    # 🗑 Toza interfeys uchun admin yuborgan xabarni darhol o'chiramiz
    try:
        await message.delete()
    except Exception:
        pass
        
    # Yangi kiritilgan tasnifni state-ga saqlaymiz
    await state.update_data(new_anime_desc=new_desc)
    
    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_desc_edit:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_desc_edit:no")
        ]
    ])
    
    # Agar tasnif juda uzun bo'lsa, tasdiqlash oynasi chiroyli ko'rinishi uchun uni qisqartirib ko'rsatamiz
    preview_desc = new_desc[:200] + "..." if len(new_desc) > 200 else new_desc
    
    confirm_text = (
        f"❓ <b>Anime tasnifi o'zgartirilsinmi?</b>\n\n"
        f"📝 <b>Yangi tasnif:</b>\n"
        f"<blockquote expandable>{preview_desc}</blockquote>"
    )
    
    # Tasdiqlash holatiga o'tkazib, tepadagi poster matnini o'zgartiramiz
    await state.set_state(EditAnimeStates.waiting_for_confirmation)
    try:
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            caption=confirm_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Tasnifni tasdiqlash xabarida xato: {e}")


# =====================================================================
# 📑 3-QADAM: Tasnif tasdiqlanganda (Ha yoki Yo'q) bosilishi
# =====================================================================
@router.callback_query(EditAnimeStates.waiting_for_confirmation, F.data.startswith("confirm_desc_edit:"))
async def save_or_cancel_anime_desc(callback: CallbackQuery, state: FSMContext, session: Any):
    action = callback.data.split(":")[1]
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    new_desc = state_data.get("new_anime_desc")
    
    # ❌ AGAR ADMIN "YO'Q" DEB BEKOR QILSA
    if action == "no":
        await callback.answer("Tahrirlash bekor qilindi.", show_alert=True)
        await state.clear()
        
        try:
            await callback.message.delete()
        except:
            pass
            
        # Pydantic muzlatilgan ob'ekt xatosini chetlab o'tib, toza nusxa bilan bosh menyuga qaytamiz
        cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
        from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
        await process_edit_anime_menu(cloned_callback, session)
        return

    # ✅ AGAR ADMIN "HA" DEB TASDIQLASA
    await callback.answer("Bazaga yozilmoqda...")
    
    try:
        service = AnimeService(session=session)
        # Siz yozgan o'sha universal update_anime funksiyasi orqali 'description' ustunini yangilaymiz
        success = await service.update_anime(
            anime_id=anime_id, 
            update_data={"description": new_desc}
        )
    except Exception as e:
        logger.error(f"DB Update Desc error: {e}")
        success = False

    if not success:
        await callback.message.edit_caption(
            caption="❌ <b>Xatolik:</b> Tasnifni saqlashda texnik xato yuz berdi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⚙️ Tahrirlash bo'limiga qaytish", callback_data=f"force_refresh_edit:{anime_id}")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Muvaffaqiyatli xabar va refresh tugmasi
    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tahrirlashga qaytish", callback_data=f"force_refresh_edit:{anime_id}")]
    ])
    
    await callback.message.edit_caption(
        caption="✅ <b>Anime tasnifi muvaffaqiyatli yangilandi!</b>",
        reply_markup=success_kb,
        parse_mode="HTML"
    )
    await state.clear()








# =====================================================================
# 📑 1-QADAM: "📅 Yili" tugmasi bosilganda holatga (State) o'tkazish
# =====================================================================
@router.callback_query(F.data.startswith("edit_field:year:"))
async def edit_anime_year_start(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split(":")[2])
    
    # Kerakli ID larni holat keshiga yozib qo'yamiz
    await state.update_data(edit_anime_id=anime_id, main_msg_id=callback.message.message_id)
    
    # State-ni yil kutish holatiga o'tkazamiz
    await state.set_state(EditAnimeStates.waiting_for_new_year)
    
    text = (
        "📅 <b>Yangi chiqish yilini kiritish:</b>\n\n"
        "Iltimos, animening yangi yilini faqat son shaklida kiriting.\n"
        "<i>(Cheklov: 1800 - 2050 yillar oralig'ida bo'lishi kerak)</i>"
    )
    
    await callback.answer("Yil tahrirlash boshlandi")
    try:
        await callback.message.edit_caption(caption=text, reply_markup=None, parse_mode="HTML")
    except TelegramBadRequest:
        pass


# =====================================================================
# 📑 2-QADAM: Admin yangi yil yuborganda tekshirish (Validatsiya) va Ha/Yo'q so'rash
# =====================================================================
@router.message(EditAnimeStates.waiting_for_new_year, F.text)
async def process_new_anime_year(message: Message, state: FSMContext):
    input_text = message.text.strip()
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    main_msg_id = state_data.get("main_msg_id")
    
    # 🗑 Toza interfeys uchun admin yuborgan xabarni darhol o'chiramiz
    try:
        await message.delete()
    except Exception:
        pass

    # 🛑 VALIDATSIYA: Kiritilgan matn faqat son ekanligini tekshiramiz
    if not input_text.isdigit():
        error_text = (
            "⚠️ <b>Xato kiritish!</b>\n\n"
            f"Siz kiritgan ma'lumot: <code>{input_text}</code>\n"
            "Iltimos, yilni faqat **butun son** shaklida yuboring! (Masalan: 2024)"
        )
        try:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id, message_id=main_msg_id, caption=error_text, reply_markup=None, parse_mode="HTML"
            )
        except: pass
        return

    new_year = int(input_text)

    # 🛑 VALIDATSIYA: 1800 va 2050 oralig'ida ekanligini tekshiramiz
    if not (1800 <= new_year <= 2050):
        error_text = (
            "⚠️ <b>Yil oralig'i noto'g'ri!</b>\n\n"
            f"Siz kiritgan yil: <code>{new_year}</code>\n"
            "Yil faqat <b>1800 va 2050 yillar oralig'ida</b> bo'lishi shart!"
        )
        try:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id, message_id=main_msg_id, caption=error_text, reply_markup=None, parse_mode="HTML"
            )
        except: pass
        return

    # Validatsiyadan o'tsa, keshga saqlaymiz
    await state.update_data(new_anime_year=new_year)
    
    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_year_edit:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_year_edit:no")
        ]
    ])
    
    confirm_text = (
        f"❓ <b>Anime chiqish yili o'zgartirilsinmi?</b>\n\n"
        f"📅 Yangi yil: <code>{new_year}</code>"
    )
    
    # Tasdiqlash holatiga o'tkazib, tepadagi poster matnini o'zgartiramiz
    await state.set_state(EditAnimeStates.waiting_for_confirmation)
    try:
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            caption=confirm_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Yilni tasdiqlash xabarida xato: {e}")


# =====================================================================
# 📑 3-QADAM: Yil tasdiqlanganda (Ha yoki Yo'q) bosilishi
# =====================================================================
@router.callback_query(EditAnimeStates.waiting_for_confirmation, F.data.startswith("confirm_year_edit:"))
async def save_or_cancel_anime_year(callback: CallbackQuery, state: FSMContext, session: Any):
    action = callback.data.split(":")[1]
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    new_year = state_data.get("new_anime_year")
    
    # ❌ AGAR ADMIN "YO'Q" DEB BEKOR QILSA
    if action == "no":
        await callback.answer("Tahrirlash bekor qilindi.", show_alert=True)
        await state.clear()
        
        try:
            await callback.message.delete()
        except:
            pass
            
        # Pydantic muzlatilgan ob'ekt xatosini aylanib o'tib, toza nusxa bilan bosh menyuga qaytamiz
        cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
        from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
        await process_edit_anime_menu(cloned_callback, session)
        return

    # ✅ AGAR ADMIN "HA" DEB TASDIQLASA
    await callback.answer("Bazaga yozilmoqda...")
    
    try:
        service = AnimeService(session=session)
        # Siz yozgan o'sha universal update_anime funksiyasi orqali 'year' ustunini butun son holatida yangilaymiz
        success = await service.update_anime(
            anime_id=anime_id, 
            update_data={"year": new_year}
        )
    except Exception as e:
        logger.error(f"DB Update Year error: {e}")
        success = False

    if not success:
        await callback.message.edit_caption(
            caption="❌ <b>Xatolik:</b> Yil ma'lumotini saqlashda texnik xato yuz berdi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⚙️ Tahrirlash bo'limiga qaytish", callback_data=f"force_refresh_edit:{anime_id}")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Muvaffaqiyatli xabar va refresh tugmasi
    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tahrirlashga qaytish", callback_data=f"force_refresh_edit:{anime_id}")]
    ])
    
    await callback.message.edit_caption(
        caption=f"✅ <b>Anime chiqish yili muvaffaqiyatli o'zgartirildi!</b>\n\n📅 Yangi yil: <code>{new_year}</code>",
        reply_markup=success_kb,
        parse_mode="HTML"
    )
    await state.clear()












# =====================================================================
# 📑 1-QADAM: "🖼 Poster" tugmasi bosilganda holatga (State) o'tkazish
# =====================================================================
@router.callback_query(F.data.startswith("edit_field:poster:"))
async def edit_anime_poster_start(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split(":")[2])
    
    # Kelajakda o'chirish yoki tahrirlash uchun ID larni saqlaymiz
    await state.update_data(edit_anime_id=anime_id, main_msg_id=callback.message.message_id)
    
    # State-ni poster kutish holatiga o'tkazamiz
    await state.set_state(EditAnimeStates.waiting_for_new_poster)
    
    text = (
        "🖼 <b>Yangi anime posterini (rasm) yuklash:</b>\n\n"
        "Iltimos, animening yangi posterini botga rasm (Photo) ko'rinishida yuboring.\n"
        "<i>(Eslatma: Rasm fayl (Document) shaklida emas, oddiy rasm formatida bo'lsin!)</i>"
    )
    
    await callback.answer("Poster tahrirlash boshlandi")
    try:
        # Asosiy xabar caption matnini o'zgartirib yo'riqnomani ko'rsatamiz
        await callback.message.edit_caption(caption=text, reply_markup=None, parse_mode="HTML")
    except TelegramBadRequest:
        pass


# =====================================================================
# 📑 2-QADAM: Admin yangi rasm yuborganda uni ushlash va tasdiqlash so'rash
# =====================================================================
@router.message(EditAnimeStates.waiting_for_new_poster, F.photo)
async def process_new_anime_poster(message: Message, state: FSMContext):
    # Eng yuqori sifatli rasm file_id sini olamiz
    new_poster_id = message.photo[-1].file_id
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    main_msg_id = state_data.get("main_msg_id")
    
    # ❌ ADMIN YUBORGAN RASMNI O'CHIRMAYMIZ (Telegram serverida yaroqli qolishi uchun)
    # 🗑 Lekin tepadagi bot yuborgan yo'riqnoma xabarini butunlay o'chirib tashlaymiz
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=main_msg_id)
    except Exception:
        pass
        
    # Yangi rasm ID sini state-ga saqlaymiz
    await state.update_data(new_anime_poster=new_poster_id)
    
    # Tasdiqlash tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_poster_edit:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_poster_edit:no")
        ]
    ])
    
    confirm_text = "❓ <b>Ushbu rasm anime uchun yangi poster etib belgilansinmi?</b>"
    
    # Yangi xabar qilib pastdan tasdiqlash uchun rasm ko'rinishida yuboramiz
    await state.set_state(EditAnimeStates.waiting_for_confirmation)
    
    # Bu yangi yuborilgan tasdiqlash xabarining ID sini ham saqlab qo'yamiz (oxirida tozalash uchun)
    confirm_msg = await message.reply_photo(
        photo=new_poster_id,
        caption=confirm_text,
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.update_data(confirm_msg_id=confirm_msg.message_id)


# =====================================================================
# 📑 3-QADAM: Poster tasdiqlanganda (Ha yoki Yo'q) bosilishi (ZAMonaviy VARIANT)
# =====================================================================
@router.callback_query(EditAnimeStates.waiting_for_confirmation, F.data.startswith("confirm_poster_edit:"))
async def save_or_cancel_anime_poster(callback: CallbackQuery, state: FSMContext, session: Any):
    action = callback.data.split(":")[1]
    state_data = await state.get_data()
    
    anime_id = state_data.get("edit_anime_id")
    new_poster = state_data.get("new_anime_poster")
    
    # ❌ AGAR ADMIN "YO'Q" DEB BEKOR QILSA
    if action == "no":
        await callback.answer("Tahrirlash bekor qilindi.", show_alert=True)
        await state.clear()
        try:
            await callback.message.delete()
        except:
            pass
            
        cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
        from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
        await process_edit_anime_menu(cloned_callback, session)
        return

    # ✅ AGAR ADMIN "HA" DEB TASDIQLASA
    await callback.answer("Poster yangilanmoqda...")
    
    try:
        service = AnimeService(session=session)
        
        # 🔥 DIQQAT: models.py faylida ustun nomi 'poster_id' bo'lgani uchun 
        # kalitni qat'iy ravishda 'poster_id' deb uzatamiz!
        success = await service.update_anime(
            anime_id=anime_id, 
            update_data={"poster_id": str(new_poster)}
        )
        
        if success:
            # 1. SQLAlchemy session keshini yangilashga majburlaymiz
            if hasattr(session, "expire_all"):
                session.expire_all()
            elif hasattr(session, "_session") and hasattr(session._session, "expire_all"):
                session._session.expire_all()
                
            # 2. Ro'yxatlar keshini va qidiruv xaritasini ham majburiy tozalaymiz
            await service.cache.invalidate("anime", "all", broadcast=True)
            await service.cache.invalidate("search_map", "all", broadcast=True)
            
    except Exception as e:
        logger.error(f"🚨 Poster yangilashda DB/Sessiya xatosi: {e}")
        success = False

    if not success:
        await callback.message.answer(
            "❌ <b>Xatolik:</b> Posterni saqlashda texnik xato yuz berdi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⚙️ Tahrirlash bo'limiga qaytish", callback_data=f"force_refresh_edit:{anime_id}")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Tasdiqlash xabarini o'chiramiz
    try:
        await callback.message.delete()
    except:
        pass

    # FSM holatini tozalaymiz
    await state.clear()
    
    # Yangilangan toza ma'lumot (yangi poster_id) bilan menyuni qayta chizamiz
    cloned_callback = callback.model_copy(update={"data": f"edit_anime:{anime_id}"})
    from handlers.admin_panel.admin_anime.edit_anime import process_edit_anime_menu
    await process_edit_anime_menu(cloned_callback, session)