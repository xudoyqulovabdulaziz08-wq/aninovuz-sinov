from aiogram import Router, html, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from typing import Any
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import StatesGroup, State
from services.channel_service import ChannelService


# FSM holatini 1 taga tushiramiz
class AutoAddChannelState(StatesGroup):
    wait_for_channel = State()  # Faqat havola yoki username kutadi



router = Router()

@router.callback_query(F.data == "add_channel")
async def start_auto_add_channel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AutoAddChannelState.wait_for_channel)
    
    text = (
        f"➕ {html.bold('Avtomatik kanal qo‘shish')}\n\n"
        f"Iltimos, kanalning {html.underline('usernamesini')} yoki {html.underline('havolasini')} yozib yuboring.\n"
        f"Bot qolgan barcha ma'lumotlarni (ID, Nomi) avtomatik aniqlaydi! ⚡️\n\n"
        f"Misol: {html.code('@Aninovuz')} yoki {html.code('https://t.me/Aninovuz')}\n\n"
        f"⚠️ {html.italic('Muhim:')} Bot ushbu kanalda oldindan admin qilingan bo‘lishi shart!"
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_channel_menu", style="danger")]
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


@router.message(AutoAddChannelState.wait_for_channel)
async def process_auto_channel(message: Message, state: FSMContext, session: Any, bot: Bot):
    input_data = message.text.strip()
    
    # Havoladan username yoki ID ni ajratib olish
    chat_identifier = input_data
    if "t.me/" in input_data:
        chat_identifier = input_data.split("t.me/")[-1].replace("@", "")
        # Agar maxsus taklif linki bo'lsa va username bo'lmasa, admin qo'lda ID kiritishi kerak bo'ladi
        if chat_identifier.startswith("+") or chat_identifier.startswith("joinchat/"):
            await message.reply(
                "❌ Maxsus yopiq kanallarning linkidan ma'lumotlarni avtomatik olib bo‘lmaydi.\n"
                "Iltimos, kanal ochiq bo'lsa uning @username shaklini yuboring."
            )
            return
        chat_identifier = f"@{chat_identifier}"

    try:
        # Telegramdan kanal ma'lumotlarini so'raymiz
        chat = await bot.get_chat(chat_identifier)
        
        channel_id = chat.id
        title = chat.title
        # Agar username bo'lsa o'shani, bo'lmasa admin yuborgan linkni saqlaymiz
        url = f"https://t.me/{chat.username}" if chat.username else input_data

        # Ma'lumotlarni bazaga saqlash
        service = ChannelService(session=session)
        await service.create_channel(
            channel_id=channel_id,
            title=title,
            url=url
        )
        
        text = (
            f"🚀 {html.bold('Kanal avtomatik qo‘shildi!')}\n\n"
            f"Bot kanal ma'lumotlarini muvaffaqiyatli aniqladi:\n"
            f"📌 {html.bold('ID:')} {html.code(channel_id)}\n"
            f"📌 {html.bold('Nomi:')} {title}\n"
            f"📌 {html.bold('Havola:')} {url}\n\n"
            f"Keshlar va ro‘yxat avtomatik yangilandi!"
        )
        await state.clear()

    except TelegramBadRequest as e:
        # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa shu xato chiqadi
        text = (
            f"❌ {html.bold('Xatolik yuz berdi!')}\n\n"
            f"Bot kanalni topa olmadi yoki kanalda admin emas.\n"
            f"Iltimos, botni kanalga qo‘shib, admin huquqlarini bering va qaytadan urinib ko‘ring."
        )
    except ValueError:
        text = f"❌ {html.bold('Xatolik:')} Ushbu kanal allaqachon bazada mavjud!"
        await state.clear()
    except Exception as e:
        text = f"❌ Kutilmagan xatolik: {str(e)}"
        await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Kanallar menyusiga qaytish", callback_data="admin_channel_menu")]
        ]
    )
    await message.answer(text=text, reply_markup=kb, parse_mode="HTML")