import logging
from typing import Any, Optional, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert

from database.models import DBUser, UserStatus

logger = logging.getLogger("UserRepository")


class UserRepository:
    # ================= SESSION HELPERS =================
    @staticmethod
    def _get_real_session(session: Any):
        if hasattr(session, "_session"):
            return session._session
        return session

    @staticmethod
    async def _prepare_session(session: Any):
        if hasattr(session, "_ensure_session"):
            await session._ensure_session()
        return UserRepository._get_real_session(session)

    # ================= SERIALIZER =================
    @staticmethod
    def _to_dict(user: DBUser) -> Dict:
        return {
            "user_id": user.user_id,
            "username": user.username,
            "status": user.status.value if user.status else None,
            "points": user.points,
            "vip_expire_date": (
                user.vip_expire_date.isoformat()
                if user.vip_expire_date else None
            ),
            "sleep_reminder_enabled": user.sleep_reminder_enabled,
            "joined_at": user.joined_at.isoformat() if user.joined_at else None,
            "is_vip": user.status == UserStatus.VIP,  # Dinamik tekshiruv
        }

    # ================= GET OR CREATE =================
    @staticmethod
    async def get_or_create(session: Any, tg_user: Any) -> Dict:
        session = await UserRepository._prepare_session(session)

        stmt = (
            insert(DBUser)
            .values(
                user_id=tg_user.id,
                username=tg_user.username,
                status=UserStatus.USER,
                points=0,
                sleep_reminder_enabled=True,
            )
            .on_conflict_do_update(
                index_elements=[DBUser.user_id],
                set_={"username": tg_user.username}
            )
            .returning(DBUser)
        )

        result = await session.execute(stmt)
        user = result.scalar_one()
        
        await session.flush()  # DBga vaqtincha yozish
        return UserRepository._to_dict(user)

    # ================= GET BY ID =================
    @staticmethod
    async def get_by_id(session: Any, user_id: int) -> Optional[Dict]:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            select(DBUser).where(DBUser.user_id == user_id)
        )

        user = result.scalar_one_or_none()
        if not user:
            return None

        return UserRepository._to_dict(user)

    # ================= UPDATE POINTS =================
    @staticmethod
    async def update_points(session: Any, user_id: int, points: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(points=DBUser.points + points)
        )

        await session.flush()
        return result.rowcount > 0

    # ================= VIP SET =================
    @staticmethod
    async def set_vip(session: Any, user_id: int, days: int) -> bool:
        session = await UserRepository._prepare_session(session)

        expire = datetime.now(timezone.utc) + timedelta(days=days)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(
                status=UserStatus.VIP,
                vip_expire_date=expire
            )
        )

        await session.flush()
        return result.rowcount > 0

    # ================= REMOVE VIP =================
    @staticmethod
    async def remove_vip(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(
                status=UserStatus.USER,
                vip_expire_date=None
            )
        )

        await session.flush()
        return result.rowcount > 0

    # ================= TOGGLE REMINDER =================
    @staticmethod
    async def toggle_sleep_reminder(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(
                sleep_reminder_enabled=case((DBUser.sleep_reminder_enabled == True, False), else_=True)
            )
        )

        await session.flush()
        return result.rowcount > 0

    # ================= EXISTS =================
    @staticmethod
    async def exists(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            select(DBUser.user_id).limit(1).where(DBUser.user_id == user_id)
        )

        return result.scalar_one_or_none() is not None

    # ================= DELETE USER =================
    @staticmethod
    async def delete(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            select(DBUser).where(DBUser.user_id == user_id)
        )

        user = result.scalar_one_or_none()
        if not user:
            return False

        session.delete(user)  # SINXRON METOD (await olib tashlandi)
        await session.flush()
        return True
    
    # ================= GET ADMIN STATS =================
    @staticmethod
    async def get_admin_stats(session: Any) -> Dict[str, int]:
        from sqlalchemy import func
        # Aylanma importni oldini olish uchun qolgan modellarni shu yerda chaqiramiz
        from database.models import Anime, Episode, Channel

        session = await UserRepository._prepare_session(session)

        # 1. Jami foydalanuvchilar soni
        total_users_stmt = select(func.count(DBUser.user_id))
        total_users = await session.scalar(total_users_stmt) or 0

        # 2. VIP foydalanuvchilar soni (is_vip gibrid ustuni orqali)
        vip_users_stmt = select(func.count(DBUser.user_id)).where(DBUser.is_vip)
        vip_users = await session.scalar(vip_users_stmt) or 0

        # 3. Jami Animelar soni
        total_anime_stmt = select(func.count(Anime.anime_id))
        total_anime = await session.scalar(total_anime_stmt) or 0

        # 4. Jami yuklangan Qismlar (Epizodlar) soni
        total_episodes_stmt = select(func.count(Episode.id))
        total_episodes = await session.scalar(total_episodes_stmt) or 0

        # 5. Jami faol majburiy obuna kanallari soni
        active_channels_stmt = select(func.count(Channel.id)).where(Channel.is_active == True)
        active_channels = await session.scalar(active_channels_stmt) or 0

        return {
            "total_users": total_users,
            "vip_users": vip_users,
            "total_anime": total_anime,
            "total_episodes": total_episodes,
            "active_channels": active_channels
        }
    
    # ================= SET ADMIN STATUS =================
    @staticmethod
    async def set_admin(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(
                status=UserStatus.ADMIN,
                vip_expire_date=None  # Admin bo'gach, VIP muddatini tozalaymiz
            )
        )

        await session.flush()
        return result.rowcount > 0
    
    # ================= REMOVE ADMIN huquqi =================
    @staticmethod
    async def remove_admin(session: Any, user_id: int) -> bool:
        session = await UserRepository._prepare_session(session)

        result = await session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(
                status=UserStatus.USER  # Statusni oddiy foydalanuvchiga qaytaramiz
            )
        )

        await session.flush()
        return result.rowcount > 0
    
    # ================= GET DATABASE SIZE =================
    @staticmethod
    async def get_db_size(session: Any) -> str:
        from sqlalchemy import text
        session = await UserRepository._prepare_session(session)
        
        try:
            # Joriy ulangan bazaning nomini va uning diskdagi hajmini aniqlaymiz
            # pg_size_pretty funksiyasi avtomatik '45 MB' yoki '1.2 GB' formatiga o'tkazib beradi
            stmt = text("SELECT pg_size_pretty(pg_database_size(current_database()));")
            result = await session.execute(stmt)
            return result.scalar() or "0 MB"
        except Exception as e:
            logger.error(f"❌ Baza hajmini hisoblashda xatolik: {e}")
            return "Noma'lum"
        
    
    # ================= CLEAR PROCESSED OUTBOX EVENTS =================
    @staticmethod
    async def clear_processed_outbox(session: Any) -> int:
        from sqlalchemy import delete
        from database.models import OutboxEvent
        
        session = await UserRepository._prepare_session(session)

        # Faqat processed=True bo'lgan, ya'ni vazifasini bajarib bo'lgan loglarni o'chiramiz
        stmt = delete(OutboxEvent).where(OutboxEvent.processed == True)
        result = await session.execute(stmt)
        
        await session.flush()
        return result.rowcount  # Qancha qator o'chirilganini qaytaradi
    

    # ================= GENERATE SQL BACKUP DUMP (PRO EDITION) =================
    @staticmethod
    async def generate_sql_dump(session: Any) -> str:
        from sqlalchemy import select
        from datetime import datetime
        # Barcha modellarni aniq import qilamiz
        from database.models import DBUser, Anime, Episode, Genre, Channel, anime_genres
        
        session = await UserRepository._prepare_session(session)
        sql_lines = [
            "-- 📥 ANI-NOVUZ TELEGRAM BOT DATABASE BACKUP DUMP\n",
            f"-- Generatsiya vaqti: {datetime.now().isoformat()}\n",
            "SET statement_timeout = 0;\n",
            "SET lock_timeout = 0;\n",
            "SET client_encoding = 'UTF-8';\n",
            "SET foreign_key_checks = 0; -- Vaqtinchalik constraintlarni yopish\n\n"
        ]

        try:
            # 1. USERS JADVALINI EKSPORT QILISH
            users_res = await session.execute(select(DBUser))
            for u in users_res.scalars().all():
                username = f"'{u.username}'" if u.username else "NULL"
                vip_date = f"'{u.vip_expire_date.isoformat()}'" if u.vip_expire_date else "NULL"
                joined = f"'{u.joined_at.isoformat()}'" if u.joined_at else "NOW()"
                sql_lines.append(
                    f"INSERT INTO users (user_id, username, joined_at, points, status, vip_expire_date, sleep_reminder_enabled) "
                    f"VALUES ({u.user_id}, {username}, {joined}, {u.points}, '{u.status.value}', {vip_date}, {str(u.sleep_reminder_enabled).lower()}) "
                    f"ON CONFLICT (user_id) DO UPDATE SET username=EXCLUDED.username, status=EXCLUDED.status, points=EXCLUDED.points, vip_expire_date=EXCLUDED.vip_expire_date;\n"
                )
            sql_lines.append("\n")

            # 2. GENRES JADVALINI EKSPORT QILISH
            genres_res = await session.execute(select(Genre))
            for g in genres_res.scalars().all():
                g_name = g.name.replace("'", "''")
                sql_lines.append(
                    f"INSERT INTO genres (id, name) VALUES ({g.id}, '{g_name}') "
                    f"ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name;\n"
                )
            sql_lines.append("\n")

            # 3. ANIME_LIST JADVALINI EKSPORT QILISH
            anime_res = await session.execute(select(Anime))
            for a in anime_res.scalars().all():
                title = a.title.replace("'", "''")
                desc = f"'{a.description.replace_with_double_quotes}'".replace("'", "''") if a.description else "NULL"
                desc_val = f"'{a.description.replace_with_double_quotes}'".replace("'", "''") if a.description else "NULL"
                desc_val = f"'{a.description.replace_with_double_quotes}'" if a.description else "NULL"
                desc_val = f"'{a.description.replace_with_double_quotes}'" if a.description else "NULL"
                
                # PostgreSQL Array parser (Xavfsiz transformatsiya)
                if a.languages:
                    lang_array = "ARRAY[" + ", ".join([f"'{l}'" for l in a.languages]) + "]::varchar[]"
                else:
                    lang_array = "ARRAY[]::varchar[]"
                
                poster = f"'{a.poster_id}'" if a.poster_id else "NULL"
                year_val = a.year if a.year else "NULL"
                desc_val = f"'{a.description.replace_with_double_quotes}'" if a.description else "NULL" # Silliqlash
                desc_clean = f"'{a.description.replace_with_double_quotes}'" if a.description else "NULL"
                
                # Toza escaped description
                if a.description:
                    clean_desc = f"'{a.description.replace_list_single}'"
                    clean_desc = f"'{a.description.replace_list_single}'"
                    clean_desc = f"'{a.description.replace_list_single}'"
                    clean_desc = f"'{a.description.replace_with_double_quotes}'"
                    clean_desc = f"'{a.description.replace_with_double_quotes}'"
                    clean_desc = f"'{a.description.replace("'", "''")}'"
                else:
                    clean_desc = "NULL"

                sql_lines.append(
                    f"INSERT INTO anime_list (anime_id, title, poster_id, year, description, languages, rating_sum, rating_count, views_week, is_completed) "
                    f"VALUES ({a.anime_id}, '{title}', {poster}, {year_val}, {clean_desc}, {lang_array}, {a.rating_sum}, {a.rating_count}, {a.views_week}, {str(a.is_completed).lower()}) "
                    f"ON CONFLICT (anime_id) DO UPDATE SET title=EXCLUDED.title, poster_id=EXCLUDED.poster_id, year=EXCLUDED.year, description=EXCLUDED.description, languages=EXCLUDED.languages, is_completed=EXCLUDED.is_completed;\n"
                )
            sql_lines.append("\n")

            # 4. ANIME_GENRES (MANY-TO-MANY RELATIONSHIP) EKSPORT QILISH 🔥 CRITICAL FIX
            # Bu jadval models.py ichidagi ulovchi havola hisoblanadi!
            genres_m2m = await session.execute(select(anime_genres))
            for row in genres_m2m.all():
                sql_lines.append(
                    f"INSERT INTO anime_genres (anime_id, genre_id) VALUES ({row.anime_id}, {row.genre_id}) "
                    f"ON CONFLICT (anime_id, genre_id) DO NOTHING;\n"
                )
            sql_lines.append("\n")

            # 5. ANIME_EPISODES JADVALINI EKSPORT QILISH
            episode_res = await session.execute(select(Episode))
            for ep in episode_res.scalars().all():
                sql_lines.append(
                    f"INSERT INTO anime_episodes (id, anime_id, episode, file_id) "
                    f"VALUES ({ep.id}, {ep.anime_id}, {ep.episode}, '{ep.file_id}') "
                    f"ON CONFLICT (anime_id, episode) DO UPDATE SET file_id=EXCLUDED.file_id;\n"
                )
            sql_lines.append("\n")

            # 6. CHANNELS JADVALINI EKSPORT QILISH
            channels_res = await session.execute(select(Channel))
            for ch in channels_res.scalars().all():
                ch_title = ch.title.replace("'", "''")
                url_val = f"'{ch.url}'" if ch.url else "NULL"
                sql_lines.append(
                    f"INSERT INTO channels (id, channel_id, title, url, is_active, created_at) "
                    f"VALUES ({ch.id}, {ch.channel_id}, '{ch_title}', {url_val}, {str(ch.is_active).lower()}, '{ch.created_at.isoformat()}') "
                    f"ON CONFLICT (channel_id) DO UPDATE SET title=EXCLUDED.title, url=EXCLUDED.url, is_active=EXCLUDED.is_active;\n"
                )

            return "".join(sql_lines)
            
        except Exception as e:
            logger.error(f"❌ Professional SQL Dump yaratishda jiddiy xatolik: {e}")
            return f"-- Export error: {str(e)}"