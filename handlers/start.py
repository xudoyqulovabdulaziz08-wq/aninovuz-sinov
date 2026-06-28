import logging
from typing import Any
from aiogram import Router, html, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from services.user_service import UserService
from config import config
from handlers.search_menu.anime_card import send_anime_card
from aiogram.fsm.context import FSMContext
logger = logging.getLogger("StartRouter")
CREATOR_ID = config.CREATOR_ID
router = Router()




# 🎯 UNIVERSAL START INTERFEYSI (Ham yangi yuborish, ham edit qilish uchun)
async def send_or_edit_start_menu(target: Message | CallbackQuery, user_id: int, username: str):
    """
    Ushbu funksiya target turi Message bo'lsa yangi xabar yuboradi,
    CallbackQuery bo'lsa mavjud xabarni media edit (tahrirlash) qiladi.
    """
    start_image_file_id = "AgACAgIAAxkBAAFNp7dqQLlLE4I3g74IGAPkA534rlh7jAACXBprGyriCEpz_27sf60NogEAAwIAA3kAAzwE" 
    
    welcome_text = (
        f"👋 Xush kelibsiz, {html.bold(username)}!\n\n"
        f"🎬 {html.bold('AniNovuz')} — siz qidirgan eng sara, sifatli va sevimli animelar makoniga qadam qo‘ydingiz.\n\n"
        f"⚡️ Quyidagi menyudan foydalanib, darhol tomosha qilishni boshlashingiz mumkin:"
    )
    
    start_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Qidiruv bo'limi", callback_data="search_menu", style="primary")],
            [
                InlineKeyboardButton(text="Reklama berish 📢", callback_data="advertise", style="primary"),
                InlineKeyboardButton(text="Qo'llanma 📖", callback_data="guide", style="primary")
            ],
            [InlineKeyboardButton(text="VIP 💎", callback_data="buy_vip", style="success")],
            [InlineKeyboardButton(text="💬 Yordam", callback_data="support", style="danger")]
        ]
    )

    # Agar foydalanuvchi inline tugmani bosgan bo'lsa (CallbackQuery) - EDIT qilamiz
    if isinstance(target, CallbackQuery):
        await target.message.edit_media(
            media=InputMediaPhoto(
                media=start_image_file_id,
                caption=welcome_text,
                parse_mode="HTML"
            ),
            reply_markup=start_keyboard
        )
        await target.answer() # Telegram yuklanish belgisini olib tashlash uchun
        
    # Agar foydalanuvchi /start deb yozgan bo'lsa (Message) - YANGI xabar yuboramiz
    elif isinstance(target, Message):
        try:
            await target.delete() # Foydalanuvchi yozgan /start matnini o'chirish
        except:
            pass
            
        await target.answer_photo(
            photo=start_image_file_id,
            caption=welcome_text,
            reply_markup=start_keyboard,
            parse_mode="HTML"
        )


# 1️⃣ /start BUYRUG'I KELGANDA (Deep-Linking qo'llab-quvvatlaydi)
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: Any, user: dict, user_service: UserService, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or "do'stim"
    user_status = user.get('status', 'user').lower()
    
    # 🚀 KANAL TUGMASIDAN PARAMETR KELGANDA (Masalan: /start anime_15,)
    if command.args:
        # 🌟 "🔍 Yuborilmoqda..." matni bilan vaqtinchalik xabarni saqlaymiz
        waiting_msg = await message.answer("🔍 Yuborilmoqda...")
        
        clean_args = command.args.strip().rstrip(",")
        if clean_args.startswith("anime_"):
            try:
                anime_id = int(clean_args.split("_")[1])
                
                from services.anime_service import AnimeService
                service = AnimeService(session=session)
                anime = await service.get_anime(anime_id)
                
                if anime:
                    # 🚀 "message" o'rniga "waiting_msg" beriladi, shunda poster yuklangach u o'chib ketadi!
                    await send_anime_card(waiting_msg, anime, session)
                    return
                else:
                    # Anime topilmasa, vaqtinchalik xabarni o'chirib tashlaymiz
                    await waiting_msg.delete()
                    
            except Exception as ex:
                logger.error(f"❌ Deep link ishlashida xatolik: {ex}")
                # Xatolik yuz bersa ham vaqtinchalik xabar o'chiriladi
                try:
                    await waiting_msg.delete()
                except:
                    pass

    # Agarda oddiy start bo'lsa yoki anime topilmasa, asosiy menyuni chiqaradi
    await send_or_edit_start_menu(message, user_id, username)

    # Admin/Creator panellari
    if user_id == CREATOR_ID:
        creator_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⚙️ Creator Paneli"), KeyboardButton(text="🛠 Admin Paneli")]],
            resize_keyboard=True
        )
        await message.answer("👑 Tizim asoschisi! Barcha boshqaruv panellari faollashtirildi:", reply_markup=creator_keyboard)
        
    elif user_status == 'admin':
        admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🛠 Admin Paneli")]],
            resize_keyboard=True
        )
        await message.answer("🛡 Tizim administratori tan olindi. Admin boshqaruv paneli faollashtirildi:", reply_markup=admin_keyboard)


# 2️⃣ ORQAGA TUGMASI BOSILGANDA
@router.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "do'stim"
    await send_or_edit_start_menu(callback, user_id, username)


# 3️⃣ 🔄 OBUNANI TASDIQLASH TUGMASI BOSILGANDA (Deep-linkni hisobga oluvchi mukammal handler)
@router.callback_query(F.data.startswith("check_sub"))
async def check_sub_callback_handler(callback: CallbackQuery, session: Any, state: FSMContext, user_service: UserService):
    await callback.answer("🎉 Rahmat, obuna muvaffaqiyatli tasdiqlandi!", show_alert=True)
    user_id = callback.from_user.id
    username = callback.from_user.username or "do'stim"
    
    # Eskidan qolib ketgan majburiy obuna blok-xabarini butunlay o'chirib tashlaymiz
    try:
        await callback.message.delete()
    except:
        pass

    # Tugma ma'lumotini tekshiramiz (Masalan: check_sub:anime_15 bormi?)
    data_parts = callback.data.split(":")
    
    if len(data_parts) > 1 and data_parts[1].startswith("anime_"):
        # 🚀 Foydalanuvchi obunani tugatib qaytdi va unga o'zi qidirgan animeni ko'rsatamiz!
        anime_param = data_parts[1] # "anime_15"
        try:
            anime_id = int(anime_param.split("_")[1])
            
            from services.anime_service import AnimeService
            service = AnimeService(session=session)
            anime = await service.get_anime(anime_id)
            
            if anime:
                # 💡 Bu yerda start.py dagi o'sha ramkali daxshatli anime caption tayyorlash kodingiz keladi
                title = anime.get("title", "Nomsiz anime")
                caption = f"🎬 <b>{title}</b>\n\nObuna tasdiqlandi! Qismlarni tomosha qilishingiz mumkin."
                
                user_anime_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📹 Qismlarni tomosha qilish", callback_data=f"show_episodes_user:{anime_id}", style="primary")],
                    [InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="back_to_start", style="danger")]
                ])
                
                poster_id = anime.get("poster_id")
                if poster_id:
                    await callback.message.answer_photo(photo=poster_id, caption=caption, reply_markup=user_anime_kb, parse_mode="HTML")
                else:
                    await callback.message.answer(text=caption, reply_markup=user_anime_kb, parse_mode="HTML")
                return
        except Exception as ex:
            logger.error(f"❌ Check sub ichida animeni yuklashda xato: {ex}")

    # Agar hech qanday deep link bo'lmasa, oddiy bosh menyuni chiqarib beramiz
    await send_or_edit_start_menu(callback.message, user_id, username)