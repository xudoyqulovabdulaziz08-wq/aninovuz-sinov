from aiogram import Router, html, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from services.user_service import UserService
from config import config

CREATOR_ID = config.CREATOR_ID
router = Router()


@router.message(F.photo)
async def get_bot_specific_file_id(message: Message):
    # Bot aynan o'zi ko'rayotgan eng katta o'lchamli rasm ID-sini logga chiqaradi
    photo_id = message.photo[-1].file_id
    print(f"\n\n🔥 BOTINGIZ UCHUN TO'G'RI FILE_ID: {photo_id}\n\n")
    await message.answer(f"✅ Rasm ID-si olindi! Uni nusxalab kodga qo'ying.\n\n<code>{photo_id}</code>")

# 🎯 UNIVERSAL START INTERFEYSI (Ham yangi yuborish, ham edit qilish uchun)
async def send_or_edit_start_menu(target: Message | CallbackQuery, user_id: int, username: str):
    """
    Ushbu funksiya target turi Message bo'lsa yangi xabar yuboradi,
    CallbackQuery bo'lsa mavjud xabarni media edit (tahrirlash) qiladi.
    """
    start_image_file_id = "AgACAgIAAxkBAAI8Vmo2h33mXWFJrVt2WytylhrKnSRKAAJHGGsbZ6WxSVOJWvc1e0TUAQADAgADdwADPAQ" 
    
    welcome_text = (
        f"👋 Xush kelibsiz, {html.bold(username)}!\n\n"
        f"🎬 {html.bold('AniNovuz')} — siz qidirgan eng sara, sifatli va sevimli animelar makoniga qadam qo'ydingiz.\n\n"
        f"⚡️ Quyidagi menyudan foydalanib, darhol tomosha qilishni boshlashingiz mumkin:"
    )
    
    start_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Qidiruv bo'limi", callback_data="search_menu", style="primary")],
            [
                InlineKeyboardButton(text="Reklama berish 📢", callback_data="advertise", style="primary"),
                InlineKeyboardButton(text="Qo'llanma 📖", callback_data="guide", style="primary")
            ],
            [InlineKeyboardButton(text="VIP olish 💎", callback_data="buy_vip", style="success")],
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


# 1️⃣ /start BUYRUG'I KELGANDA
@router.message(CommandStart())
async def cmd_start(message: Message, user: dict, user_service: UserService):
    user_id = message.from_user.id
    username = message.from_user.username or "do'stim"
    user_status = user.get('status', 'user').lower()
    
    # Asosiy menyuni yangi xabar sifatida yuboramiz
    await send_or_edit_start_menu(message, user_id, username)

    # Admin/Creator panellari (Reply keyboard baribir alohida xabarda chiqishi shart)
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


# 2️⃣ ORQAGA TUGMASI BOSILGANDA (Boshqa fayllardan ham chaqirish mumkin)
@router.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "do'stim"
    
    # Asosiy menyuni mavjud xabarni EDIT qilish orqali qaytaramiz
    await send_or_edit_start_menu(callback, user_id, username)