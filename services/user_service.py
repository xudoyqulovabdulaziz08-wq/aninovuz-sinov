from __future__ import annotations

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timezone

from repositories.user_repository import UserRepository
from database.cache import cache_manager  # Universal CacheManager
from database.models import UserStatus

logger = logging.getLogger("UserService")


class UserService:
    """
    🚀 Business Logic Layer for Users (CACHE-AWARE & TRANSACTION-SAFE)
    - Kesh birinchi strategiyasi (Cache-first)
    - Tranzaksiyaviy xavfsizlik (Commit / Rollback)
    - Dinamik VIP validatsiyasi
    """

    def __init__(self, session):
        self.session = session
        self.repo = UserRepository
        self.cache = cache_manager

    # ==================================================
    # 🕵️‍♂️ INTERNAL HELPER: DYNAMIC VIP CHECK
    # ==================================================
    def _ensure_fresh_vip_status(self, user: Dict) -> Dict:
        """
        Keshdan kelgan yoki DBdan olingan user datasi ichidagi is_vip qiymatini
        ayni joriy vaqt (datetime.now) bilan dinamik tekshirib beradi.
        """
        if user["status"] != UserStatus.VIP.value:
            user["is_vip"] = False
            return user

        if user["vip_expire_date"] is None:
            user["is_vip"] = True
            return user

        try:
            # ISO formatdagi stringni ob'ektga o'tkazamiz
            expire_dt = datetime.fromisoformat(user["vip_expire_date"])
            now = datetime.now(timezone.utc)
            
            # Agar muddati o'tib ketgan bo'lsa dinamik o'zgartiramiz
            if now > expire_dt:
                user["is_vip"] = False
                # Eslatma: DBda status hamon VIP bo'lishi mumkin, uni fon ishlari (cron) tozalaydi,
                # lekin foydalanuvchiga xizmat ko'rsatishda biz unga VIP bermaymiz.
            else:
                user["is_vip"] = True
        except Exception as e:
            logger.error(f"Error parsing vip_expire_date: {e}")
            user["is_vip"] = False

        return user

    # ==================================================
    # 🔥 GET OR CREATE USER (SESSION & CACHE SYNC)
    # ==================================================
    async def get_or_create_user(self, tg_user: Any) -> Dict:
        try:
            # 1. DB write / upsert via repo
            user = await self.repo.get_or_create(self.session, tg_user)
            
            # 2. Commit transaction (Outbox eventlar ham birga yoziladi)
            await self.session.commit()
            
            # 3. Keshni yangilash
            user = self._ensure_fresh_vip_status(user)
            await self.cache.set("users", str(tg_user.id), user, ttl=7200) # 2 soat kesh

            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed in get_or_create_user for {tg_user.id}: {e}")
            raise e

    # ==================================================
    # 🎯 GET USER BY ID (CACHE-FIRST WITH EXPIRE VALIDATION)
    # ==================================================
    async def get_user(self, user_id: int) -> Optional[Dict]:
        # 1. Keshdan qidirish
        cached_user = await self.cache.get("users", str(user_id))
        if cached_user:
            logger.debug(f"🎯 CACHE HIT user_id={user_id}")
            return self._ensure_fresh_vip_status(cached_user)

        # 2. DB Fallback
        user = await self.repo.get_by_id(self.session, user_id)
        if not user:
            return None

        # 3. Keshni to'ldirish
        user = self._ensure_fresh_vip_status(user)
        await self.cache.set("users", str(user_id), user, ttl=7200)

        return user

    # ==================================================
    # 💎 SET VIP STATUS
    # ==================================================
    async def grant_vip(self, user_id: int, days: int) -> bool:
        try:
            ok = await self.repo.set_vip(self.session, user_id, days)
            if not ok:
                await self.session.rollback()
                return False

            await self.session.commit()

            # Keshni invalidatsiya qilish (Kesh o'chadi, keyingi so'rovda DB dan yangisi olinadi)
            await self.cache.invalidate("users", str(user_id), broadcast=True)
            logger.info(f"✅ VIP granted to user {user_id} for {days} days.")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to set VIP for user {user_id}: {e}")
            raise e

    # ==================================================
    # ❌ REMOVE VIP STATUS
    # ==================================================
    async def revoke_vip(self, user_id: int) -> bool:
        try:
            ok = await self.repo.remove_vip(self.session, user_id)
            if not ok:
                await self.session.rollback()
                return False

            await self.session.commit()

            await self.cache.invalidate("users", str(user_id), broadcast=True)
            logger.info(f"✅ VIP revoked from user {user_id}.")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to revoke VIP for user {user_id}: {e}")
            raise e

    # ==================================================
    # 💰 UPDATE POINTS
    # ==================================================
    async def increment_points(self, user_id: int, points: int) -> bool:
        try:
            ok = await self.repo.update_points(self.session, user_id, points)
            if not ok:
                await self.session.rollback()
                return False

            await self.session.commit()

            # Points tez-tez o'zgarishi mumkinligi sababli kesh darhol o'chiriladi
            await self.cache.invalidate("users", str(user_id), broadcast=True)
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to update points for user {user_id}: {e}")
            raise e

    # ==================================================
    # 🔔 TOGGLE SLEEP REMINDER
    # ==================================================
    async def toggle_reminder(self, user_id: int) -> bool:
        try:
            ok = await self.repo.toggle_sleep_reminder(self.session, user_id)
            if not ok:
                await self.session.rollback()
                return False

            await self.session.commit()

            await self.cache.invalidate("users", str(user_id), broadcast=True)
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to toggle reminder for user {user_id}: {e}")
            raise e

    # ==================================================
    # 🗑 DELETE USER
    # ==================================================
    async def terminate_user(self, user_id: int) -> bool:
        try:
            ok = await self.repo.delete(self.session, user_id)
            if not ok:
                await self.session.rollback()
                return False

            await self.session.commit()

            # Keshni butunlay tozalash
            await self.cache.invalidate("users", str(user_id), broadcast=True)
            logger.info(f"🗑 User {user_id} completely deleted from system.")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to delete user {user_id}: {e}")
            raise e