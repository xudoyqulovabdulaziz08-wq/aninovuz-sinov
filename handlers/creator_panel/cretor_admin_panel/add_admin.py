import logging
from aiogram import Router, F, html
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest


from database.models import UserStatus
from services.user_service import UserService


logger = logging.getLogger("AddAdminHandler")



from aiogram.fsm.state import StatesGroup, State
router = Router()
class AddAdminSG(StatesGroup):
    waiting_for_id = State()      # Admin ID sini kutish holati
    waiting_for_confirm = State() # Tasdiqlash holati (Xa/Yo'q)




@router.callback_query(F.data == "add_admin")
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    text = (
        f"➕ {html.bold('Yangi admin qo‘shish')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Iltimos, admin qilmoqchi bo‘lgan foydalanuvchining {html.code('Telegram ID')} raqamini yuboring:\n\n"
        f"⚠️ {html.italic('Eslatma: VIP statusga ega foydalanuvchilarni admin qilib bo‘lmaydi.')}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_creator", style="danger")]
    ])
    
    # 📌 UX ENGINIYERING: Kelgusida qayta tahrirlash uchun asosiy xabar ID sini saqlab qo'yamiz
    await state.update_data(main_msg_id=callback.message.message_id)
    
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddAdminSG.waiting_for_id)





# =========================================================
# 2. ID QABUL QILISH VA TEKSHIRUV (VAQTINCHALIK KESH BILAN)
# =========================================================
@router.message(AddAdminSG.waiting_for_id)
async def process_admin_id(message: Message, state: FSMContext, user_service: UserService):
    raw_id = message.text.strip()
    
    # Foydalanuvchi yuborgan ID xabarini darhol o'chirib chatni toza tutamiz
    try:
        await message.delete()
    except Exception:
        pass
        
    # Keshdan asosiy xabar ID sini olamiz
    state_data = await state.get_data()
    main_msg_id = state_data.get("main_msg_id")

    # 1-Tekshiruv: ID raqam ekanligini tekshirish
    if not raw_id.isdigit():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_creator", style="danger")]
        ])
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=main_msg_id,
                text=f"❌ {html.bold('Xatolik!')}\n\nTelegram ID faqat raqamlardan iborat bo‘lishi kerak. Iltimos, qaytadan to‘g‘ri ID kiriting:",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    target_user_id = int(raw_id)

    # 2-Tekshiruv: Bot bazasida bor-yo'qligini tekshirish (Cache-first)
    target_user = await user_service.get_user(target_user_id)
    
    # Agar foydalanuvchi topilmasa yoki bazada emergency profil bo'lsa (ya'ni haqiqiy foydalanuvchi emas)
    if not target_user or target_user.get("is_emergency", False):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="add_admin", style="primary"),
             InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_creator", style="danger")]
        ])
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=main_msg_id,
                text=f"🔍 {html.bold('Foydalanuvchi topilmadi!')}\n\nUshbu ID ({html.code(target_user_id)}) ga ega foydalanuvchi botimizdan ro‘yxatdan o‘tmagan.",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    # Dinamik ravishda joriy statusni tekshirib olamiz (Muddati o'tgan VIP larni tozalash uchun)
    target_user = user_service._ensure_fresh_vip_status(target_user)

    # 3-Tekshiruv: Allaqachon ADMIN bo'lsa
    if target_user.get("status") == UserStatus.ADMIN.value:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_creator", style="danger")]
        ])
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=main_msg_id,
                text=f"ℹ️ Foydalanuvchi ({html.code(target_user_id)}) allaqachon botda {html.bold('ADMIN')} statusida.",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    # 4-Tekshiruv: Siz aytgan eng muhim qoida - VIP statusini tekshirish
    if target_user.get("is_vip", False) or target_user.get("status") == UserStatus.VIP.value:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_creator", style="danger")]
        ])
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=main_msg_id,
                text=f"🚫 {html.bold('Chalkashlikni oldini olish taqiqi!')}\n\n"
                     f"Ushbu foydalanuvchi hozirda {html.bold('💎 VIP obunachi')} hisoblanadi.\n"
                     f"Qoidaga ko‘ra, VIP foydalanuvchilarni admin qilib bo‘lmaydi! Avval uning VIP muddatini tugatish yoki olib tashlash kerak.",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    # 💾 KESHGA SAQLASH: Hamma tekshiruvdan o'tsa, maqsadli ID ni vaqtinchalik saqlaymiz
    await state.update_data(target_admin_id=target_user_id, target_username=target_user.get("username", "Mavjud emas"))
    
    # Tasdiqlash so'rovi (XA / YO'Q)
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, tasdiqlayman", callback_data="confirm_add_admin:yes", style="success"),
            InlineKeyboardButton(text="❌ Yo‘q, bekor qilish", callback_data="confirm_add_admin:no", style="danger")
        ]
    ])
    
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            text=f"❓ {html.bold('Adminlikni tasdiqlash')}\n\n"
                 f"Rostdan ham quyidagi foydalanuvchini admin qilmoqchimisiz?\n\n"
                 f"🆔 ID: {html.code(target_user_id)}\n"
                 f"👤 Username: @{target_user.get('username', 'Mavjud emas')}\n\n"
                 f"✨ {html.italic('Unga barcha admin huquqlari va VIP imtiyozlar avtomatik beriladi.')}",
            reply_markup=confirm_kb,
            parse_mode="HTML"
        )
        await state.set_state(AddAdminSG.waiting_for_confirm)
    except Exception as e:
        logger.error(f"Error in showing confirmation: {e}")




    
# =========================================================
# 3. TASDIQLASH (XA / YO'Q) CALLBACK HANDLERI
# =========================================================
@router.callback_query(AddAdminSG.waiting_for_confirm, F.data.startswith("confirm_add_admin:"))
async def finalize_add_admin(callback: CallbackQuery, state: FSMContext, user_service: UserService):
    await callback.answer()
    
    decision = callback.data.split(":")[1]
    state_data = await state.get_data()
    target_id = state_data.get("target_admin_id")
    target_username = state_data.get("target_username")
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin boshqaruviga qaytish", callback_data="admin_creator", style="danger")]
    ])
    
    if decision == "yes" and target_id:
        # Boya UserService ichiga qo'shgan toza kesh invalidatsiyali metodimizni chaqiramiz
        success = await user_service.make_admin(target_id)
        
        if success:
            text = (
                f"🎉 {html.bold('Muvaffaqiyatli bajarildi!')}\n\n"
                f"Foydalanuvchi tizimga muvaffaqiyatli {html.bold('ADMIN')} qilib qo‘shildi.\n\n"
                f"🆔 ID: {html.code(target_id)}\n"
                f"👤 Username: @{target_username}\n\n"
                f"🔒 L1/L2 keshlar yangilandi. Foydalanuvchi botga yozgan birinchi soniyasidanoq admin panel unga ochiq bo‘ladi."
            )
            
            # Yangi adminning o'ziga ham bot orqali xushxabar jo'natib qo'yamiz (UX bo'yicha chiroyli signal)
            try:
                await callback.bot.send_message(
                    chat_id=target_id,
                    text=f"👑 <b>Tabriklaymiz!</b> Asoschi (Creator) sizni ushbu botga <b>ADMIN</b> qilib tayinladi.\n"
                         f"Botni boshqarish uchun /admin buyrug'ini yozishingiz mumkin."
                )
            except Exception:
                pass
        else:
            text = f"❌ {html.bold('Xatolik!')}\n\nBazaga yozishda xatolik yuz berdi. Iltimos qaytadan urinib ko‘ring."
            
    else:
        # Agar YO'Q bosilgan bo'lsa
        text = f"❌ {html.bold('Admin qo‘shish bekor qilindi.')}\n\nHech qanday o‘zgarish amalga oshirilmadi."

    # FSM ni tozalaymiz
    await state.clear()
    
    # Asosiy oynani yakuniy xabar bilan edit qilamiz
    await callback.message.edit_text(text=text, reply_markup=back_kb, parse_mode="HTML")