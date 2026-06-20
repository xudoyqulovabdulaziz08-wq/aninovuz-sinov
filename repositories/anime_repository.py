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

        # Modeldagi metodga tayaniladi
        return anime.to_dict(include_relations=True)

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
        return [a.to_dict(include_relations=True) for a in result.scalars().all()]

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
        
        # Eslatma: Bu yerda endi anime.anime_id generate bo'lgan bo'ladi
        return anime.to_dict(include_relations=True)

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

    # ================= DELETE =================
    @staticmethod
    async def delete(session: Any, anime_id: int) -> bool:
        session = await AnimeRepository._prepare_session(session)

        result = await session.execute(
            select(Anime).where(Anime.anime_id == anime_id)
        )
        anime = result.scalar_one_or_none()

        if not anime:
            return False

        # TO'G'RI VARIANT: await olib tashlandi, chunki u xotiradagi stateni o'zgartiradi xolos.
        session.delete(anime) 
        await session.flush()  # Haqiqiy SQL DELETE so'rovi shu yerda DBga boradi.
        
        return True