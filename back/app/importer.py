"""Lectura de CSV / XLSX con las mismas columnas que datos.xlsx."""

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook

from .vigencia import normalizar

# columna canónica -> encabezados aceptados (ya normalizados, sin espacios ni _)
ALIAS = {
    "local": ["LOCAL", "SEDE"],
    "tipo_comprobante": ["TIPOCOMPROBANTE", "TIPO"],
    "num_comprobante": ["NUMCOMPROBANTE", "NUMEROCOMPROBANTE", "COMPROBANTE", "NBOLETA", "BOLETA"],
    "fecha": ["FECHA", "FECHAPAGO", "FECHAEMISION"],
    "cliente_nombre": ["CLIENTENOMBRECOMPLETO", "CLIENTE", "NOMBRE", "NOMBRECOMPLETO", "NOMBRES"],
    "dni": ["DNICLIENTE", "DNI", "DOCUMENTO", "NRODOCUMENTO"],
    "estado": ["ESTADO", "ESTADOCOMPROBANTE"],
    "cajero": ["CAJERO"],
    "item": ["ITEM", "PRODUCTO", "CONCEPTO"],
    "total": ["TOTALCOBRADO", "TOTAL", "MONTO", "IMPORTE"],
}
OBLIGATORIAS = ["num_comprobante", "fecha", "cliente_nombre", "dni", "item"]
COLUMNAS_PLANTILLA = [
    "LOCAL", "TIPO_COMPROBANTE", "NUM_COMPROBANTE", "FECHA", "CLIENTE_NOMBRE_COMPLETO",
    "DNI_CLIENTE", "ESTADO", "CAJERO", "ITEM", "TOTAL_COBRADO",
]


def _clave_encabezado(h) -> str:
    return "".join(ch for ch in normalizar(str(h or "")) if ch.isalnum())


def mapear_encabezados(encabezados: list) -> dict[int, str]:
    inverso = {alias: campo for campo, lista in ALIAS.items() for alias in lista}
    mapa: dict[int, str] = {}
    for i, h in enumerate(encabezados):
        campo = inverso.get(_clave_encabezado(h))
        if campo and campo not in mapa.values():
            mapa[i] = campo
    faltan = [c for c in OBLIGATORIAS if c not in mapa.values()]
    if faltan:
        raise ValueError(
            "Faltan columnas obligatorias: " + ", ".join(faltan)
            + ". Descarga la plantilla para ver los encabezados esperados."
        )
    return mapa


def parse_fecha(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip().split(" ")[0].split("T")[0]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"fecha inválida '{v}' (usa DD/MM/AAAA)")


def parse_total(v) -> Decimal:
    if v is None or str(v).strip() == "":
        return Decimal(0)
    s = str(v).strip().replace("S/", "").replace(" ", "")
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    s = s.replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"total inválido '{v}'")


def _decodificar(contenido: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return contenido.decode(enc)
        except UnicodeDecodeError:
            continue
    return contenido.decode("latin-1")


def leer_filas(nombre_archivo: str, contenido: bytes) -> list[tuple[int, dict]]:
    """Devuelve [(numero_fila_en_archivo, {campo: valor})]."""
    nombre = nombre_archivo.lower()
    if nombre.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        filas = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    elif nombre.endswith((".csv", ".txt")):
        texto = _decodificar(contenido)
        try:
            dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
        filas = list(csv.reader(io.StringIO(texto), dialecto))
    else:
        raise ValueError("Formato no soportado: sube un archivo .csv o .xlsx")

    if not filas:
        raise ValueError("El archivo está vacío")
    mapa = mapear_encabezados(filas[0])
    salida = []
    for n, fila in enumerate(filas[1:], start=2):
        if not any(str(c or "").strip() for c in fila):
            continue
        salida.append((n, {campo: fila[i] if i < len(fila) else None for i, campo in mapa.items()}))
    return salida
