import logging
import asyncio
from aiogram import Router, F, html
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.anime_service import AnimeService
from aiogram.fsm.state import StatesGroup, State
from typing import Any

class AddEpisodeStates(StatesGroup):
    waiting_for_videos = State()  # Videolarni qabul qilish holati





router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("add_episode:"))
async def start_add_episode(callback: CallbackQuery, state: FSMContext, session: Any):
    await callback.answer()
    anime_id = int(callback.data.split(":")[1])
    
    # Anime ma'lumotlarini bazadan olamiz (oxirgi qism raqamini bilish uchun)
    service = AnimeService(session=session)
    anime = await service.get_anime(anime_id)
    
    if not anime:
        await callback.message.answer("❌ Anime topilmadi!")
        return

    # Mavjud qismlar sonini aniqlaymiz
    episodes = anime.get("episodes", [])
    next_ep = len(episodes) + 1

    # Eski xabarni o'chiramiz
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Admin holatini o'zgartiramiz va anime_id ni saqlaymiz
    await state.set_state(AddEpisodeStates.waiting_for_videos)
    await state.update_data(anime_id=anime_id, video_list=[], next_ep=next_ep)

    text = (
        f"🎬 {html.bold(anime['title'])} animesiga qism qo‘shish\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📹 Iltimos, qism videolarini ketma-ketlikda tashlang.\n"
        f"ℹ️ Tizim avtomatik ravish manually {html.code(f'{next_ep}-qismdan')} boshlab raqamlaydi.\n\n"
        f"⚠️ {html.italic('Bir nechta videoni belgilab birdiga tashlashingiz ham mumkin.')}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga (Bekor qilish)", callback_data=f"v_anime:{anime_id}:1", style="danger")]
    ])

    await callback.message.answer(text=text, reply_markup=kb, parse_mode="HTML")








# Parallel so'rovlarni tartibga solish uchun global lock (FSM bilan xavfsiz integratsiya)
state_locks = {}

@router.message(AddEpisodeStates.waiting_for_videos, F.video)
async def collect_anime_videos_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Har bir foydalanuvchi uchun alohida blokirovka (Lock) yaratamiz
    if user_id not in state_locks:
        state_locks[user_id] = asyncio.Lock()

    async with state_locks[user_id]:
        current_data = await state.get_data()
        video_list = current_data.get("video_list", [])
        
        # Kelgan videoni ro'yxatga qo'shamiz (file_id va uning unikal telegram kodi)
        file_id = message.video.file_id
        video_list.append(file_id)
        
        await state.update_data(video_list=video_list)
        
        # Avvalgi taymer bo'lsa uni o'chiramiz (Debounce effekti)
        timer_task = current_data.get("timer_task")
        if timer_task:
            timer_task.cancel()
        
        # Yangi asinxron kutish taymerini yaratamiz (1.5 soniya)
        # Agar 1.5 soniya ichida yangi video kelmasa, demak yuborish tugadi.
        loop = asyncio.get_running_loop()
        new_task = loop.create_task(wait_and_finish_collection(message, state))
        await state.update_data(timer_task=new_task)









async def wait_and_finish_collection(message: Message, state: FSMContext):
    try:
        # 1.5 soniya yangi xabarlar kelishini kutamiz
        await asyncio.sleep(1.5)
        
        # Kutish yakunlandi, ma'lumotlarni yig'amiz
        data = await state.get_data()
        video_list = data.get("video_list", [])
        anime_id = data.get("anime_id")
        next_ep = data.get("next_ep", 1)
        
        if not video_list:
            return

        total_added = len(video_list)
        end_ep = next_ep + total_added - 1

        summary_text = (
            f"📦 {html.bold('Videolar muvaffaqiyatli qabul qilindi!')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📥 Jami yuklangan fayllar: {html.bold(total_added)} ta\n"
            f"🔢 Qismlar oralig‘i: {html.code(f'{next_ep}-qismdan')} -> {html.code(f'{end_ep}-qismgacha')}\n\n"
            f"✨ Endi quyidagi amallardan birini tanlang:"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 Faqat bazaga saqlash", callback_data=f"save_episodes_db:{anime_id}", style="primary"),
                InlineKeyboardButton(text="📢 Kanalga e‘lon qilish", callback_data=f"publish_episodes_chan:{anime_id}", style="primary")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"v_anime:{anime_id}:1", style="danger")
            ]
        ])

        await message.answer(text=summary_text, reply_markup=kb, parse_mode="HTML")
        
    except asyncio.CancelledError:
        # Agar taymer bekor qilingan bo'lsa (ya'ni 1.5 soniya ichida yangi video kelgan)
        pass
    finally:
        # Lock tozalash
        user_id = message.from_user.id
        if user_id in state_locks:
            state_locks.pop(user_id, None)









@router.callback_query(F.data.startswith("save_episodes_db:"), AddEpisodeStates.waiting_for_videos)
async def save_episodes_to_database(callback: CallbackQuery, state: FSMContext, session: Any):
    await callback.answer("Saqlash boshlandi...", show_alert=False)
    
    data = await state.get_data()
    video_list = data.get("video_list", [])
    anime_id = data.get("anime_id")
    next_ep = data.get("next_ep", 1)

    if not video_list:
        await callback.message.answer("❌ Saqlash uchun videolar topilmadi. Jarayon bekor qilindi.")
        await state.clear()
        return

    # SafeSession'ni uyg'otamiz (Siz topgan eng muhim bug-fix)
    if hasattr(session, "_ensure_session"):
        await session._ensure_session()

    service = AnimeService(session=session)
    success_count = 0

    try:
        # Har bir videoni o'z tartib raqami bilan bazaga yozamiz
        for index, file_id in enumerate(video_list):
            current_episode_num = next_ep + index
            
            # models.py dagi Episode va AnimeRepository.add_episode chaqiriladi
            ok = await service.add_episode(
                anime_id=anime_id,
                episode_num=current_episode_num,
                file_id=file_id
            )
            if ok:
                success_count += 1

        # Eski xabarni o'chiramiz
        try:
            await callback.message.delete()
        except Exception:
            pass

        final_text = (
            f"✅ {html.bold('Muvaffaqiyatli saqlandi!')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Baza va kesh xotirasiga jami {html.bold(success_count)} ta yangi qism qo‘shildi."
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Anime sahifasiga", callback_data="list_anime_page:1", style="danger")]
        ])
        
        await callback.message.answer(text=final_text, reply_markup=kb, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Qismlarni saqlashda xatolik: {e}")
        await callback.message.answer("❌ Tizimda qismlarni saqlashda jiddiy xatolik yuz berdi.")
    finally:
        # FSM ni tozalaymiz
        await state.clear()