import logging
import io
from typing import Any
from datetime import datetime
from aiogram.fsm.context import FSMContext
from asyncio.log import logger
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram import Router, html, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, Message, BufferedInputFile
from services.user_service import UserService
from config import config
from services.orchestrator import get_ai_stats
from repositories.user_repository import UserRepository
router = Router()


class AdminDBStates(StatesGroup):
    waiting_for_backup_file = State()



@router.callback_query(F.data == "creator_db_panel")
async def creator_db_menu(callback: CallbackQuery, user_service: UserService):
    # Tugma bosilganda yuqoridagi yuklanish soat belgisini darhol o'chiramiz
    await callback.answer()
    
    # 📊 1. Real vaqtda bazaning hajmini yuklab olamiz
    db_size = await user_service.get_database_storage_info()
    ai_stats = get_ai_stats()
    
    # 🗄️ UX ENGINIYERING: Maksimal darajada professional monitoring paneli dizayni
    text = (
        f"🗄️ {html.bold('Baza Nazorati va Tizim Control')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 {html.bold('Tizim statistikasi:')}\n"
        f"📝 Baza holati: <code>🟢 Faol / Stabil</code>\n"
        f"💾 Egallangan joy: {html.code(db_size)} 📦\n\n"
        f"🧠 {html.bold('AI Cache Brain holati:')}\n"
        f"├ 🔥 Kuzatuvdagi faol a'zolar: <code>{ai_stats['tracked_hot_users_count']} ta</code>\n"
        f"├ ⚡️ L1/L2 umumiy yozishlar: <code>{ai_stats['l1_total_writes']}/{ai_stats['l2_total_writes']}</code>\n"
        f"├ ⏱️ O'rtacha kechikish (Latency): <code>{ai_stats['avg_latency_ms']} ms</code>\n"
        f"└ 💤 Joriy dinamik uyqu: <code>{ai_stats['current_dynamic_sleep']}s</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ {html.bold('DIQQAT:')} Bu yerda amallarni bajarishda ehtiyot bo'ling.\n"
        f"👇 Ijro etish uchun operatsiyani tanlang:"
    )

    # 🎛️ Tugmalar dizayni va joylashuvi
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Baza Import", callback_data="baza_import", style="primary"),
                InlineKeyboardButton(text="📤 Baza Export ", callback_data="baza_export", style="primary")
            ],
            [
                # Yangilash tugmasi - joy o'zgarganini qayta tekshirish uchun silliqqina shu oynani qayta yuklaydi
                InlineKeyboardButton(text="🔄 Statni yangilash", callback_data="creator_db_panel", style="primary")
            ],
            [
                InlineKeyboardButton(text="🗑️  OutboxEvent tozalash", callback_data="outboxevent_clear", style="primary")
            ],
            [
                InlineKeyboardButton(text="🗑️ Bazani toliq tozalash (Clear)", callback_data="baza_clear", style="danger")
            ],
            [
                InlineKeyboardButton(text="⬅️ Bosh panelga", callback_data="creator_panel", style="danger")  
            ]
        ]
    )

    # Media xabarlarni toza matnga almashtirish mantiqi
    if callback.message.photo or callback.message.video:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.message.answer(text=text, reply_markup=kb, parse_mode="HTML")
        return

    # Toza matn bo'lsa, silliq edit_text (Xuddi dashboardlar kabi ma'lumot silliq yangilanadi)
    try:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logger.error(f"❌ Baza bo'limida Telegram xatoligi: {e}")
    except Exception as e:
        logger.error(f"❌ Baza bo'limida kutilmagan xatolik: {e}")



    
    # =========================================================
# 1. 🗑️ OUTBOX TOZALASH TUGMASI BOSILGANDA (TASDIQLASH)
# =========================================================
@router.callback_query(F.data == "outboxevent_clear")
async def confirm_outbox_clear_request(callback: CallbackQuery):
    await callback.answer()
    
    text = (
        f"❓ {html.bold('OutboxEvent loglarini tozalash')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Rostdan ham tizimda qayta ishlab bo‘lingan barcha kesh va sinxronizatsiya loglarini o‘chirmoqchimisiz?\n\n"
        f"ℹ️ {html.italic('Bu amal faqat muvaffaqiyatli yakunlangan loglarni o‘chiradi, asosiy kontent (anime, qism, user) larga mutlaqo zarar yetkazmaydi hamda bazada ancha joy ochadi.')}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, tozalansin", callback_data="confirm_outbox:yes", style="primary"),
            InlineKeyboardButton(text="❌ Yo‘q, bekor qilish", callback_data="creator_db_panel", style="danger")
        ]
    ])
    
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


# =========================================================
# 2. ⚡ YAKUNIY TOZALASH AMALI (HA / YO'Q)
# =========================================================
@router.callback_query(F.data.startswith("confirm_outbox:"))
async def finalize_outbox_clear(callback: CallbackQuery, user_service: UserService):
    await callback.answer()
    
    decision = callback.data.split(":")[1]
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Baza paneliga qaytish", callback_data="creator_db_panel", style="danger")]
    ])
    
    if decision == "yes":
        # Servis orqali eski loglarni tozalaymiz
        count = await user_service.clean_outbox_events()
        
        text = (
            f"🧹 {html.bold('Tozalash yakunlandi!')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Vazifasini bajarib bo‘lgan jami {html.code(count)} ta OutboxEvent loglari bazadan muvaffaqiyatli o‘chirib tashlandi.\n\n"
            f"📉 Baza diski yengillashdi va xavfsizlik ta'minlandi."
        )
    else:
        text = f"❌ {html.bold('Tozalash amali bekor qilindi.')}\n\nHech qanday log o‘chirilmadi."

    await callback.message.edit_text(text=text, reply_markup=back_kb, parse_mode="HTML")



    # ================= SAFE EXECUTE SQL SCRIPT (IMPORT) =================
    @staticmethod
    async def execute_sql_backup(session: Any, sql_content: str) -> bool:
        from sqlalchemy import text
        session = await UserRepository._prepare_session(session)
        
        try:
            # 1. Xavfsizlik uchun cheklovlarni (Foreign Key) vaqtinchalik o'chirib turish ham mumkin,
            # lekin toza SQL dump ishlatilsa, bitta tranzaksiya ichida bajarilgani ma'qul.
            
            # 2. SQL tarkibidagi buyruqlarni toza matn ko'rinishida ijro etamiz
            # PostgreSQL dump faylida "DROP TABLE IF EXISTS", "CREATE TABLE" va "INSERT" buyruqlari tartib bilan bo'ladi
            await session.execute(text(sql_content))
            
            await session.flush()
            return True
        except Exception as e:
            logger.error(f"❌ SQL dump ijro etishda jiddiy xatolik: {e}")
            return False
        



    
    # =========================================================
# 1. TUGMA BOSILGANDA - FAYL KUTISH REJIMINI YOQISH
# =========================================================
@router.callback_query(F.data == "baza_import")
async def start_baza_import(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # FSM holatni yoqamiz
    await state.set_state(AdminDBStates.waiting_for_backup_file)
    
    text = (
        f"📥 {html.bold('Baza Import Tizimi (Restore)')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tizimni zaxiradan qayta tiklash uchun PostgreSQL formatidagi {html.code('.sql')} "
        f"faylini ushbu chatga {html.underline('Hujjat (Document) ko‘rinishida')} yuboring.\n\n"
        f"⚠️ {html.bold('OGOHLANTIRISH:')} Import muvaffaqiyatli yakunlansa, joriy bazadagi barcha ma'lumotlar "
        f"yuborilgan fayldagi ma'lumotlarga to'liq almashadi va keshlar tozalanadi!\n\n"
        f"❌ Bekor qilish uchun istalgan matnni yozing yoki quyidagi tugmani bosing:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Amallarni bekor qilish", callback_data="creator_db_panel", style="danger")]
    ])
    
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


# =========================================================
# 2. FAYL KELGANDA - UNI YUKLAB OLIB BAZAGA URISH
# =========================================================
@router.message(AdminDBStates.waiting_for_backup_file, F.document)
async def process_backup_file_import(message: Message, state: FSMContext, user_service: UserService):
    # Fayl kengaytmasini tekshiramiz (.sql bo'lishi shart)
    file_name = message.document.file_name
    if not file_name.endswith('.sql'):
        await message.reply(
            text="❌ {html.bold('Xato fayl formati!')}\n\nFaqatgina {html.code('.sql')} kengaytmasiga ega bo‘lgan toza Postgres dump faylini yuborishingiz shart.",
            parse_mode="HTML"
        )
        return

    # Yuklanish jarayonini ko'rsatish xabari
    status_msg = await message.reply("⏳ Fayl o‘qilmoqda va tekshirilmoqda, iltimos kuting...")
    
    try:
        # Faylni xotiraga (BytesIO) yuklab olamiz
        file_io = io.BytesIO()
        await message.bot.download(file=message.document.file_id, destination=file_io)
        
        # Baytlarni matnga o'giramiz (UTF-8 formatida)
        sql_content = file_io.getvalue().decode('utf-8')
        
        await status_msg.edit_text("⚡ Baza qayta tiklanmoqda va L1/L2 keshlar invalidatsiya qilinmoqda...")
        
        # Servis orqali importni ishga tushiramiz
        success = await user_service.import_database_dump(sql_content)
        
        # FSM ni yopamiz
        await state.clear()
        
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Baza paneliga qaytish", callback_data="creator_db_panel", style="primary")]
        ])
        
        if success:
            await status_msg.edit_text(
                text=f"✅ {html.bold('Muvaffaqiyatli import qilindi!')}\n\n"
                     f"Baza muvaffaqiyatli zaxiradan qayta tiklandi. Jami keshlar tozalandi va sinxronizatsiya yangilandi.\n"
                     f"📦 Fayl: {html.code(file_name)}",
                reply_markup=back_kb,
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                text="❌ {html.bold('Import muvaffaqiyatsiz tugadi!')}\n\nSQL sintaksisida yoki jadvallar ketma-ketligida xatolik yuz berdi. Baza o'zgarishsiz qoldi.",
                reply_markup=back_kb,
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"🔥 Import jarayonida jiddiy crash: {e}")
        await state.clear()
        await status_msg.edit_text(
            text=f"🔥 {html.bold('Tizim xatoligi!')}\n\nFaylni qayta ishlashda kutilmagan xato yuz berdi: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Panelga qaytish", callback_data="creator_db_panel", style="danger")]
            ]),
            parse_mode="HTML"
        )


# =========================================================
# 3. FAYL O'RNIGA MATN YUBORILSA - BEKOR QILISH MANTIQI
# =========================================================
@router.message(AdminDBStates.waiting_for_backup_file)
async def cancel_import_on_text(message: Message, state: FSMContext):
    await state.clear()
    await message.reply(
        text="❌ Baza import qilish jarayoni bekor qilindi. Hech qanday o‘zgarish amalga oshirilmadi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Baza paneliga qaytish", callback_data="creator_db_panel", style="primary")]
        ])
    )




@router.callback_query(F.data == "baza_export")
async def process_database_export(callback: CallbackQuery, user_service: UserService):
    # Yuklanish vaqt olishi mumkinligi sababli tepada "soat" belgisini aylantirib turamiz
    # va xabar beramiz
    await callback.answer("⏳ SQL zaxira nusxasi tayyorlanmoqda...", show_alert=False)
    
    status_msg = await callback.message.answer("⚡ Baza jadvallari tahlil qilinmoqda va SQL dump generatsiya qilinmoqda...")

    try:
        # 1. Servis orqali toza SQL matnini olamiz
        sql_dump_content = await user_service.export_database_dump()
        
        # 2. Matnni baytlar oqimiga (bytes) o'tkazamiz
        file_bytes = sql_dump_content.encode('utf-8')
        
        # Sifati va sanasini fayl nomiga qo'shib chiroyli nom beramiz
        current_date = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        backup_filename = f"ani_nowuz_backup_{current_date}.sql"
        
        # 3. Aiogram uchun virtual kirish faylini tayyorlaymiz
        document_file = BufferedInputFile(file_bytes, filename=backup_filename)
        
        # Status xabarni o'chiramiz
        await status_msg.delete()
        
        # 4. Creatorga faylni daxshatli UX xabari bilan yuboramiz
        text = (
            f"📤 {html.bold('Baza muvaffaqiyatli Eksport qilindi!')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Fayl nomi: {html.code(backup_filename)}\n"
            f"📊 Fayl formati: <code>PostgreSQL SCRIPT (.sql)</code>\n"
            f"🛡️ Holati: <code>Xavfsiz / Buzilishlarsiz</code>\n\n"
            f"ℹ️ {html.italic('Ushbu faylni kelajakda ixtiyoriy serverdagi Postgres bazasiga Import bolimi orqali yuklab, tizimni toliq qayta tiklashingiz mumkin.')}"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Baza paneliga qaytish", callback_data="creator_db_panel", style="primary")]
        ])
        
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=document_file,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"🔥 Export handler crash: {e}")
        await status_msg.edit_text(
            text=f"❌ {html.bold('Eksportda xatolik yuz berdi!')}\n\nTizim SQL faylni shakllantira olmadi: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Panelga qaytish", callback_data="creator_db_panel", style="danger")]
            ]),
            parse_mode="HTML"
        )