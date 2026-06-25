import logging
from aiogram import Router, F
from datetime import datetime, timedelta, timezone
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import UserService 
from typing import Any
from database.models import UserStatus, DBUser
from services.user_service import UserService
from database.cache import cache_manager

logger = logging.getLogger("AdminVIP")
router = Router()

class AdminVIPStates(StatesGroup):
    wait_for_user_id = State()  # User ID sini kutish holati






@router.callback_query(F.data == "add_vip")
async def process_add_vip_click(callback: CallbackQuery, state: FSMContext):
    # Holatni o'rnatamiz (Bot endi aynan shu foydalanuvchidan ID kutadi)
    await state.set_state(AdminVIPStates.wait_for_user_id)
    
    # Orqaga qaytish tugmasi
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_vip_panel", style="danger")]
    ])
    
    # Matnni o'zgartiramiz
    await callback.message.edit_text(
        text="🆔 <b>Iltimos, VIP status bermoqchi bo'lgan foydalanuvchining Telegram ID raqamini yuboring:</b>\n\n"
             "<i>Masalan: 123456789</i>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )
    await callback.answer()




@router.callback_query(AdminVIPStates.wait_for_user_id) # Callback bosib yuborsa ham tekshirish uchun
@router.message(AdminVIPStates.wait_for_user_id, ~F.text.isdigit())
async def process_invalid_user_id(message: Message):
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_vip_panel", style="danger")]
    ])
    
    await message.answer(
        text="⚠️ <b>Xato format!</b> Foydalanuvchi ID raqami faqat sonlardan iborat bo'lishi kerak.\n"
             "Iltimos, qaytadan faqat raqamlarni yuboring:",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )







  # UserService importi

# 5. To'g'ri ID (faqat raqamlar) kelganda ishlaydigan xavfsiz handler
@router.message(AdminVIPStates.wait_for_user_id, F.text.isdigit())
async def process_valid_user_id(message: Message, state: FSMContext, session: Any):
    user_id = int(message.text)
    
    # 🔍 1. Bazadan foydalanuvchini xavfsiz qidiramiz
    try:
        user_service = UserService(session=session)
        # Kesh-aware va xavfsiz usulda user ma'lumotlarini olamiz
        user_data = await user_service.get_user(user_id=user_id)
    except Exception as e:
        logger.error(f"VIP tekshiruvida user qidirishda xato: {e}")
        await message.answer("❌ Bazadan foydalanuvchini qidirishda texnik xatolik yuz berdi.")
        return

    # 🛑 2. Agar user bazada umuman mavjud bo'lmasa
    if not user_data:
        cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_vip_panel", style="danger")]
        ])
        await message.answer(
            text=f"❌ <b>ID: {user_id}</b> raqamli foydalanuvchi tizimda (bot bazasida) mavjud emas!\n"
                 f"Iltimos, ID raqamni to'g'ri kiritganingizni qayta tekshiring:",
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )
        return

    # ✅ 3. Foydalanuvchi topilsa, ID va Ismini saqlab qo'yamiz
    await state.update_data(target_user_id=user_id)
    
    username = user_data.get("username") or "Foydalanuvchi"
    current_status = user_data.get("status", "user")

    # 📅 4. Muddat tanlash tugmalarini hosil qilamiz (Callback_data ga oylarni yozamiz)
    duration_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 1 Oylik", callback_data="set_vip_duration:1", style="primary"),
            InlineKeyboardButton(text="📅 2 Oylik", callback_data="set_vip_duration:2", style="primary")
        ],
        [
            InlineKeyboardButton(text="📅 3 Oylik", callback_data="set_vip_duration:3", style="primary"),
            InlineKeyboardButton(text="📅 6 Oylik", callback_data="set_vip_duration:6", style="primary")
        ],
        [
            InlineKeyboardButton(text="📆 1 Yillik", callback_data="set_vip_duration:12", style="primary")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_vip_panel", style="danger")
        ]
    ])

    await message.answer(
        text=f"🔍 <b>Foydalanuvchi topildi!</b>\n\n"
             f"👤 <b>Nomi:</b> {username}\n"
             f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
             f"📊 <b>Joriy statusi:</b> <code>{current_status.upper()}</code>\n\n"
             f"✨ <i>Iltimos, ushbu foydalanuvchi uchun VIP muddatini tanlang:</i>",
        reply_markup=duration_kb,
        parse_mode="HTML"
    )









@router.callback_query(F.data.startswith("set_vip_duration:"))
async def process_set_duration(callback: CallbackQuery, state: FSMContext):
    # Callback datadan oylar sonini ajratib olamiz
    months = int(callback.data.split(":")[1])
    
    # FSM xotirasidan maqsadli user_id ni olamiz
    state_data = await state.get_data()
    target_user_id = state_data.get("target_user_id")
    
    if not target_user_id:
        await callback.answer("🚨 Xatolik: Foydalanuvchi ID topilmadi!", show_alert=True)
        await state.clear()
        return

    # Oylar sonini eslab qolamiz
    await state.update_data(selected_months=months)
    
    # Tasdiqlash tugmalari
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_vip_grant:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_vip_grant:no")
        ]
    ])

    # Muddat matnini chiroyli formatda chiqarish
    duration_text = f"{months} oylik" if months < 12 else "1 yillik"

    await callback.message.edit_text(
        text=f"❓ <b>Tasdiqlash:</b>\n\n"
             f"Rostdan ham <code>{target_user_id}</code> ID raqamli foydalanuvchini "
             f"<b>{duration_text}</b> muddatga <b>VIP</b> qilmoqchimisiz?",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )
    await callback.answer()


# 2. 👑 "Ha" yoki "Yo'q" tasdiqlash tugmalari bosilganda
@router.callback_query(F.data.startswith("confirm_vip_grant:"))
async def process_vip_confirmation(callback: CallbackQuery, state: FSMContext, session: Any):
    decision = callback.data.split(":")[1]
    
    # FSM xotirasidan ma'lumotlarni o'qiymiz
    state_data = await state.get_data()
    target_user_id = state_data.get("target_user_id")
    months = state_data.get("selected_months")
    
    # Holatni darhol tozalaymiz
    await state.clear()

    # VIP panelga qaytish tugmasi (Har ikkala holatda ham kerak bo'ladi)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 VIP Panelga qaytish", callback_data="cancel_add_vip")]
    ])

    # ❌ Agar "Yo'q" bosilgan bo'lsa amallarni bekor qilamiz
    if decision == "no":
        await callback.message.edit_text(
            text="❌ <b>VIP status berish jarayoni admin tomonidan bekor qilindi.</b>",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # ✅ Agar "Ha" bosilgan bo'lsa - Baza va Kesh bilan ishlash boshlanadi
    await callback.answer("⏳ VIP status faollashtirilmoqda...", show_alert=False)

    try:
        # Muddat hisoblash (Hozirgi vaqtga oylarni qo'shamiz)
        # Oylarni timedelta orqali taxminan 1 oy = 30 kun deb hisoblaymiz
        days_to_add = months * 30
        expire_date = datetime.now(timezone.utc) + timedelta(days=days_to_add)

        # 🔄 TRANZAKSIYAVIY XAVFSIZ YANGILASH
        from sqlalchemy import update
        
        # 1. Ma'lumotlar bazasida user statusi va muddatini yangilaymiz
        stmt = (
            update(DBUser)
            .where(DBUser.user_id == target_user_id)
            .values(
                status=UserStatus.VIP,
                vip_expire_date=expire_date
            )
        )
        await session.execute(stmt)
        await session.commit()  # Ma'lumotlarni saqlaymiz

        # 2. 🧹 VALKEY KESHINI MAJBURIY TOZALASH (Invalidate)
        # Shunda middleware keyingi safar foydalanuvchini keshdan emas, yangilangan bazadan o'qiydi!
        await cache_manager.invalidate("users", str(target_user_id), broadcast=True)
        # Agar obuna statusi keshida ham user_id bo'lsa, uni ham tozalash (ixtiyoriy)
        await cache_manager.invalidate("sub_status", str(target_user_id), broadcast=True)

        # Chiroyli sana formati
        formatted_date = expire_date.strftime("%d.%m.%Y %H:%M")
        duration_text = f"{months} oylik" if months < 12 else "1 yillik"

        await callback.message.edit_text(
            text=f"🚀 <b>Muvaffaqiyatli bajarildi!</b>\n\n"
                 f"👤 Foydalanuvchi: <code>{target_user_id}</code>\n"
                 f"💎 Status: <b>VIP ({duration_text})</b>\n"
                 f"📅 Tugash muddati: <code>{formatted_date}</code> gacha belgilandi.\n\n"
                 f"<i>Kesh yangilandi va foydalanuvchi uchun VIP imkoniyatlar ochildi.</i>",
            reply_markup=back_kb,
            parse_mode="HTML"
        )

        # ✨ Ixtiyoriy: Agar xohlasangiz, foydalanuvchining o'ziga ham VIP bo'lgani haqida bildirishnoma yuborish:
        try:
            await callback.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 <b>Tabriklaymiz! Admin tomonidan sizga {duration_text} VIP status taqdim etildi!</b>\n"
                     f"📅 VIP muddati: <code>{formatted_date}</code> gacha faol.",
                parse_mode="HTML"
            )
        except Exception:
            # Agar foydalanuvchi botni bloklagan bo'lsa xato bermasligi uchun
            pass

    except Exception as db_err:
        await session.rollback()  # Xatolik bo'lsa bazani orqaga qaytaradi
        logger.error(f"❌ VIP status berishda bazada xato yuz berdi: {db_err}")
        await callback.message.edit_text(
            text="❌ <b>Texnik xatolik:</b> Foydalanuvchiga VIP status berish amalga oshmadi.",
            reply_markup=back_kb,
            parse_mode="HTML"
        )