import logging
from typing import Any, Optional, Dict, List
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from database.models import Anime, Episode, Genre

logger = logging.getLogger("AnimeRepository")

class AnimeRepository:

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
        return AnimeRepository._get_real_session(session)

    # ================= GET BY ID =================
    @staticmethod
    async def get_by_id(session: Any, anime_id: int) -> Optional[Dict]:
        session = await AnimeRepository._prepare_session(session)

        stmt = (
            select(Anime)
            .where(Anime.anime_id == anime_id)
            .options(selectinload(Anime.genres), selectinload(Anime.episodes))
        )

        result = await session.execute(stmt)
        anime = result.scalar_one_or_none()

        if not anime:
            return None

        # Ustunlarni dict qilamiz va munosabatlarni qo'lda xavfsiz qo'shamiz
        data = anime.to_dict()
        data["genres"] = [g.id for g in anime.genres] if hasattr(anime, "genres") else []
        data["episodes"] = [
            {"id": ep.id, "episode": ep.episode, "file_id": ep.file_id} 
            for ep in anime.episodes
        ] if hasattr(anime, "episodes") else []
        
        return data
    

    # ================= GET EPISODES BY ANIME ID =================
    @staticmethod
    async def get_episodes_by_anime_id(session: Any, anime_id: int) -> List[Dict]:
        """
        🎬 Bazadan ma'lum bir animening barcha qismlarini 
        qism raqami bo'yicha tartiblangan holatda tortib beradi.
        """
        real_session = await AnimeRepository._prepare_session(session)

        stmt = (
            select(Episode)
            .where(Episode.anime_id == anime_id)
            .order_by(Episode.episode)  # Qismlar ketma-ketligi (1, 2, 3...) bu buzilmasligi shart!
        )

        result = await real_session.execute(stmt)
        episodes_list = result.scalars().all()

        # Har bir epizod obyektini to_dict() orqali dict formatiga o'giramiz
        return [ep.to_dict() for ep in episodes_list]

    # ================= LIST =================
    @staticmethod
    async def list(session: Any) -> List[Dict]:
        session = await AnimeRepository._prepare_session(session)

        stmt = (
            select(Anime)
            .options(selectinload(Anime.genres), selectinload(Anime.episodes))
            .order_by(desc(Anime.anime_id))
        )

        result = await session.execute(stmt)
        anime_list = []
        
        for anime in result.scalars().all():
            data = anime.to_dict()
            data["genres"] = [g.id for g in anime.genres] if hasattr(anime, "genres") else []
            data["episodes"] = [
                {"id": ep.id, "episode": ep.episode, "file_id": ep.file_id} 
                for ep in anime.episodes
            ] if hasattr(anime, "episodes") else []
            anime_list.append(data)
            
        return anime_list

    # ================= CREATE ANIME =================
    @staticmethod
    async def create(
        session: Any,
        title: str,
        poster_id: Optional[str],
        year: int,
        is_completed: bool,
        genres: List[Any],
        description: str,
        languages: list
    ) -> Dict:
        session = await AnimeRepository._prepare_session(session)

        genre_objs = []
        if genres:
            stmt = select(Genre).where(Genre.id.in_(genres))
            res = await session.execute(stmt)
            genre_objs = list(res.scalars().all())

        anime = Anime(
            title=title,
            poster_id=poster_id,
            year=year,
            is_completed=is_completed,
            description=description,
            languages=languages,
            genres=genre_objs
        )

        session.add(anime)
        await session.flush() 
        
        # Ustunlarni dict qilamiz va munosabatlarni qo'lda xavfsiz qo'shamiz
        data = anime.to_dict()
        data["genres"] = [g.id for g in anime.genres] if hasattr(anime, "genres") else []
        data["episodes"] = []  # Yangi yaratilganda epizodlar bo'lmaydi
        
        return data

    # ================= ADD EPISODE =================
    @staticmethod
    async def add_episode(
        session: Any,
        anime_id: int,
        episode_num: int,
        file_id: str
    ) -> bool:
        session = await AnimeRepository._prepare_session(session)

        ep = Episode(
            anime_id=anime_id,
            episode=episode_num,
            file_id=file_id
        )

        session.add(ep)
        await session.flush()
        return True
    
    # ================= DELETE EPISODE =================
    @staticmethod
    async def delete_episode(session: Any, anime_id: int, episode_num: int) -> bool:
        from sqlalchemy import delete
        real_session = await AnimeRepository._prepare_session(session)

        stmt = delete(Episode).where(
            Episode.anime_id == anime_id,
            Episode.episode == episode_num
        )
        result = await real_session.execute(stmt)
        await real_session.flush()
        
        # Agar kamida 1 ta qator o'chirilgan bo'lsa True qaytadi
        return result.rowcount > 0

    # ================= DELETE =================
    @staticmethod
    async def delete(session: Any, anime_id: int) -> bool:
        real_session = await AnimeRepository._prepare_session(session)

        result = await real_session.execute(
            select(Anime).where(Anime.anime_id == anime_id)
        )
        anime = result.scalar_one_or_none()

        if not anime:
            return False

        await real_session.delete(anime)   # ✅ await qo'shing!
        await real_session.flush()
        return True
    
    # ================= UPDATE EPISODE FILE =================
    @staticmethod
    async def update_episode_file(session: Any, anime_id: int, episode_num: int, new_file_id: str) -> bool:
        from sqlalchemy import update
        real_session = await AnimeRepository._prepare_session(session)

        stmt = (
            update(Episode)
            .where(Episode.anime_id == anime_id, Episode.episode == episode_num)
            .values(file_id=new_file_id)
        )
        result = await real_session.execute(stmt)
        await real_session.flush()
        
        return result.rowcount > 0
    


    # ================= MULTI-GENRE SEARCH (OPTIMIZED) =================
    @staticmethod
    async def get_by_genres(session: Any, genre_ids: List[int]) -> List[Dict]:
        from database.models import anime_genres  # Many-to-Many o'rtadagi jadval
        from sqlalchemy import func

        session = await AnimeRepository._prepare_session(session)

        # SQL mantiqi: Tanlangan janrlar ichidan qidir, anime bo'yicha guruhla
        # va faqat guruhdagi janrlar soni biz yuborgan janrlar soniga teng bo'lganlarini ol!
        stmt = (
            select(Anime)
            .join(anime_genres)
            .where(anime_genres.c.genre_id.in_(genre_ids))
            .group_by(Anime.anime_id)
            .having(func.count(anime_genres.c.genre_id) == len(genre_ids))
            .options(selectinload(Anime.genres), selectinload(Anime.episodes))
            .order_by(desc(Anime.anime_id))
        )

        result = await session.execute(stmt)
        anime_list = []
        
        for anime in result.scalars().all():
            data = anime.to_dict()
            data["genres"] = [g.id for g in anime.genres] if hasattr(anime, "genres") else []
            data["episodes"] = [
                {"id": ep.id, "episode": ep.episode, "file_id": ep.file_id} 
                for ep in anime.episodes
            ] if hasattr(anime, "episodes") else []
            anime_list.append(data)
            
        return anime_list
    

    # ================= UNIVERSAL UPDATE ANIME =================
    @staticmethod
    async def update(session: Any, anime_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Bazadagi animening istalgan ustunlarini dinamik yangilash uchun universal metod.
        update_data format: {"title": "Yangi nom", "year": 2026}
        """
        session = await AnimeRepository._prepare_session(session)
        
        # 1. Animeni bazadan qidiramiz
        stmt = select(Anime).where(Anime.anime_id == anime_id)
        result = await session.execute(stmt)
        anime = result.scalar_one_or_none()
        
        if not anime:
            logger.warning(f"⚠️ Yangilash g'alati: Anime ID={anime_id} topilmadi.")
            return False
            
        # 2. Kelgan ma'lumotlarni setattr orqali dinamik ustunlarga yozamiz
        for key, value in update_data.items():
            if hasattr(anime, key):
                setattr(anime, key, value)
                logger.debug(f"✍️ Anime ID={anime_id}: {key} -> {value}")
                
        return True
    

    @staticmethod
    async def update_anime_genres(session: Any, anime_id: int, genre_ids: list[int]) -> bool:
        """Anime janrlarini Many-to-Many munosabati orqali xavfsiz yangilash"""
        from sqlalchemy.orm import selectinload
        session = await AnimeRepository._prepare_session(session)
        
        # Animeni janrlari bilan birga yuklaymiz
        stmt = select(Anime).where(Anime.anime_id == anime_id).options(selectinload(Anime.genres))
        result = await session.execute(stmt)
        anime = result.scalar_one_or_none()
        
        if not anime:
            return False
            
        if genre_ids:
            # Yangi janrlarni bazadan qidirib topamiz
            genre_stmt = select(Genre).where(Genre.id.in_(genre_ids))
            genre_result = await session.execute(genre_stmt)
            new_genres = genre_result.scalars().all()
            anime.genres = list(new_genres)
        else:
            anime.genres = [] # Agar hamma janr olib tashlansa
            
        return True