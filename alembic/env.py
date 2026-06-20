import asyncio
import ssl
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# =========================================================================
# 1. MODELLARNI IMPORT QILISH (Alembic ko'rishi uchun majburiy)
# =========================================================================
from database.models import Base  # Sizning modelingiz joylashgan to'g'ri path

# Alembic Config obyekti
config = context.config

# Logging sozlamalari
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# =========================================================================
# 2. METADATA-NI ULYAMIZ (None o'rniga Base.metadata bo'lishi shart)
# =========================================================================
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Sinxron kontekst ichida migratsiyani bajarish uchun yordamchi funksiya"""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (Asinxron va Aiven SSL qo'llab-quvvatlaydi)."""
    
    url = config.get_main_option("sqlalchemy.url")
    
    # asyncpg uchun SSL konfiguratsiyasi
    connect_args = {}
    if url and "asyncpg" in url:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx  # Aiven Cloud self-signed sertifikati uchun

    # To'g'ridan-to'g'ri asinxron engine yaratamiz
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        # Asinxron ulanish ichida sinxron migratsiya funksiyasini ishga tushiramiz
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Asinxron funksiyani event loop orqali ishga tushirish
    asyncio.run(run_migrations_online())