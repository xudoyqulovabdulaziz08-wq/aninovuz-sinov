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