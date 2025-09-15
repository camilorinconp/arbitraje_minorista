import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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
Base = declarative_base()


# Función para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
