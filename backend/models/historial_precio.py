# backend/models/historial_precio.py

from sqlalchemy import Column, Integer, BigInteger, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..services.database import Base


class HistorialPrecio(Base):
    __tablename__ = "historial_precios"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_producto = Column(Integer, ForeignKey("productos.id"), nullable=False)
    id_minorista = Column(Integer, ForeignKey("minoristas.id"), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    producto = relationship("Producto", back_populates="historial_precios")
    minorista = relationship("Minorista", back_populates="historial_precios")
