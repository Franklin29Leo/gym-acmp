from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from .vigencia import normalizar_dni


class BoletaIn(BaseModel):
    local: str = "GIMNASIO-SAUNA"
    tipo_comprobante: str = "Boleta de Venta."
    num_comprobante: str = Field(min_length=1, max_length=40)
    fecha: date
    cliente_nombre: str = Field(min_length=1, max_length=160)
    dni: str = Field(min_length=1, max_length=15)
    estado: str = "VIGENTE"
    cajero: str = ""
    item: str = Field(min_length=1, max_length=160)
    total: Decimal = Decimal(0)

    @field_validator("num_comprobante", "cliente_nombre", "item", "local", "tipo_comprobante", "cajero")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("cliente_nombre", "estado")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        return normalizar_dni(v)


class BoletaOut(BoletaIn):
    id: int
    fecha_fin: date
    estado_membresia: str
    dias_restantes: int


class ClienteConsulta(BaseModel):
    dni: str
    cliente_nombre: str
    estado_membresia: str  # VIGENTE / POR_VENCER / VENCIDO / ANULADO
    dias_restantes: int
    fecha_inicio: date
    fecha_fin: date
    item: str
    num_comprobante: str
    boletas: list[BoletaOut]


class ConsultaOut(BaseModel):
    fecha_referencia: date
    resultados: list[ClienteConsulta]


class ListaBoletas(BaseModel):
    total: int
    items: list[BoletaOut]


class ErrorFila(BaseModel):
    fila: int
    mensaje: str


class ResultadoImportacion(BaseModel):
    leidas: int
    insertadas: int
    actualizadas: int
    errores: list[ErrorFila]


class Resumen(BaseModel):
    fecha_referencia: date
    clientes_total: int
    clientes_vigentes: int
    clientes_por_vencer: int
    clientes_vencidos: int
    boletas_total: int
    recaudado_mes: Decimal
    proximos_vencimientos: list[ClienteConsulta]
