# backend/routes/gestion_datos.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, HttpUrl, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime

from ..services import database
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
    discovery_url: Optional[HttpUrl] = None
    product_link_selector: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v):
        if not v or not v.strip():
            raise ValueError("El nombre del minorista no puede estar vacío")
        if len(v.strip()) < 2:
            raise ValueError("El nombre del minorista debe tener al menos 2 caracteres")
        return v.strip()

    @field_validator("url_base")
    @classmethod
    def validate_url_base(cls, v):
        if v and not str(v).startswith(("http://", "https://")):
            raise ValueError("La URL base debe comenzar con http:// o https://")
        return v

    @field_validator("discovery_url")
    @classmethod
    def validate_discovery_url(cls, v):
        if v and not str(v).startswith(("http://", "https://")):
            raise ValueError(
                "La URL de descubrimiento debe comenzar con http:// o https://"
            )
        return v

    @field_validator(
        "name_selector", "price_selector", "image_selector", "product_link_selector"
    )
    @classmethod
    def validate_selectors(cls, v):
        if v and not v.strip():
            return None  # Convertir strings vacíos a None
        if v and len(v.strip()) < 2:
            raise ValueError("Los selectores CSS deben tener al menos 2 caracteres")
        return v.strip() if v else None


class Minorista(MinoristaBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    minorista: Optional[Minorista]  # Relación con Minorista

    model_config = ConfigDict(from_attributes=True)


class HistorialPrecioSchema(BaseModel):
    id: int
    id_producto: int
    id_minorista: int
    precio: float
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Endpoints para Minoristas ---


@router.post(
    "/minoristas/", response_model=Minorista, status_code=status.HTTP_201_CREATED
)
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
        image_selector=minorista.image_selector,
    )
    try:
        db.add(db_minorista)
        db.commit()
        db.refresh(db_minorista)
        return db_minorista
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Ya existe un minorista con ese nombre o URL base."
        )


@router.get("/minoristas/", response_model=List[Minorista])
def listar_minoristas(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
    """
    Obtiene una lista de todos los minoristas registrados.
    """
    minoristas = db.query(MinoristaModel).offset(skip).limit(limit).all()
    return minoristas


@router.get("/minoristas/buscar", response_model=List[Minorista])
def buscar_minoristas(q: str, db: Session = Depends(database.get_db)):
    """
    Busca minoristas por un término de búsqueda en el nombre.
    Ideal para campos de autocompletado.
    """
    minoristas = (
        db.query(MinoristaModel)
        .filter(MinoristaModel.nombre.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    return minoristas


@router.get("/minoristas/{minorista_id}", response_model=Minorista)
def obtener_minorista(minorista_id: int, db: Session = Depends(database.get_db)):
    """
    Obtiene los detalles de un minorista específico por su ID.
    """
    minorista = (
        db.query(MinoristaModel).filter(MinoristaModel.id == minorista_id).first()
    )
    if minorista is None:
        raise HTTPException(status_code=404, detail="Minorista no encontrado.")
    return minorista


@router.put("/minoristas/{minorista_id}", response_model=Minorista)
def actualizar_minorista(
    minorista_id: int, minorista: MinoristaBase, db: Session = Depends(database.get_db)
):
    """
    Actualiza un minorista existente por su ID.
    """
    db_minorista = (
        db.query(MinoristaModel).filter(MinoristaModel.id == minorista_id).first()
    )
    if db_minorista is None:
        raise HTTPException(status_code=404, detail="Minorista no encontrado.")

    for key, value in minorista.dict(exclude_unset=True).items():
        setattr(db_minorista, key, value)

    db.add(db_minorista)
    db.commit()
    db.refresh(db_minorista)
    return db_minorista


@router.delete("/minoristas/{minorista_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_minorista(minorista_id: int, db: Session = Depends(database.get_db)):
    """
    Elimina un minorista por su ID.
    """
    db_minorista = (
        db.query(MinoristaModel).filter(MinoristaModel.id == minorista_id).first()
    )
    if db_minorista is None:
        raise HTTPException(status_code=404, detail="Minorista no encontrado.")

    db.delete(db_minorista)
    db.commit()
    return {"message": "Minorista eliminado exitosamente."}


# --- Endpoints para Productos (actualizados para usar el nuevo modelo) ---


@router.get("/productos/", response_model=List[Producto])
def listar_productos(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
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


@router.get(
    "/productos/{producto_id}/historial-precios",
    response_model=List[HistorialPrecioSchema],
)
def obtener_historial_precios_producto(
    producto_id: int, db: Session = Depends(database.get_db)
):
    """
    Obtiene el historial de precios de un producto específico.
    """
    historial = (
        db.query(HistorialPrecioModel)
        .filter(HistorialPrecioModel.id_producto == producto_id)
        .order_by(HistorialPrecioModel.fecha_registro.desc())
        .all()
    )
    return historial
