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
        self.repo = AnimeRepository
        self.cache = cache_manager

    # ==================================================
    # 🔥 GET BY ID (CACHE-FIRST)
    # ==================================================
    async def get_anime(self, anime_id: int) -> Optional[Dict]:
        # 1. Keshdan izlash
        cached = await self.cache.get("anime", anime_id)
        if cached:
            logger.debug(f"🎯 CACHE HIT anime_id={anime_id}")
            return cached

        # 2. DB fallback
        anime = await self.repo.get_by_id(self.session, anime_id)

        if not anime:
            return None

        # 3. Keshga yozish
        await self.cache.set("anime", anime_id, anime, ttl=3600)

        return anime

    # ==================================================
    # 📋 LIST ANIME (CACHE-FIRST)
    # ==================================================
    async def list_anime(self) -> List[Dict]:
        cached = await self.cache.get("anime", "all")
        if cached:
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
            # 1. DB write (flush qilinadi, hali commit yo'q)
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
            
            # 2. Haqiqiy DB saqlash (COMMIT)
            await self.session.commit()
            
            # ----------------------------------------------
            # FAqat commit muvaffaqiyatli bo'lsa keshga o'tamiz
            # ----------------------------------------------
            anime_id = anime["anime_id"]

            # 3. Keshni yangilash
            await self.cache.set("anime", anime_id, anime, ttl=3600)
            await self.cache.invalidate("anime", "all", broadcast=True)
            
            # Search mapni butunlay tozalash (yoki invalidate qilish), navbatdagi so'rov o'zi qayta quradi
            await self.cache.invalidate("search_map", "all", broadcast=True)

            logger.info(f"✅ Anime created + cached: {anime_id}")
            return anime

        except Exception as e:
            await self.session.rollback() # Xato bo'lsa bekor qilish
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
            # DB write
            ok = await self.repo.add_episode(self.session, anime_id, episode_num, file_id)
            
            # Haqiqiy saqlash
            await self.session.commit()

            if ok:
                # Obyekt tarkibi (episodes list) o'zgargani uchun uning keshini tozalaymiz
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
                
                # Eslatma: Episode list alohida kesh qilinmagan, u anime.to_dict() ichida yashaydi.
            return ok

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to add episode: {e}")
            raise e

    # ==================================================
    # 🗑 DELETE ANIME (TRANSACTION SAFE)
    # ==================================================
    async def delete_anime(self, anime_id: int) -> bool:
        try:
            ok = await self.repo.delete(self.session, anime_id)
            
            # Haqiqiy o'chirish
            await self.session.commit()

            if ok:
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
                await self.cache.invalidate("search_map", "all", broadcast=True)

            return ok

        except Exception as e:
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

        # Keshda bo'lmasa DB dan olib qayta qurish
        all_anime = await self.repo.list(self.session)

        search_map = {
            str(a["anime_id"]): f'{a["title"]} ({a.get("year")})'
            for a in all_anime
        }

        await self.cache.set("search_map", "all", search_map, ttl=3600)
        return search_map