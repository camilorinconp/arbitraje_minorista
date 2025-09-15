# backend/models/producto.py

from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..services.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    product_url = Column(String, nullable=False, unique=True)
    image_url = Column(String, nullable=True)
    last_scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Nuevas columnas
    id_minorista = Column(
        BigInteger, ForeignKey("minoristas.id"), nullable=True
    )  # Será NOT NULL una vez que tengamos minoristas
    identificador_producto = Column(String, nullable=True, index=True)

    # Relaciones (se definirán completamente una vez que los otros modelos existan)
    minorista = relationship("Minorista", back_populates="productos")
    historial_precios = relationship("HistorialPrecio", back_populates="producto")
