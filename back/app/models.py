from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Boleta(Base):
    __tablename__ = "boletas"

    id: Mapped[int] = mapped_column(primary_key=True)
    local: Mapped[str] = mapped_column(String(80), default="GIMNASIO-SAUNA")
    tipo_comprobante: Mapped[str] = mapped_column(String(60), default="Boleta de Venta.")
    num_comprobante: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    fecha_fin: Mapped[date] = mapped_column(Date, index=True)
    cliente_nombre: Mapped[str] = mapped_column(String(160))
    nombre_norm: Mapped[str] = mapped_column(String(160), index=True)
    dni: Mapped[str] = mapped_column(String(15), index=True)
    estado: Mapped[str] = mapped_column(String(20), default="VIGENTE")
    cajero: Mapped[str] = mapped_column(String(120), default="")
    item: Mapped[str] = mapped_column(String(160))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_boletas_dni_fin", "dni", "fecha_fin"),)
