# Intranet Gimnasio – Membresías mensuales

Registra las boletas del gimnasio (a mano o por carga masiva CSV/XLSX) y permite cotejar por **DNI o nombre** si la membresía mensual del cliente sigue vigente.

**Regla de vigencia:** un pago del `02/01/2026` cubre hasta el `02/02/2026` inclusive; el `03/02/2026` ya está vencido. Si el día no existe en el mes siguiente (pago el 31/01), vence el último día de ese mes (28/02).

- `back/` – FastAPI + SQLAlchemy 2 + PostgreSQL (psycopg 3)
- `front/` – Vite + React

## 1. Base de datos

```powershell
cd back
# edita .env y reemplaza TU_CLAVE por la contraseña del usuario postgres
.venv\Scripts\python crear_bd.py
```

`crear_bd.py` crea la base `gimnasio` (si no existe) y la tabla `boletas`.

Si no existe el entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## 2. Desarrollo

Dos terminales:

```powershell
# terminal 1 – API en http://localhost:8000 (docs en /docs)
cd back
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# terminal 2 – web en http://localhost:5173
cd front
npm install
npm run dev
```

Vite redirige `/api` al puerto 8000, así que no hace falta configurar CORS.

## 3. Producción en la intranet (un solo proceso)

```powershell
cd front; npm run build
cd ..\back
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI sirve `front/dist`, y los demás equipos de la red entran por `http://IP-DEL-SERVIDOR:8000`. Abre el puerto 8000 en el firewall de Windows.

## 4. Servidor Ubuntu con Docker

Ver **[DEPLOY.md](DEPLOY.md)** (`docker compose up -d --build`).

## Pantallas

| Pantalla | Qué hace |
|---|---|
| **Consultar vigencia** | Buscador por DNI (también parcial) o nombre (sin tildes, en cualquier orden). Muestra Vigente / Por vencer / Vencido, hasta qué fecha vale, los días que quedan y el historial. Se puede cotejar a otra fecha. Arriba están los indicadores y la lista de los que vencen pronto. |
| **Boletas** | Lista con filtros (texto, estado, rango de fechas), alta, edición y eliminación manual. |
| **Carga masiva** | Sube un `.csv` (con `,` o `;`, UTF-8 o ANSI) o un `.xlsx` con las columnas de `datos.xlsx`. Si un `NUM_COMPROBANTE` ya existe, se actualiza en vez de duplicarse. Indica las filas con error. |

## Reglas de negocio

- La vigencia del cliente la da la boleta **no anulada** que llega más lejos.
- `ESTADO` del comprobante = `ANULADO` (o cualquier valor que empiece por `ANUL`): esa boleta no da membresía.
- "Por vencer" = le quedan `DIAS_POR_VENCER` días o menos (5 por defecto, se cambia en `.env`).
- Un pago adelantado no se acumula: dos boletas seguidas no suman dos meses desde la primera, cada una cuenta desde su propia fecha.
- Los DNI con menos de 8 dígitos se completan con ceros (Excel suele quitarlos).
- La fecha de "hoy" se toma en la zona `America/Lima`.
