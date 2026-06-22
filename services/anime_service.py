from __future__ import annotations

import logging
from typing import Any, Optional, Dict, List

from repositories.anime_repository import AnimeRepository
from database.cache import cache_manager  # yagona universal cache manager

logger = logging.getLogger("AnimeService")


class AnimeService:
    """
    🚀 Business Logic Layer (CACHE-AWARE & TRANSACTION-SAFE)
    - Tranzaksiyani to'liq nazorat qiladi (Commit / Rollback)
    - Faqatgina muvaffaqiyatli Commitdan keyin keshga tegadi
    """

    def __init__(self, session):
        self.session = session
        # 💡 TO'G'RI: Repozitoriy klassini instansiya (obyekt) sifatida yaratamiz
        self.repo = AnimeRepository() 
        self.cache = cache_manager

    # ==================================================
    # 🔥 GET BY ID (CACHE-FIRST)
    # ==================================================
    async def get_anime(self, anime_id: int) -> Optional[Dict]:
        cached = await self.cache.get("anime", anime_id)
        if cached:
            logger.debug(f"🎯 CACHE HIT anime_id={anime_id}")
            return cached

        anime = await self.repo.get_by_id(self.session, anime_id)
        if not anime:
            return None

        await self.cache.set("anime", anime_id, anime, ttl=3600)
        return anime

    # ==================================================
    # 📋 LIST ANIME (CACHE-FIRST)
    # ==================================================
    async def list_anime(self) -> List[Dict]:
        cached = await self.cache.get("anime", "all")
        if cached is not None:  # Bo'sh ro'yxat kelsa ham kesh ishlashi uchun
            return cached

        data = await self.repo.list(self.session)
        await self.cache.set("anime", "all", data, ttl=1800)
        return data

    # ==================================================
    # ➕ CREATE ANIME (TRANSACTION SAFE)
    # ==================================================
    async def create_anime(
        self,
        title: str,
        poster_id: Optional[str],
        year: int,
        is_completed: bool,
        genres: List[int],
        description: str,
        languages: list
    ) -> Dict:
        try:
            anime = await self.repo.create(
                self.session,
                title,
                poster_id,
                year,
                is_completed,
                genres,
                description,
                languages
            )
            
            await self.session.commit()
            anime_id = anime["anime_id"]

            await self.cache.set("anime", anime_id, anime, ttl=3600)
            await self.cache.invalidate("anime", "all", broadcast=True)
            await self.cache.invalidate("search_map", "all", broadcast=True)

            logger.info(f"✅ Anime created + cached: {anime_id}")
            return anime

        except Exception as e:
            # 💡 SAFE ROLLBACK: AttributeError (NoneType) xavfini butunlay yo'q qilamiz
            if self.session and hasattr(self.session, "rollback"):
                await self.session.rollback()
            logger.error(f"❌ Failed to create anime: {e}")
            raise e

    # ==================================================
    # 🎬 ADD EPISODE (TRANSACTION SAFE)
    # ==================================================
    async def add_episode(
        self,
        anime_id: int,
        episode_num: int,
        file_id: str
    ) -> bool:
        try:
            ok = await self.repo.add_episode(self.session, anime_id, episode_num, file_id)
            await self.session.commit()

            if ok:
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
            return ok

        except Exception as e:
            if self.session and hasattr(self.session, "rollback"):
                await self.session.rollback()
            logger.error(f"❌ Failed to add episode: {e}")
            raise e


    # ==================================================
    # 🗑 DELETE EPISODE (TRANSACTION SAFE)
    # ==================================================
    async def delete_episode(self, anime_id: int, episode_num: int) -> bool:
        try:
            # Session'ni oldindan xavfsiz "uyg'otamiz"
            if hasattr(self.session, "_ensure_session"):
                await self.session._ensure_session()
            
            # Repozitoriy orqali o'chirishni ijro etamiz
            ok = await self.repo.delete_episode(self.session, anime_id, episode_num)
            
            # Muammosiz o'chsa, tranzaksiyani saqlaymiz
            await self.session.commit()

            if ok:
                # Keshni invalidatsiya qilamiz, shunda ro'yxat darhol yangilanadi
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
                logger.info(f"🗑 Episode cache invalidated: Anime {anime_id}, Ep {episode_num}")

            return ok

        except Exception as e:
            if self.session and hasattr(self.session, "rollback"):
                await self.session.rollback()
            logger.error(f"❌ Failed to delete episode: {e}")
            raise e

    # ==================================================
    # 🗑 DELETE ANIME (TRANSACTION SAFE)
    # ==================================================
    async def delete_anime(self, anime_id: int) -> bool:
        try:
            # Session'ni oldin "uyg'otamiz"
            if hasattr(self.session, "_ensure_session"):
             await self.session._ensure_session()
            
            ok = await self.repo.delete(self.session, anime_id)
        
            await self.session.commit()   # ✅ Endi bir xil session

            if ok:
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
                await self.cache.invalidate("search_map", "all", broadcast=True)

            return ok

        except Exception as e:
            if self.session and hasattr(self.session, "rollback"):
                await self.session.rollback()
            logger.error(f"❌ Failed to delete anime: {e}")
            raise e

    # ==================================================
    # 🔎 SEARCH MAP 
    # ==================================================
    async def get_search_map(self) -> Dict:
        cached = await self.cache.get("search_map", "all")
        if cached:
            return cached

        all_anime = await self.repo.list(self.session)
        search_map = {
            str(a["anime_id"]): f'{a["title"]} ({a.get("year")})'
            for a in all_anime
        }

        await self.cache.set("search_map", "all", search_map, ttl=3600)
        return search_map