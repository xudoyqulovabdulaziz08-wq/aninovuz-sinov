
import asyncio
import logging
from typing import Any
from aiogram import Router, html, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from repositories.user_repository import UserRepository
from database.models import DBUser, UserStatus
router = Router()
logger = logging.getLogger("AdminVIP")
class AdminAdvertSG(StatesGroup):
    waiting_for_ad = State()


# 1. Reklama yuborish tugmasi bosilganda toifalarni ko'rsatish
@router.callback_query(F.data == "admin_advert")
async def process_admin_advert_menu(callback: CallbackQuery):
    await callback.answer()
    
    # Guruhlarga mos maxsus callback_data format: "send_adv:{guruh_nomi}"
    advert_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Hammaga (User, VIP, Admin)", callback_data="send_adv:all", style="primary")
        ],
        [
            InlineKeyboardButton(text="💎 Faqat VIP foydalanuvchilarga", callback_data="send_adv:vip", style="primary")
        ],
        [
            InlineKeyboardButton(text="👤 Faqat oddiy foydalanuvchilarga", callback_data="send_adv:user", style="primary")
        ],
        [
            InlineKeyboardButton(text="🛠 Faqat Adminlarga", callback_data="send_adv:admin", style="primary")
        ],
        [
            # Admin bosh menyusiga yoki mos keladigan asosiy panelga qaytish
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_panel", style="danger")
        ]
    ])
    
    await callback.message.edit_text(
        text="📢 <b>Reklama va Bildirishnomalar yuborish bo'limi</b>\n\n"
             "<i>Ushbu bo'lim orqali bot foydalanuvchilariga reklama, aksiya yoki texnik "
             "xabarlarni yuborishingiz mumkin.</i>\n\n"
             "✨ Xabar yubormoqchi bo'lgan maqsadli (target) guruhni tanlang:",
        reply_markup=advert_kb,
        parse_mode="HTML"
    )






@router.callback_query(F.data.startswith("send_adv:"))
async def process_select_advert_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    target_group = callback.data.split(":")[1] # all, vip, user, admin
    
    # Guruh nomini chiroyli matnga o'tkazamiz
    group_titles = {
        "all": "🌍 Hammaga (User, VIP, Admin)",
        "vip": "💎 Faqat VIP foydalanuvchilarga",
        "user": "👤 Faqat oddiy foydalanuvchilarga",
        "admin": "🛠 Faqat Adminlarga"
    }
    title = group_titles.get(target_group, target_group)
    
    # Ma'lumotlarni holatda saqlaymiz
    await state.update_data(target_group=target_group, group_title=title)
    await state.set_state(AdminAdvertSG.waiting_for_ad)
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_advert", style="danger")]
    ])
    
    await callback.message.edit_text(
        text=f"🎯 Target guruh: <b>{title}</b>\n\n"
             f"📥 <b>Iltimos, yubormoqchi bo'lgan reklama xabaringizni yuboring.</b>\n"
             f"<i>(Matn, rasm, video, albom, hujjat yoki inline tugmali xabar bo'lishi mumkin. Bot uni qanday bo'lsa shunday nusxalaydi)</i>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )





@router.message(AdminAdvertSG.waiting_for_ad)
async def process_receive_advert_message(message: Message, state: FSMContext):
    # Admin yuborgan xabarning ID sini va Chat ID sini saqlaymiz
    await state.update_data(ad_message_id=message.message_id, ad_chat_id=message.chat.id)
    
    data = await state.get_data()
    title = data.get("group_title")
    
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, tarqatilsin", callback_data="adv_confirm:yes", style="primary"),
            InlineKeyboardButton(text="❌ Yo'q, bekor qilinsin", callback_data="adv_confirm:no", style="danger")
        ]
    ])
    
    # Admin yuborgan xabarga javob (reply) tariqasida tasdiqlash so'raymiz
    await message.reply(
        text=f"❓ <b>Reklamani tasdiqlash:</b>\n\n"
             f"Ushbu xabarni <b>{title}</b> guruhidagi barcha foydalanuvchilarga tarqatishni tasdiqlaysizmi?",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )




async def send_advert_background_task(bot, target_group, from_chat_id, message_id, session_factory):
    """Orqa fonda xabar tarqatish taski (Bot yuklamasini kamaytiradi va crashdan himoya qiladi)"""
    logger.info(f"🚀 Background advert broadcast started for group: {target_group}")
    
    # Yangi session ochamiz, chunki bu alohida fondagi task
    async with session_factory() as session:
        stmt = select(DBUser.user_id)
        
        # Guruh bo'yicha filterlash
        if target_group == "vip":
            stmt = stmt.where(DBUser.status == UserStatus.VIP)
        elif target_group == "user":
            stmt = stmt.where(DBUser.status == UserStatus.USER)
        elif target_group == "admin":
            stmt = stmt.where(DBUser.status == UserStatus.ADMIN)
        # 'all' bo'lsa hech qanday filtersiz hamma olinadi
        
        result = await session.execute(stmt)
        user_ids = result.scalars().all()

    success_count = 0
    fail_count = 0
    
    for uid in user_ids:
        try:
            # copy_to metodi xabarni rasm, video, text, inline_keyboard bilan birga nusxalaydi
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success_count += 1
            # Telegram FloodWait xatoligini oldini olish uchun kichik kechikish
            await asyncio.sleep(0.05) 
        except Exception as e:
            fail_count += 1
            # Agar foydalanuvchi botni bloklagan bo'lsa, logga yozadi lekin tarqatish to'xtamaydi
            logger.debug(f"Could not send ad to {uid}: {e}")

    logger.info(f"🏁 Advert broadcast finished. Success: {success_count}, Failed: {fail_count}")
    
    # Xohishga ko'ra adminga reklama tugagani haqida hisobot yuborish mumkin
    try:
        await bot.send_message(
            chat_id=from_chat_id,
            text=f"📊 <b>Reklama tarqatish yakunlandi!</b>\n\n"
                 f"✅ Muvaffaqiyatli yetkazildi: <code>{success_count} ta</code>\n"
                 f"❌ Yetkazilmadi (Bloklaganlar): <code>{fail_count} ta</code>",
            parse_mode="HTML"
        )
    except Exception:
        pass







@router.callback_query(F.data.startswith("adv_confirm:"))
async def process_final_advert_decision(callback: CallbackQuery, state: FSMContext, session: Any):
    decision = callback.data.split(":")[1]
    
    if decision == "no":
        await callback.answer("Reklama yuborish bekor qilindi.")
        await state.clear()
        await callback.message.edit_text(
            text="❌ <b>Reklama yuborish bekor qilindi.</b>\nAsosiy admin panelga qaytishingiz mumkin.",
            parse_mode="HTML"
        )
        return

    # "yes" bo'lganda FSM ma'lumotlarini olamiz
    data = await state.get_data()
    target_group = data.get("target_group")
    ad_message_id = data.get("ad_message_id")
    ad_chat_id = data.get("ad_chat_id")
    
    await callback.answer("🚀 Tarqatish boshlandi!", show_alert=False)
    await state.clear() # FSM holatni darhol tozalaymiz
    
    # 📌 ORQA FONDA ISHLASH SIRI: asyncio.create_task
    # Buning uchun sizda session_factory (async_sessionmaker) bor deb hisoblaymiz, 
    # agar session proxy modelda bo'lsa, session.__class__ yoki asosiy sessionmaker uzatiladi.
    session_real = UserRepository._get_real_session(session)
    session_factory = session_real.bind if hasattr(session_real, "bind") else None
    
    # Agar middleware'ingizda sessionmaker bo'lsa, o'shani ishlating, aks holda joriy session bindidan sessionmaker yasaymiz
    if session_factory and not isinstance(session_factory, async_sessionmaker):
        session_factory = async_sessionmaker(bind=session_real.bind, expire_on_commit=False)

    asyncio.create_task(
        send_advert_background_task(
            bot=callback.bot,
            target_group=target_group,
            from_chat_id=ad_chat_id,
            message_id=ad_message_id,
            session_factory=session_factory
        )
    )
    
    # Adminga darhol javob qaytaramiz (Bot qotib qolmaydi!)
    await callback.message.edit_text(
        text="🚀 <b>Reklama orqa fonda tarqatila boshladi!</b>\n\n"
             "Bot foydalanuvchilarga odatiy rejimda xizmat ko'rsatishda davom etadi. "
             "Tarqatish yakunlangach, sizga yakuniy hisobot xabari yuboriladi.",
        parse_mode="HTML"
    )

# 6. Har qanday vaqtda bekor qilish handler'i
@router.callback_query(F.data == "cancel_advert")
async def process_cancel_advert_global(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Jarayon bekor qilindi.")
    await state.clear()
    await callback.message.edit_text(
        text="❌ Reklama yuborish jarayoni bekor qilindi.",
        parse_mode="HTML"
    )