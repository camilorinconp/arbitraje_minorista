# backend/models/minorista.py

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..services.database import Base


class Minorista(Base):
    __tablename__ = "minoristas"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    url_base = Column(String, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Nuevas columnas para selectores de scraper
    name_selector = Column(String, nullable=True)
    price_selector = Column(String, nullable=True)
    image_selector = Column(String, nullable=True)
    discovery_url = Column(String, nullable=True)
    product_link_selector = Column(String, nullable=True)

    # Relaciones
    productos = relationship("Producto", back_populates="minorista")
    historial_precios = relationship("HistorialPrecio", back_populates="minorista")
