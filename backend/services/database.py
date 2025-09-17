from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ..core.config import settings

# --- Conexión a Supabase (Cliente genérico) ---
supabase_url = settings.supabase_url
supabase_key = settings.supabase_anon_key

# Solo validar Supabase en producción
if settings.is_production and (not supabase_url or not supabase_key):
    raise ValueError(
        "Las variables de entorno SUPABASE_URL y SUPABASE_ANON_KEY son necesarias en producción."
    )

# Only create Supabase client if configuration is provided
supabase_client: Client = None
if supabase_url and supabase_key:
    supabase_client = create_client(supabase_url, supabase_key)

# --- Conexión directa a la Base de Datos con SQLAlchemy ---
# URL de la base de datos desde configuración
database_url = settings.database_url_for_env

# Crear engine síncrono para compatibilidad
sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(sync_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Configuración Async para SQLAlchemy ---
# Configurar engine async con connection pooling optimizado
async_engine = create_async_engine(
    database_url,
    # Connection pool settings from config
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,     # Verificar conexiones antes de usar
    pool_recycle=settings.db_pool_recycle,
    # Performance settings
    echo=settings.debug,    # Loggear queries solo en debug
    future=True,            # Usar la nueva API de SQLAlchemy 2.0
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,         # Auto-flush antes de queries
    autocommit=False
)

Base = declarative_base()


# Función para obtener una sesión de base de datos (síncrona)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Función para obtener una sesión de base de datos async
async def get_async_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


# Alias for authentication middleware
async def get_db_session():
    async for session in get_async_db():
        yield session
