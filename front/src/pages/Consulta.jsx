import { useEffect, useRef, useState } from 'react'
import { api, ETIQUETA, fmtFecha, fmtSoles, textoDias } from '../api.js'

function Badge({ estado }) {
  return <span className={`badge b-${estado}`}>{ETIQUETA[estado] ?? estado}</span>
}

function TarjetaCliente({ c }) {
  const [abierto, setAbierto] = useState(false)
  return (
    <article className={`cliente c-${c.estado_membresia}`}>
      <div className="cliente-top">
        <div>
          <h3>{c.cliente_nombre}</h3>
          <p className="muted">DNI {c.dni}</p>
        </div>
        <Badge estado={c.estado_membresia} />
      </div>
      <div className="periodo">
        <div>
          <span>Pagó</span>
          <strong>{fmtFecha(c.fecha_inicio)}</strong>
        </div>
        <div className="flecha">→</div>
        <div>
          <span>Válido hasta</span>
          <strong>{fmtFecha(c.fecha_fin)}</strong>
        </div>
        <div className="dias">{textoDias(c.estado_membresia, c.dias_restantes)}</div>
      </div>
      <p className="muted small">
        {c.item} · {c.num_comprobante}
      </p>
      {c.boletas.length > 0 && (
        <button className="link" onClick={() => setAbierto(!abierto)}>
          {abierto ? 'Ocultar' : 'Ver'} historial ({c.boletas.length} boleta{c.boletas.length > 1 ? 's' : ''})
        </button>
      )}
      {abierto && (
        <table className="tabla mini">
          <thead>
            <tr>
              <th>Comprobante</th><th>Pago</th><th>Hasta</th><th>Item</th><th className="num">Total</th><th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {c.boletas.map((b) => (
              <tr key={b.id}>
                <td>{b.num_comprobante}</td>
                <td>{fmtFecha(b.fecha)}</td>
                <td>{fmtFecha(b.fecha_fin)}</td>
                <td>{b.item}</td>
                <td className="num">{fmtSoles(b.total)}</td>
                <td><Badge estado={b.estado_membresia} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  )
}

export default function Consulta() {
  const [q, setQ] = useState('')
  const [fecha, setFecha] = useState('')
  const [res, setRes] = useState(null)
  const [resumen, setResumen] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)
  const input = useRef(null)

  useEffect(() => {
    input.current?.focus()
    api.resumen().then(setResumen).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    const termino = q.trim()
    if (termino.length < 2) {
      setRes(null)
      return
    }
    setCargando(true)
    const t = setTimeout(() => {
      api
        .consulta(termino, fecha)
        .then((r) => { setRes(r); setError('') })
        .catch((e) => setError(e.message))
        .finally(() => setCargando(false))
    }, 300)
    return () => clearTimeout(t)
  }, [q, fecha])

  return (
    <section>
      {resumen && (
        <div className="kpis">
          <div className="kpi"><span>Socios vigentes</span><strong>{resumen.clientes_vigentes}</strong></div>
          <div className="kpi oro"><span>Por vencer</span><strong>{resumen.clientes_por_vencer}</strong></div>
          <div className="kpi rojo"><span>Vencidos</span><strong>{resumen.clientes_vencidos}</strong></div>
          <div className="kpi"><span>Recaudado este mes</span><strong>{fmtSoles(resumen.recaudado_mes)}</strong></div>
        </div>
      )}

      <div className="buscador card">
        <label htmlFor="q">Buscar cliente por DNI o nombre</label>
        <div className="buscador-fila">
          <input
            id="q"
            ref={input}
            className="grande"
            placeholder="Ej. 70699441 o PAICO EFFIO"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoComplete="off"
          />
          <div className="campo-fecha">
            <label htmlFor="f">Fecha de cotejo</label>
            <input id="f" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          </div>
        </div>
        <p className="muted small">
          Un pago del 02/01 cubre hasta el 02/02 inclusive; desde el 03/02 figura como vencido.
          {fecha ? ` Cotejando al ${fmtFecha(fecha)}.` : ' Cotejando a la fecha de hoy.'}
        </p>
      </div>

      {error && <div className="alerta error">{error}</div>}
      {cargando && <p className="muted">Buscando…</p>}

      {res && !cargando && (
        res.resultados.length === 0 ? (
          <div className="vacio card">No hay boletas registradas para “{q}”.</div>
        ) : (
          <div className="resultados">
            {res.resultados.map((c) => <TarjetaCliente key={c.dni} c={c} />)}
          </div>
        )
      )}

      {!res && resumen?.proximos_vencimientos?.length > 0 && (
        <div className="card">
          <h2>Vencen en los próximos días</h2>
          <table className="tabla">
            <thead>
              <tr><th>Cliente</th><th>DNI</th><th>Válido hasta</th><th>Días</th></tr>
            </thead>
            <tbody>
              {resumen.proximos_vencimientos.map((c) => (
                <tr key={c.dni} className="clic" onClick={() => setQ(c.dni)}>
                  <td>{c.cliente_nombre}</td>
                  <td>{c.dni}</td>
                  <td>{fmtFecha(c.fecha_fin)}</td>
                  <td>{textoDias(c.estado_membresia, c.dias_restantes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
