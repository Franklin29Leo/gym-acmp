import { useCallback, useEffect, useState } from 'react'
import { api, ETIQUETA, fmtFecha, fmtSoles } from '../api.js'

const hoyISO = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Lima' })

const ITEMS = ['GIMNASIO SOCIO MENSUAL', 'GIMNASIO MENSUAL INVITADO SOCIO', 'GIMNASIO MENSUAL PUBLICO EN GENERAL']
const LOCALES = ['GIMNASIO-SAUNA', 'GARITA-CHORRILLOS']

// en una boleta antigua el valor puede no estar en la lista: se agrega para no perderlo
const opciones = (lista, actual) => (actual && !lista.includes(actual) ? [...lista, actual] : lista)

const VACIA = {
  local: 'GIMNASIO-SAUNA',
  tipo_comprobante: 'Boleta de Venta.',
  num_comprobante: '',
  fecha: hoyISO(),
  cliente_nombre: '',
  dni: '',
  estado: 'VIGENTE',
  cajero: '',
  item: 'GIMNASIO SOCIO MENSUAL',
  total: 50,
}

function Formulario({ inicial, catalogos, onCerrar, onGuardado }) {
  const [f, setF] = useState(inicial)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    try {
      const datos = { ...f, total: Number(f.total || 0) }
      if (f.id) await api.editar(f.id, datos)
      else await api.crear(datos)
      onGuardado()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="modal-fondo" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <form className="modal card" onSubmit={guardar}>
        <h2>{f.id ? 'Editar boleta' : 'Nueva boleta'}</h2>
        <div className="grid-form">
          <label>N° comprobante*<input required value={f.num_comprobante} onChange={set('num_comprobante')} placeholder="BS22-00000300" /></label>
          <label>Fecha de pago*<input required type="date" value={f.fecha} onChange={set('fecha')} /></label>
          <label className="span2">Cliente (apellidos y nombres)*<input required value={f.cliente_nombre} onChange={set('cliente_nombre')} /></label>
          <label>DNI*<input required value={f.dni} onChange={set('dni')} inputMode="numeric" maxLength={15} /></label>
          <label>Total cobrado (S/)<input type="number" step="0.01" min="0" value={f.total} onChange={set('total')} /></label>
          <label className="span2">Item*
            <select required value={f.item} onChange={set('item')}>
              {opciones(ITEMS, f.item).map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Local*
            <select required value={f.local} onChange={set('local')}>
              {opciones(LOCALES, f.local).map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Cajero<input list="dl-cajeros" value={f.cajero} onChange={set('cajero')} /></label>
          {f.id && (
            <label>Estado del comprobante
              <select value={f.estado} onChange={set('estado')}>
                <option value="VIGENTE">VIGENTE</option>
                <option value="ANULADO">ANULADO</option>
              </select>
            </label>
          )}
        </div>
        <datalist id="dl-cajeros">{catalogos.cajeros?.map((v) => <option key={v} value={v} />)}</datalist>
        {error && <div className="alerta error">{error}</div>}
        <div className="acciones">
          <button type="button" className="btn sec" onClick={onCerrar}>Cancelar</button>
          <button className="btn" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar'}</button>
        </div>
      </form>
    </div>
  )
}

export default function Boletas() {
  const [filtros, setFiltros] = useState({ q: '', vigencia: '', desde: '', hasta: '' })
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState({ total: 0, items: [] })
  const [catalogos, setCatalogos] = useState({})
  const [editando, setEditando] = useState(null)
  const [error, setError] = useState('')
  const POR_PAGINA = 25

  const cargar = useCallback(() => {
    api
      .boletas({ ...filtros, pagina, por_pagina: POR_PAGINA })
      .then((d) => { setDatos(d); setError('') })
      .catch((e) => setError(e.message))
  }, [filtros, pagina])

  useEffect(() => {
    const t = setTimeout(cargar, 250)
    return () => clearTimeout(t)
  }, [cargar])

  useEffect(() => {
    api.catalogos().then(setCatalogos).catch(() => {})
  }, [])

  const setFiltro = (k) => (e) => {
    setFiltros({ ...filtros, [k]: e.target.value })
    setPagina(1)
  }

  const eliminar = async (b) => {
    if (!confirm(`¿Eliminar la boleta ${b.num_comprobante} de ${b.cliente_nombre}?`)) return
    try {
      await api.eliminar(b.id)
      cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  const paginas = Math.max(1, Math.ceil(datos.total / POR_PAGINA))

  return (
    <section>
      <div className="encabezado">
        <h1>Boletas registradas</h1>
        <button className="btn" onClick={() => setEditando({ ...VACIA, fecha: hoyISO() })}>+ Nueva boleta</button>
      </div>

      <div className="card filtros">
        <input placeholder="DNI o nombre" value={filtros.q} onChange={setFiltro('q')} />
        <select value={filtros.vigencia} onChange={setFiltro('vigencia')}>
          <option value="">Todas</option>
          <option value="vigente">Vigentes</option>
          <option value="por_vencer">Por vencer</option>
          <option value="vencido">Vencidas</option>
          <option value="anulado">Anuladas</option>
        </select>
        <label>Pagadas desde <input type="date" value={filtros.desde} onChange={setFiltro('desde')} /></label>
        <label>hasta <input type="date" value={filtros.hasta} onChange={setFiltro('hasta')} /></label>
      </div>

      {error && <div className="alerta error">{error}</div>}

      <div className="card tabla-wrap">
        <table className="tabla">
          <thead>
            <tr>
              <th>Comprobante</th><th>Pago</th><th>Válido hasta</th><th>Cliente</th><th>DNI</th>
              <th>Item</th><th className="num">Total</th><th>Membresía</th><th></th>
            </tr>
          </thead>
          <tbody>
            {datos.items.map((b) => (
              <tr key={b.id}>
                <td>{b.num_comprobante}</td>
                <td>{fmtFecha(b.fecha)}</td>
                <td>{fmtFecha(b.fecha_fin)}</td>
                <td>{b.cliente_nombre}</td>
                <td>{b.dni}</td>
                <td className="small">{b.item}</td>
                <td className="num">{fmtSoles(b.total)}</td>
                <td><span className={`badge b-${b.estado_membresia}`}>{ETIQUETA[b.estado_membresia]}</span></td>
                <td className="fila-acciones">
                  <button className="link" onClick={() => setEditando({ ...b })}>Editar</button>
                  <button className="link peligro" onClick={() => eliminar(b)}>Eliminar</button>
                </td>
              </tr>
            ))}
            {datos.items.length === 0 && (
              <tr><td colSpan={9} className="vacio">Sin resultados.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="paginacion">
        <span className="muted">{datos.total} boleta{datos.total === 1 ? '' : 's'}</span>
        <button className="btn sec" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>‹ Anterior</button>
        <span>Página {pagina} de {paginas}</span>
        <button className="btn sec" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>Siguiente ›</button>
      </div>

      {editando && (
        <Formulario
          inicial={editando}
          catalogos={catalogos}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            cargar()
            api.catalogos().then(setCatalogos).catch(() => {})
          }}
        />
      )}
    </section>
  )
}
