"""Reglas de vigencia de la membresía mensual.

Un pago con fecha 02/01/2026 cubre hasta el 02/02/2026 inclusive;
el 03/02/2026 ya está vencido. Si el día no existe en el mes siguiente
(31/01) se usa el último día de ese mes (28/02 o 29/02).
"""

import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from .config import settings


def hoy() -> date:
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()


def fecha_fin(fecha_pago: date) -> date:
    return fecha_pago + relativedelta(months=1)


def es_anulada(estado_comprobante: str | None) -> bool:
    return (estado_comprobante or "").strip().upper().startswith("ANUL")


def estado_membresia(fin: date, anulada: bool, ref: date) -> tuple[str, int]:
    """Devuelve (estado, dias_restantes). dias_restantes = 0 el último día válido."""
    if anulada:
        return "ANULADO", 0
    dias = (fin - ref).days
    if dias < 0:
        return "VENCIDO", dias
    if dias <= settings.dias_por_vencer:
        return "POR_VENCER", dias
    return "VIGENTE", dias


def normalizar(texto: str | None) -> str:
    """Mayúsculas, sin tildes, Ñ->N y el carácter dañado '�' (suele ser Ñ) -> N."""
    t = (texto or "").replace("�", "N").upper()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split())


def normalizar_dni(dni) -> str:
    s = str(dni or "").strip()
    if s.endswith(".0"):  # números leídos desde Excel
        s = s[:-2]
    s = s.replace(" ", "")
    if s.isdigit() and len(s) < 8:  # Excel suele comerse los ceros a la izquierda
        s = s.zfill(8)
    return s
