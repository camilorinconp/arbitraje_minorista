# backend/models/minorista.py

from sqlalchemy import Column, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..services.database import Base

class Minorista(Base):
    __tablename__ = "minoristas"

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    url_base = Column(String, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    productos = relationship("Producto", back_populates="minorista")
    historial_precios = relationship("HistorialPrecio", back_populates="minorista")
