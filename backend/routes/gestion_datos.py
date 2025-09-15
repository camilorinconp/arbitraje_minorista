# backend/routes/gestion_datos.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

from ..services import database, scraper as scraper_service
from ..models.producto import Producto as ProductoModel
from ..models.minorista import Minorista as MinoristaModel
from ..models.historial_precio import HistorialPrecio as HistorialPrecioModel

router = APIRouter(
    prefix="/gestion-datos",
    tags=["Gestión de Datos"],
)

# --- Esquemas Pydantic ---

class MinoristaBase(BaseModel):
    nombre: str
    url_base: HttpUrl
    activo: Optional[bool] = True
    name_selector: Optional[str] = None
    price_selector: Optional[str] = None
    image_selector: Optional[str] = None

class Minorista(MinoristaBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ProductoBase(BaseModel):
    name: str
    price: float
    product_url: HttpUrl
    image_url: Optional[str] = None
    identificador_producto: Optional[str] = None

class Producto(ProductoBase):
    id: int
    last_scraped_at: datetime
    created_at: datetime
    id_minorista: int
    minorista: Optional[Minorista] # Relación con Minorista

    class Config:
        orm_mode = True

class HistorialPrecioSchema(BaseModel):
    id: int
    id_producto: int
    id_minorista: int
    precio: float
    fecha_registro: datetime

    class Config:
        orm_mode = True

class ScrapeRequest(BaseModel):
    product_url: HttpUrl
    id_minorista: int

# --- Endpoints para Minoristas ---

@router.post("/minoristas/", response_model=Minorista, status_code=status.HTTP_201_CREATED)
def crear_minorista(minorista: MinoristaBase, db: Session = Depends(database.get_db)):
    """
    Crea un nuevo minorista en la base de datos.
    """
    db_minorista = MinoristaModel(
        nombre=minorista.nombre, 
        url_base=str(minorista.url_base), 
        activo=minorista.activo,
        name_selector=minorista.name_selector,
        price_selector=minorista.price_selector,
        image_selector=minorista.image_selector
    )
    try:
        db.add(db_minorista)
        db.commit()
        db.refresh(db_minorista)
        return db_minorista
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un minorista con ese nombre o URL base.")

@router.get("/minoristas/", response_model=List[Minorista])
def listar_minoristas(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Obtiene una lista de todos los minoristas registrados.
    """
    minoristas = db.query(MinoristaModel).offset(skip).limit(limit).all()
    return minoristas

@router.get("/minoristas/{minorista_id}", response_model=Minorista)
def obtener_minorista(minorista_id: int, db: Session = Depends(database.get_db)):
    """
    Obtiene los detalles de un minorista específico por su ID.
    """
    minorista = db.query(MinoristaModel).filter(MinoristaModel.id == minorista_id).first()
    if minorista is None:
        raise HTTPException(status_code=404, detail="Minorista no encontrado.")
    return minorista

# --- Endpoints para Scraper ---

@router.post("/scrape/", response_model=Producto)
async def activar_scraper(request: ScrapeRequest, db: Session = Depends(database.get_db)):
    """
    Activa el scraper para una URL de producto específica de un minorista y guarda/actualiza los datos.
    """
    try:
        producto = await scraper_service.scrape_product_data(str(request.product_url), request.id_minorista, db)
        return producto
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud de scraping: {e}")

# --- Endpoints para Productos (actualizados para usar el nuevo modelo) ---

@router.get("/productos/", response_model=List[Producto])
def listar_productos(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Obtiene una lista de productos de la base de datos.
    """
    productos = db.query(ProductoModel).offset(skip).limit(limit).all()
    return productos

@router.get("/productos/{producto_id}", response_model=Producto)
def obtener_producto(producto_id: int, db: Session = Depends(database.get_db)):
    """
    Obtiene los detalles de un producto específico por su ID.
    """
    producto = db.query(ProductoModel).filter(ProductoModel.id == producto_id).first()
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return producto

@router.get("/productos/{producto_id}/historial-precios", response_model=List[HistorialPrecioSchema])
def obtener_historial_precios_producto(producto_id: int, db: Session = Depends(database.get_db)):
    """
    Obtiene el historial de precios de un producto específico.
    """
    historial = db.query(HistorialPrecioModel).filter(HistorialPrecioModel.id_producto == producto_id).order_by(HistorialPrecioModel.fecha_registro.desc()).all()
    return historial