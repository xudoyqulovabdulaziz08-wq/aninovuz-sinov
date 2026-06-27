import math
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from services.user_service import UserService
from aiogram import html, F, Router

from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger("admin list")
router = Router()



async def get_admin_list_markup(session, page: int = 1, per_page: int = 10) -> tuple[InlineKeyboardMarkup, int]:
    service = UserService(session=session)
    
    # 1. DB dan barcha adminlarni yuklash
    try:
        all_admins = await service.list_admin_users()
        if not all_admins:
            all_admins = []
    except Exception as e:
        logger.error(f"❌ Admin ro'yxatini olishda xatolik: {e}")
        all_admins = []
        
    total_admins = len(all_admins)
    
    # 2. Agar tizimda umuman admin topilmasa (faqat Creator bo'lsa)
    if total_admins == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Admin Boshqaruviga", callback_data="admin_creator", style="danger")]
        ])
        return kb, 0

    # 3. Sahifalarni xavfsiz hisoblash
    total_pages = math.ceil(total_admins / per_page)
    page = max(1, min(page, total_pages))

    # 4. Joriy sahifaga tegishli qismini kesib olish
    start_idx = (page - 1) * per_page
    current_page_admins = all_admins[start_idx : start_idx + per_page]

    inline_keyboard = []

    # 5. Adminlar uchun tugmalarni shakllantirish
    for admin in current_page_admins:
        user_id = admin.get("user_id")
        username = admin.get("username")
        
        # Username bo'lsa @ bilan, bo'lmasa ID ning o'zi bilan chiroyli chiqishi uchun
        display_name = f"@{username}" if username else f"ID: {user_id}"
        
        inline_keyboard.append([
            InlineKeyboardButton(
                text=f"👨‍💼 {display_name}", 
                # view_admin:ADMIN_ID:CURRENT_PAGE (O'chirilgandan keyin shu sahifaga qaytish uchun)
                callback_data=f"view_admin:{user_id}:{page}"
            )
        ])

    # 6. Paginatsiya (Navigatsiya) satri - Sizning UX andozangiz bilan 100% bir xil
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"list_admin_page:{page-1}", style="primary"))
    else:
        nav_row.append(InlineKeyboardButton(text="⛔️", callback_data="void", style="danger"))

    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="void", style="primary"))

    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"list_admin_page:{page+1}", style="primary"))
    else:
        nav_row.append(InlineKeyboardButton(text="⛔️", callback_data="void", style="danger"))

    inline_keyboard.append(nav_row)

    # 7. Ortga qaytish satri (Siz aytgan admin boshqaruv bosh menyusi)
    inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Admin Boshqaruviga", callback_data="admin_creator", style="danger")
    ])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard), total_admins





@router.callback_query(F.data.startswith("list_admin_page:"))
async def process_admin_list_page(callback: CallbackQuery, session):
    await callback.answer()
    
    # 1. Callback datadan joriy sahifani ajratib olamiz
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 1
        
    # 2. Generator orqali klaviatura va jami sonini olamiz
    kb, total_admins = await get_admin_list_markup(session=session, page=page, per_page=10)
    
    # 3. Dinamik matn tayyorlaymiz
    if total_admins == 0:
        text = (
            f"📋 {html.bold('Adminlar ro‘yxati')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Botda hozircha biror bir tayinlangan admin mavjud emas! 👤"
        )
    else:
        text = (
            f"📋 {html.bold('Adminlar ro‘yxati')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Tizimda jami {html.bold(total_admins)} ta faol admin topildi.\n"
            f"Admin profili bilan tanishish va uni {html.bold('o‘chirish')} uchun kerakli foydalanuvchi tugmasini bosing:\n\n"
            f"👇 Sahifa: {page}"
        )
        
    # 4. Silliqqina edit text qilamiz
    try:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logger.error(f"❌ Admin ro'yxati paginatsiyasida xatolik: {e}")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xatolik: {e}")

# Bo'sh tugmalar (void) bosilganda yuklanish belgisini o'chirib qo'yish uchun
@router.callback_query(F.data == "void")
async def process_void_callback(callback: CallbackQuery):
    await callback.answer()




@router.callback_query(F.data.startswith("view_admin:"))
async def view_admin_profile(callback: CallbackQuery, user_service: UserService):
    await callback.answer()
    
    # Callback datadan admin_id va joriy sahifani ajratib olamiz
    # Format: view_admin:ADMIN_ID:PAGE
    params = callback.data.split(":")
    target_admin_id = int(params[1])
    current_page = params[2]
    
    # Admin ma'lumotlarini kesh/DB dan olamiz
    admin_data = await user_service.get_user(target_admin_id)
    
    if not admin_data:
        await callback.message.edit_text(
            text="❌ Ushbu admin ma'lumotlari topilmadi yoki u allaqachon o'chirilgan.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data=f"list_admin_page:{current_page}", style="danger")]
            ])
        )
        return

    username = admin_data.get("username")
    display_username = f"@{username}" if username else "Mavjud emas"
    joined_at = admin_data.get("joined_at", "Noma'lum").split("T")[0] # Sanani chiroyli kesamiz
    points = admin_data.get("points", 0)

    text = (
        f"👤 {html.bold('Admin Profili')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Telegram ID: {html.code(target_admin_id)}\n"
        f"👤 Username: {display_username}\n"
        f"💰 To'plagan ballari: <code>{points}</code>\n"
        f"📅 Botga qo'shilgan vaqti: <b>{joined_at}</b>\n"
        f"🛡️ Status: <code>👨‍💼 Admin</code>\n\n"
        f"👇 Ushbu admin ustida amal bajarish:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            # O'chirish bosqichiga o'tish (ID va Sahifani birga uzatamiz)
            InlineKeyboardButton(text="❌ Adminlikdan bo‘shatish", callback_data=f"dismiss_admin:{target_admin_id}:{current_page}", style="danger")
        ],
        [
            # Aynan qaysi paginatsiya sahifasidan kelgan bo'lsa, o'sha sahifaga silliq qaytaradi
            InlineKeyboardButton(text="⬅️ Ro‘yxatga qaytish", callback_data=f"list_admin_page:{current_page}", style="danger")
        ]
    ])

    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")







# =========================================================
# A) ❌ O'CHIRISH TUGMASI BOSILGANDA (TASDIQLASH SÕROVI)
# =========================================================
@router.callback_query(F.data.startswith("dismiss_admin:"))
async def confirm_dismiss_admin_request(callback: CallbackQuery):
    await callback.answer()
    
    # Format: dismiss_admin:ADMIN_ID:PAGE
    _, target_id, page = callback.data.split(":")
    
    text = (
        f"❓ {html.bold('Adminni o‘chirishni tasdiqlash')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Rostdan ham ushbu adminni huquqlarini bekor qilib, oddiy foydalanuvchi darajasiga tushirmoqchimisiz?\n\n"
        f"🆔 Admin ID: {html.code(target_id)}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o‘chirilsin", callback_data=f"confirm_dismiss:yes:{target_id}:{page}", style="success"),
            InlineKeyboardButton(text="❌ Yo‘q, bekor qilish", callback_data=f"confirm_dismiss:no:{target_id}:{page}", style="danger")
        ]
    ])
    
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


# =========================================================
# B) ⚡ YAKUNIY AMAL (HA / YO'Q BOSILGANDA)
# =========================================================
@router.callback_query(F.data.startswith("confirm_dismiss:"))
async def finalize_dismiss_admin(callback: CallbackQuery, user_service: UserService):
    await callback.answer()
    
    # Format: confirm_dismiss:DECISION:ADMIN_ID:PAGE
    _, decision, target_id, page = callback.data.split(":")
    target_id = int(target_id)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin ro‘yxatiga qaytish", callback_data=f"list_admin_page:{page}", style="danger")]
    ])
    
    if decision == "yes":
        # Servis orqali DB va Keshdan adminlikni o'chiramiz
        success = await user_service.revoke_admin(target_id)
        
        if success:
            text = (
                f"📉 {html.bold('Admin muvaffaqiyatli o‘chirildi!')}\n\n"
                f"Foydalanuvchining adminlik huquqlari to‘liq bekor qilindi va u {html.bold('oddiy foydalanuvchi')} statusiga o‘tkazildi.\n\n"
                f"🆔 ID: {html.code(target_id)}\n"
                f"🧹 Tizim keshlaridan L1/L2 tozalandi."
            )
            
            # 🔔 SIZ AYTGAN UX SIGNAL: Sobiq adminga Creator nomidan xabarnoma yuborish
            try:
                await callback.bot.send_message(
                    chat_id=target_id,
                    text=f"🚨 <b>Xabarnoma!</b>\n\nAsoschi (Creator) tomonidan sizning ushbu botdagi <b>adminlik huquqlaringiz bekor qilindi</b> va statusiz oddiy foydalanuvchi darajasiga tushirildi."
                )
            except Exception:
                # Agar foydalanuvchi botni bloklagan bo'lsa xato bermasligi uchun pass qilamiz
                pass
        else:
            text = f"❌ {html.bold('Xatolik!')}\n\nAdmin statusini o‘zgartirishda xatolik yuz berdi."
            
    else:
        # Agar YO'Q bosilsa, hech narsa o'zgarmaydi, shunchaki profiliga qaytib ketadi
        text = f"❌ {html.bold('Adminni o‘chirish bekor qilindi.')}\n\nHech qanday o‘zgarish amalga oshirilmadi."
        # Profiliga silliq qaytishi uchun tugmani o'zgartiramiz
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Admin profiliga qaytish", callback_data=f"view_admin:{target_id}:{page}", style="danger")]
        ])

    await callback.message.edit_text(text=text, reply_markup=back_kb, parse_mode="HTML")