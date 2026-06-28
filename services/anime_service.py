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
    # 🔥 UPDATE ANIME (TRANSACTION-SAFE & CACHE-AWARE)
    # ==================================================
    async def update_anime(self, anime_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Business Logic: Animeni yangilaydi, DB commit qiladi va muvaffaqiyatli bo'lsa,
        Valkey keshidan eski ma'lumotni o'chirib tashlaydi (Invalidate).
        """
        if not update_data:
            return False

        # ✅ TO'G'RI VARIANT (Teskari sleshlar olib tashlandi):
        if hasattr(self.session, "_ensure_session"):
            await self.session._ensure_session()

        try:
            # Repozitoriy orqali bazadagi fieldlarni yangilaymiz
            success = await self.repo.update(self.session, anime_id, update_data)
            
            if not success:
                return False
                
            if hasattr(self.session, "commit"):
                await self.session.commit()
                
            await self.cache.invalidate("anime", anime_id)
            logger.info(f"✅ Anime ID={anime_id} muvaffaqiyatli yangilandi va keshi tozalandi.")
            return True
            
        except Exception as e:
            logger.error(f"🚨 Service ichida animeni yangilashda xato yuz berdi: {e}")
            if hasattr(self.session, "rollback"):
                await self.session.rollback()
            return False
        

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
    # 🔄 UPDATE EPISODE FILE (TRANSACTION SAFE)
    # ==================================================
    async def update_episode_file(self, anime_id: int, episode_num: int, new_file_id: str) -> bool:
        try:
            if hasattr(self.session, "_ensure_session"):
                await self.session._ensure_session()
            
            ok = await self.repo.update_episode_file(self.session, anime_id, episode_num, new_file_id)
            await self.session.commit()

            if ok:
                # Keshni invalidatsiya qilamiz, shunda yangi video pleerda darhol ko'rinadi
                await self.cache.invalidate("anime", anime_id, broadcast=True)
                await self.cache.invalidate("anime", "all", broadcast=True)
                await self.cache.invalidate("anime_episodes", anime_id, broadcast=True)
                logger.info(f"🔄 Episode file updated + cache invalidated: Anime {anime_id}, Ep {episode_num}")

            return ok

        except Exception as e:
            if self.session and hasattr(self.session, "rollback"):
                await self.session.rollback()
            logger.error(f"❌ Failed to update episode file: {e}")
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
    

    # ==================================================
    # 🔎 SEARCH BY GENRES MULTI (OPTIMIZED DB-LEVEL)
    # ==================================================
    async def search_by_genres(self, genre_ids: List[int]) -> List[Dict]:
        """Tanlangan barcha janrlarga mos keluvchi animelarni bazadan eng tezkor usulda filtrlab beradi."""
        if not genre_ids:
            return []
        return await self.repo.get_by_genres(self.session, genre_ids)
    



    # ==================================================
    # 📹 GET ANIME EPISODES CACHE (CACHE-FIRST)
    # ==================================================
    async def get_anime_episodes_cache(self, anime_id: int) -> List[Dict]:
        """
        🚀 Anime qismlarini keshdan (Cache-First) tezkor yuklab berish funksiyasi.
        Keshda bo'lmasa DBdan oladi va 1 soatga (ttl=3600) saqlaydi.
        """
        # 1. Avval kesh menedjerdan ushbu animening qismlarini so'raymiz
        cached_episodes = await self.cache.get("anime_episodes", anime_id)
        if cached_episodes is not None:
            logger.debug(f"🎯 CACHE HIT: anime_episodes loaded from cache for anime_id={anime_id}")
            return cached_episodes

        # 2. Agar keshda bo'lmasa, sessiyani tekshirib repozitoriyga yuzlanamiz
        if hasattr(self.session, "_ensure_session"):
            await self.session._ensure_session()

        episodes = await self.repo.get_episodes_by_anime_id(self.session, anime_id)
        
        # 3. Kelgan ma'lumotni 1 soatga (3600 soniya) keshga yozib qo'yamiz
        await self.cache.set("anime_episodes", anime_id, episodes, ttl=3600)
        logger.info(f"💾 CACHE SET: Anime episodes cached for anime_id={anime_id} (TTL: 1h)")
        
        return episodes
    

    async def update_genres(self, anime_id: int, genre_ids: list[int]) -> bool:
        """Business Logic: Janrlarni yangilash, commit qilish va keshni invalidatsiya qilish"""
        if hasattr(self.session, "_ensure_session"):
            await self.session._ensure_session()
            
        try:
            success = await self.repo.update_anime_genres(self.session, anime_id, genre_ids)
            if not success:
                return False
                
            if hasattr(self.session, "commit"):
                await self.session.commit()
                
            # Keshni va barcha qidiruv xaritalarini majburiy tozalaymiz
            await self.cache.invalidate("anime", anime_id)
            await self.cache.invalidate("anime", "all", broadcast=True)
            return True
        except Exception as e:
            logger.error(f"🚨 Janrlarni yangilashda service xatosi: {e}")
            if hasattr(self.session, "rollback"):
                await self.session.rollback()
            return False


    # ==================================================
    # 📥 IMPORT DATABASE BACKUP & FLUSH CACHE
    # ==================================================
    async def import_database_dump(self, sql_content: str) -> bool:
        try:
            # 1. SQL Dumpni bazaga xavfsiz yozamiz
            success = await self.repo.execute_sql_backup(self.session, sql_content)
            
            if not success:
                await self.session.rollback()
                return False
                
            # 2. Tranzaksiyani tasdiqlaymiz
            await self.session.commit()
            
            # 3. 🧹 CRITICAL UX: Butun tizim keshini tozalaymiz (Flush All L1/L2)
            # Chunki yangi baza import bo'lgach, eski keshlar butunlay o'z kuchini yoqotadi
            await self.cache.clear_all() # Yoki valkey.redis.flushall()
            
            logger.info("📥 Database successfully restored from backup. Cache flushed completely.")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to restore database: {e}")
            raise e
        
    