from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import importer
from .config import settings
from .db import Base, engine, get_db
from .models import Boleta
from .schemas import (
    BoletaIn, BoletaOut, ClienteConsulta, ConsultaOut, ErrorFila, ListaBoletas,
    ResultadoImportacion, Resumen,
)
from .vigencia import es_anulada, estado_membresia, fecha_fin, hoy, normalizar, normalizar_dni

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Intranet Gimnasio – Membresías mensuales", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- helpers ----------

def a_out(b: Boleta, ref: date) -> BoletaOut:
    est, dias = estado_membresia(b.fecha_fin, es_anulada(b.estado), ref)
    return BoletaOut(
        id=b.id, local=b.local, tipo_comprobante=b.tipo_comprobante,
        num_comprobante=b.num_comprobante, fecha=b.fecha, cliente_nombre=b.cliente_nombre,
        dni=b.dni, estado=b.estado, cajero=b.cajero, item=b.item, total=b.total,
        fecha_fin=b.fecha_fin, estado_membresia=est, dias_restantes=dias,
    )


def aplicar(b: Boleta, datos: BoletaIn) -> Boleta:
    for k, v in datos.model_dump().items():
        setattr(b, k, v)
    b.fecha_fin = fecha_fin(datos.fecha)
    b.nombre_norm = normalizar(datos.cliente_nombre)
    return b


def construir_cliente(boletas: list[Boleta], ref: date) -> ClienteConsulta:
    boletas = sorted(boletas, key=lambda b: (b.fecha, b.id), reverse=True)
    validas = [b for b in boletas if not es_anulada(b.estado)]
    # la que llega más lejos determina la vigencia del cliente
    clave = max(validas, key=lambda b: b.fecha_fin) if validas else boletas[0]
    est, dias = estado_membresia(clave.fecha_fin, not validas, ref)
    return ClienteConsulta(
        dni=clave.dni, cliente_nombre=clave.cliente_nombre, estado_membresia=est,
        dias_restantes=dias, fecha_inicio=clave.fecha, fecha_fin=clave.fecha_fin,
        item=clave.item, num_comprobante=clave.num_comprobante,
        boletas=[a_out(b, ref) for b in boletas],
    )


def filtro_busqueda(q: str):
    q = q.strip()
    if not q:
        return None
    if q.replace(" ", "").isdigit():
        return Boleta.dni.like("%" + q.replace(" ", "") + "%")
    tokens = normalizar(q).split()
    return and_(*[Boleta.nombre_norm.like(f"%{t}%") for t in tokens])


# ---------- API ----------

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"ok": True, "hoy": hoy()}


@app.get("/api/consulta", response_model=ConsultaOut)
def consulta(
    q: str = Query(..., min_length=2, description="DNI o nombre del cliente"),
    fecha: date | None = Query(None, description="Fecha de referencia (por defecto hoy)"),
    db: Session = Depends(get_db),
):
    ref = fecha or hoy()
    filtro = filtro_busqueda(q)
    if filtro is None:
        return ConsultaOut(fecha_referencia=ref, resultados=[])
    dnis = db.scalars(select(Boleta.dni).where(filtro).distinct().limit(50)).all()
    if not dnis:
        return ConsultaOut(fecha_referencia=ref, resultados=[])
    grupos: dict[str, list[Boleta]] = defaultdict(list)
    for b in db.scalars(select(Boleta).where(Boleta.dni.in_(dnis))):
        grupos[b.dni].append(b)
    resultados = [construir_cliente(bs, ref) for bs in grupos.values()]
    resultados.sort(key=lambda c: c.cliente_nombre)
    return ConsultaOut(fecha_referencia=ref, resultados=resultados)


@app.get("/api/resumen", response_model=Resumen)
def resumen(db: Session = Depends(get_db)):
    ref = hoy()
    no_anulada = ~func.upper(Boleta.estado).like("ANUL%")
    fines = db.execute(
        select(Boleta.dni, func.max(Boleta.fecha_fin)).where(no_anulada).group_by(Boleta.dni)
    ).all()
    conteo = defaultdict(int)
    por_vencer = []
    for dni, fin in fines:
        est, _ = estado_membresia(fin, False, ref)
        conteo[est] += 1
        if est == "POR_VENCER":
            por_vencer.append(dni)
    proximos = []
    if por_vencer:
        grupos: dict[str, list[Boleta]] = defaultdict(list)
        for b in db.scalars(select(Boleta).where(Boleta.dni.in_(por_vencer))):
            grupos[b.dni].append(b)
        proximos = sorted((construir_cliente(bs, ref) for bs in grupos.values()), key=lambda c: c.fecha_fin)
    inicio_mes = ref.replace(day=1)
    recaudado = db.scalar(
        select(func.coalesce(func.sum(Boleta.total), 0)).where(no_anulada, Boleta.fecha >= inicio_mes, Boleta.fecha <= ref)
    )
    return Resumen(
        fecha_referencia=ref,
        clientes_total=db.scalar(select(func.count(func.distinct(Boleta.dni)))) or 0,
        clientes_vigentes=conteo["VIGENTE"] + conteo["POR_VENCER"],
        clientes_por_vencer=conteo["POR_VENCER"],
        clientes_vencidos=conteo["VENCIDO"],
        boletas_total=db.scalar(select(func.count(Boleta.id))) or 0,
        recaudado_mes=Decimal(recaudado or 0),
        proximos_vencimientos=proximos,
    )


@app.get("/api/boletas", response_model=ListaBoletas)
def listar_boletas(
    q: str = "",
    vigencia: str = Query("", pattern="^(|vigente|por_vencer|vencido|anulado)$"),
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
):
    ref = hoy()
    conds = []
    if (f := filtro_busqueda(q)) is not None:
        conds.append(f)
    if desde:
        conds.append(Boleta.fecha >= desde)
    if hasta:
        conds.append(Boleta.fecha <= hasta)
    anulada = func.upper(Boleta.estado).like("ANUL%")
    limite = date.fromordinal(ref.toordinal() + settings.dias_por_vencer)
    if vigencia == "anulado":
        conds.append(anulada)
    elif vigencia:
        conds.append(~anulada)
        if vigencia == "vigente":
            conds.append(Boleta.fecha_fin >= ref)
        elif vigencia == "por_vencer":
            conds.append(and_(Boleta.fecha_fin >= ref, Boleta.fecha_fin <= limite))
        elif vigencia == "vencido":
            conds.append(Boleta.fecha_fin < ref)
    base = select(Boleta).where(*conds)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    filas = db.scalars(
        base.order_by(Boleta.fecha.desc(), Boleta.num_comprobante.desc())
        .offset((pagina - 1) * por_pagina).limit(por_pagina)
    ).all()
    return ListaBoletas(total=total or 0, items=[a_out(b, ref) for b in filas])


@app.post("/api/boletas", response_model=BoletaOut, status_code=201)
def crear_boleta(datos: BoletaIn, db: Session = Depends(get_db)):
    b = aplicar(Boleta(), datos)
    db.add(b)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Ya existe el comprobante {datos.num_comprobante}")
    db.refresh(b)
    return a_out(b, hoy())


@app.put("/api/boletas/{boleta_id}", response_model=BoletaOut)
def editar_boleta(boleta_id: int, datos: BoletaIn, db: Session = Depends(get_db)):
    b = db.get(Boleta, boleta_id)
    if not b:
        raise HTTPException(404, "Boleta no encontrada")
    aplicar(b, datos)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Ya existe el comprobante {datos.num_comprobante}")
    db.refresh(b)
    return a_out(b, hoy())


@app.delete("/api/boletas/{boleta_id}", status_code=204)
def eliminar_boleta(boleta_id: int, db: Session = Depends(get_db)):
    b = db.get(Boleta, boleta_id)
    if not b:
        raise HTTPException(404, "Boleta no encontrada")
    db.delete(b)
    db.commit()
    return Response(status_code=204)


@app.get("/api/catalogos")
def catalogos(db: Session = Depends(get_db)):
    def distintos(col):
        return [v for v in db.scalars(select(col).distinct().order_by(col)) if v]
    return {
        "locales": distintos(Boleta.local),
        "tipos": distintos(Boleta.tipo_comprobante),
        "cajeros": distintos(Boleta.cajero),
        "items": distintos(Boleta.item),
    }


@app.post("/api/importar", response_model=ResultadoImportacion)
async def importar(archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    contenido = await archivo.read()
    try:
        filas = importer.leer_filas(archivo.filename or "", contenido)
    except ValueError as e:
        raise HTTPException(400, str(e))

    errores: list[ErrorFila] = []
    validas: dict[str, BoletaIn] = {}  # si un comprobante se repite en el archivo, gana la última fila
    for n, f in filas:
        try:
            datos = BoletaIn(
                local=str(f.get("local") or "GIMNASIO-SAUNA"),
                tipo_comprobante=str(f.get("tipo_comprobante") or "Boleta de Venta."),
                num_comprobante=str(f.get("num_comprobante") or "").strip(),
                fecha=importer.parse_fecha(f.get("fecha")),
                cliente_nombre=str(f.get("cliente_nombre") or ""),
                dni=normalizar_dni(f.get("dni")),
                estado=str(f.get("estado") or "VIGENTE"),
                cajero=str(f.get("cajero") or ""),
                item=str(f.get("item") or ""),
                total=importer.parse_total(f.get("total")),
            )
            validas[datos.num_comprobante] = datos
        except ValidationError as e:
            campos = ", ".join(str(err["loc"][0]) for err in e.errors())
            errores.append(ErrorFila(fila=n, mensaje=f"datos incompletos o inválidos: {campos}"))
        except ValueError as e:
            errores.append(ErrorFila(fila=n, mensaje=str(e)))

    existentes = {
        b.num_comprobante: b
        for b in db.scalars(select(Boleta).where(Boleta.num_comprobante.in_(list(validas))))
    } if validas else {}
    insertadas = actualizadas = 0
    for num, datos in validas.items():
        if num in existentes:
            aplicar(existentes[num], datos)
            actualizadas += 1
        else:
            db.add(aplicar(Boleta(), datos))
            insertadas += 1
    db.commit()
    return ResultadoImportacion(
        leidas=len(filas), insertadas=insertadas, actualizadas=actualizadas, errores=errores
    )


@app.get("/api/plantilla.csv")
def plantilla():
    ejemplo = "GIMNASIO-SAUNA;Boleta de Venta.;BS22-00000001;02/01/2026;APELLIDOS NOMBRES;07123456;VIGENTE;NOMBRE CAJERO;GIMNASIO SOCIO MENSUAL;50"
    cuerpo = ";".join(importer.COLUMNAS_PLANTILLA) + "\r\n" + ejemplo + "\r\n"
    return Response(
        content="﻿" + cuerpo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="plantilla_boletas.csv"'},
    )


# ---------- frontend compilado (producción) ----------

DIST = Path(__file__).resolve().parents[2] / "front" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        archivo = DIST / ruta
        if ruta and archivo.is_file() and DIST in archivo.resolve().parents:
            return FileResponse(archivo)
        return FileResponse(DIST / "index.html")
