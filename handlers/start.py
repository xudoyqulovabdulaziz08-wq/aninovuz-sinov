from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message
from services.user_service import UserService

router = Router(name="start_router")

@router.message(CommandStart())
async def cmd_start(message: Message, user: dict, user_service: UserService):
    """
    /start buyrug'i uchun handler.
    E'tibor bering, 'user' va 'user_service' middleware'dan tayyor holatda keladi!
    """
    user_id = message.from_user.id
    username = message.from_user.username or "foydalanuvchi"
    
    # 1. Foydalanuvchi ma'lumotlari allaqachon keshda yoki DBda mavjud (middleware buni hal qilgan)
    # 2. Agar foydalanuvchiga qo'shimcha ball berish yoki statusini yangilash kerak bo'lsa:
    # await user_service.add_points(user_id, points=10) # Masalan, start uchun bonus
    
    welcome_text = (
        f"👋 Assalomu alaykum, {html.bold(username)}!\n\n"
        f"🎬 {html.italic('Anime Qidiruv Botiga')} xush kelibsiz.\n"
        f"Sizning ID: {html.code(user_id)}\n"
        f"Statusingiz: {html.bold(user.get('status', 'user'))}\n\n"
        f"🤖 Bot orqali sevimli animelaringizni nomi, ID-si yoki "
        f"foto/skrinshot orqali (AI yordamida) qidirishingiz mumkin!"
    )
    
    await message.answer(text=welcome_text, parse_mode="HTML")