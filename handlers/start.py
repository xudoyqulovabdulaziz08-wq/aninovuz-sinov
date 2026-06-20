from aiogram import Router, html, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService

router = Router()




@router.message(CommandStart())
async def cmd_start(message: Message, user: dict, user_service: UserService):
    user_id = message.from_user.id
    username = message.from_user.username or "do'stim"
    
    # 🔥 Telegram serveridagi doimiy va eng sifatli rasm ID-si
    start_image_file_id = "AgACAgIAAxkBAAI8Rmo2fma5AXPIoM2q4ZCKKizFvTVwAAIyGGsbedywST6juNnOr2gkAQADAgADdwADPAQ" 
    
    # 📝 Mukammal va o'ziga xos matn
    welcome_text = (
        f"👋 Xush kelibsiz, {html.bold(username)}!\n\n"
        f"🎬 {html.bold('AniNovuz')} — siz qidirgan eng sara, sifatli va sevimli animelar makoniga qadam qo'ydingiz.\n\n"
        f"📌 {html.italic('ID')}: {html.code(user_id)}\n"
        f"🔑 {html.italic('STATUS')}: {html.bold(user.get('status', 'user').upper())}\n\n"
        f"⚡️ Quyidagi  menyudan foydalanishingiz mumkin⬇️:"
    )
    
    # 🎨 Eng yangi uslubdagi original rangli tugmalar
    start_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            # 🔵 Ko'k tugma (Asosiy harakat)
            [
                InlineKeyboardButton(
                    text="🔍 Qidiruv bo'limi", 
                    callback_data="search_menu",
                    style="primary"
                )
            ],
            # Standart chiroyli ko'k tugmalar
            [
                InlineKeyboardButton(
                    text="Reklama berish 📢",
                    callback_data="advertise",
                    style="primary"
                ),
                InlineKeyboardButton(
                    text="Qo'llanma 📖",
                    callback_data="guide",
                    style="primary"
                )
            ],
            # 🟢 Yashil tugma (Premium taklif)
            [
                InlineKeyboardButton(
                    text="VIP olish 💎", 
                    callback_data="buy_vip",
                    style="success"
                )
            ],
            # 🔴 Qizil tugma (Yordam)
            [
                InlineKeyboardButton(
                    text="💬 Muammo bormi? Aloqa", 
                    callback_data="support",
                    style="danger"
                )
            ]
        ]
    )
    
    # 🚀 Rasmni mahalliy file_id orqali chaqmoqdek tezlikda yuborish
    await message.answer_photo(
        photo=start_image_file_id,
        caption=welcome_text,
        reply_markup=start_keyboard
    )