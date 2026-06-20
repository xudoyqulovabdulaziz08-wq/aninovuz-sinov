import asyncio
import logging
from typing import Any, Optional, Dict, List

from sqlalchemy import select, update, delete, desc, not_  # not_ qo'shildi
from sqlalchemy.exc import IntegrityError

from database.models import Channel

logger = logging.getLogger("ChannelRepository")


class ChannelRepository:

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
        return ChannelRepository._get_real_session(session)

    # ================= SERIALIZER =================
    @staticmethod
    def _to_dict(channel: Channel) -> Dict[str, Any]:
        return channel.to_dict()

    # ================= CACHE INVALIDATION =================
    @staticmethod
    async def _invalidate_cache(channel_id: Optional[int] = None, valkey=None):
        """
        Cluster-wide cache invalidation
        """
        if not valkey:
            return

        try:
            await valkey.invalidate(table="channels", obj_id="all_list", broadcast=True)
            await valkey.invalidate(table="channels", obj_id="active_list", broadcast=True)

            if channel_id:
                await valkey.invalidate(
                    table="channels",
                    obj_id=str(channel_id),
                    broadcast=True
                )

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")

    # ================= GET ALL =================
    @staticmethod
    async def get_all(session: Any, valkey=None) -> List[Dict[str, Any]]:
        session = await ChannelRepository._prepare_session(session)

        # ---- cache ----
        if valkey:
            try:
                cached = await valkey.get(table="channels", obj_id="all_list")
                if cached is not None:
                    return cached
            except Exception:
                pass

        result = await session.execute(
            select(Channel).order_by(desc(Channel.id))
        )

        data = [ch.to_dict() for ch in result.scalars().all()]

        if valkey:
            try:
                await valkey.set(
                    table="channels",
                    obj_id="all_list",
                    data=data,
                    ttl=3600
                )
            except Exception as e:
                logger.error(f"Cache write error: {e}")

        return data

    # ================= GET ACTIVE =================
    @staticmethod
    async def get_active(session: Any, valkey=None) -> List[Dict[str, Any]]:
        session = await ChannelRepository._prepare_session(session)

        if valkey:
            try:
                cached = await valkey.get(table="channels", obj_id="active_list")
                if cached:
                    return cached
            except Exception:
                pass

        result = await session.execute(
            select(Channel)
            .where(Channel.is_active == True)
            .order_by(desc(Channel.id))
        )

        data = [ch.to_dict() for ch in result.scalars().all()]

        if valkey:
            try:
                await valkey.set(
                    table="channels",
                    obj_id="active_list",
                    data=data,
                    ttl=3600
                )
            except Exception as e:
                logger.error(f"Cache write error: {e}")

        return data

    # ================= GET BY ID =================
    @staticmethod
    async def get_by_id(session: Any, channel_id: int, valkey=None) -> Optional[Dict[str, Any]]:
        session = await ChannelRepository._prepare_session(session)

        obj_key = str(channel_id)

        # cache
        if valkey:
            try:
                cached = await valkey.get(table="channels", obj_id=obj_key)
                if cached:
                    return cached
            except Exception:
                pass

        result = await session.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        )

        channel = result.scalar_one_or_none()
        if not channel:
            return None

        data = channel.to_dict()

        if valkey:
            try:
                await valkey.set(
                    table="channels",
                    obj_id=obj_key,
                    data=data,
                    ttl=3600
                )
            except Exception:
                pass

        return data

    # ================= CREATE =================
    @staticmethod
    async def create(
        session: Any,
        channel_id: int,
        title: str,
        url: Optional[str] = None,
        valkey=None
    ) -> Dict[str, Any]:

        session = await ChannelRepository._prepare_session(session)

        try:
            channel = Channel(
                channel_id=channel_id,
                title=title,
                url=url,
                is_active=True
            )

            session.add(channel)
            await session.flush()

            data = channel.to_dict()

            if hasattr(session, "on_commit"):
                session.on_commit(
                    lambda cid=channel_id: asyncio.create_task(
                        ChannelRepository._invalidate_cache(cid, valkey)
                    )
                )
            else:
                await ChannelRepository._invalidate_cache(channel_id, valkey)

            return data

        except IntegrityError:
            raise ValueError("Channel already exists")

    # ================= TOGGLE =================
    @staticmethod
    async def toggle_status(session: Any, channel_id: int, valkey=None) -> bool:
        session = await ChannelRepository._prepare_session(session)

        result = await session.execute(
            update(Channel)
            .where(Channel.channel_id == channel_id)
            .values(is_active=not_(Channel.is_active))
        )

        if result.rowcount == 0:
            return False

        if hasattr(session, "on_commit"):
            def _commit(cid=channel_id):
                asyncio.create_task(
                    ChannelRepository._invalidate_cache(cid, valkey)
                )
            session.on_commit(_commit)
        else:
            await ChannelRepository._invalidate_cache(channel_id, valkey)

        return True  # <-- TUZATILDI: Endi ikkala holatda ham to'g'ri ishlaydi

    # ================= DELETE =================
    @staticmethod
    async def delete(session: Any, channel_id: int, valkey=None) -> bool:
        session = await ChannelRepository._prepare_session(session)

        result = await session.execute(
            delete(Channel).where(Channel.channel_id == channel_id)
        )

        if result.rowcount == 0:
            return False

        # <-- TUZATILDI: on_commit xavfsizligi bu yerga ham qo'shildi, ortiqcha flush olib tashlandi
        if hasattr(session, "on_commit"):
            def _commit(cid=channel_id):
                asyncio.create_task(
                    ChannelRepository._invalidate_cache(cid, valkey)
                )
            session.on_commit(_commit)
        else:
            await ChannelRepository._invalidate_cache(channel_id, valkey)

        return True