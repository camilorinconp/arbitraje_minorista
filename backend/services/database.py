import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Conexión a Supabase (Cliente genérico) ---
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError(
        "Las variables de entorno SUPABASE_URL y SUPABASE_KEY son necesarias."
    )

supabase_client: Client = create_client(supabase_url, supabase_key)

# --- Conexión directa a la Base de Datos con SQLAlchemy ---
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("La variable de entorno DATABASE_URL es necesaria.")

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Configuración Async para SQLAlchemy ---
# Convertir URL de PostgreSQL síncrona a asíncrona
async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

# Configurar engine async con connection pooling optimizado
async_engine = create_async_engine(
    async_database_url,
    # Connection pool settings
    pool_size=20,           # Número base de conexiones en el pool
    max_overflow=30,        # Conexiones adicionales cuando se necesite
    pool_pre_ping=True,     # Verificar conexiones antes de usar
    pool_recycle=3600,      # Reciclar conexiones cada hora
    # Performance settings
    echo=False,             # No loggear todas las queries SQL en producción
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
