# backend/models/producto.py

from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..services.database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    url_producto = Column(String, nullable=False, unique=True)
    url_imagen = Column(String, nullable=True)
    ultima_fecha_rastreo = Column(DateTime(timezone=True), server_default=func.now())
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Nuevas columnas
    id_minorista = Column(BigInteger, ForeignKey("minoristas.id"), nullable=True) # Será NOT NULL una vez que tengamos minoristas
    identificador_producto = Column(String, nullable=True, index=True)

    # Relaciones (se definirán completamente una vez que los otros modelos existan)
    minorista = relationship("Minorista", back_populates="productos")
    historial_precios = relationship("HistorialPrecio", back_populates="producto")