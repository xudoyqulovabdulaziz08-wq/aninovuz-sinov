import os
import asyncio
import logging
import orjson
from contextlib import suppress
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ================= YANGI ARXITEKTURA IMPORTLARI =================
from config import config
from database.connection import AsyncSessionLocal, engine, check_db
from database.events import attach_cache_listeners
from database.cache import cache_manager

# Workerlarni o'zingiz joylagan fayldan import qiling (masalan: workers.py)
from services.cache_worker import CacheInvalidationWorker
from services.outbox.worker import OutboxWorker 

# Middleware'lar (Oldingi qadamlarda to'g'irlangan fayllardan)
from middlewares.middlewere import DbSessionMiddleware
from middlewares.subscription import CheckSubscriptionMiddleware


from routers import main_router

logger = logging.getLogger("Main")
logging.basicConfig(level=logging.INFO)

# ================= GLOBAL STATE =================
background_tasks: set[asyncio.Task] = set()
valkey = cache_manager  # Eski kod bilan moslik uchun alias


# =========================================================
# 🧠 AI CACHE BRAIN v2 (HOOK LAYER)
# =========================================================
class AICacheBrain:
    """
    🔥 USER BEHAVIOR LEARNING + PREDICTIVE CACHE
    """
    def __init__(self):
        self.user_stats = {}
        self.hot_users = set()

    async def observe(self, user_id: int, action: str):
        stat = self.user_stats.setdefault(user_id, {
            "hits": 0,
            "miss": 0,
            "actions": []
        })

        stat["actions"].append(action)
        stat["hits"] += 1

        if stat["hits"] > 50:
            self.hot_users.add(user_id)

    def predict_warm(self, user_id: int) -> bool:
        return user_id in self.hot_users


ai_brain = AICacheBrain()


# =========================================================
# 🚀 WORKER BOOTSTRAP
# =========================================================
async def start_workers():
    """Fonda ishlovchi distributed workerlarni xavfsiz ishga tushirish"""
    outbox = OutboxWorker