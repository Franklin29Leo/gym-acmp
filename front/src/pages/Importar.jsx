import { useRef, useState } from 'react'
import { api } from '../api.js'

export default function Importar() {
  const [archivo, setArchivo] = useState(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')
  const [subiendo, setSubiendo] = useState(false)
  const input = useRef(null)

  const elegir = (f) => {
    if (!f) return
    setArchivo(f)
    setRes(null)
    setError('')
  }

  const subir = async () => {
    setSubiendo(true)
    setError('')
    try {
      setRes(await api.importar(archivo))
    } catch (e) {
      setError(e.message)
    } finally {
      setSubiendo(false)
    }
  }

  return (
    <section>
      <div className="encabezado">
        <h1>Carga masiva de boletas</h1>
        <a className="btn sec" href={api.plantillaUrl}>Descargar plantilla CSV</a>
      </div>

      <div className="card">
        <p>
          Sube un archivo <strong>.csv</strong> (separado por coma o punto y coma) o <strong>.xlsx</strong> con
          las columnas del reporte de ventas: <code>LOCAL, TIPO_COMPROBANTE, NUM_COMPROBANTE, FECHA,
          CLIENTE_NOMBRE_COMPLETO, DNI_CLIENTE, ESTADO, CAJERO, ITEM, TOTAL_COBRADO</code>.
        </p>
        <p className="muted small">
          Obligatorias: NUM_COMPROBANTE, FECHA (DD/MM/AAAA), CLIENTE, DNI e ITEM. Si un comprobante ya existe se
          actualiza, así que puedes volver a subir el mismo reporte sin duplicar. Los DNI con menos de 8 dígitos
          se completan con ceros a la izquierda.
        </p>

        <div
          className={`zona ${arrastrando ? 'sobre' : ''}`}
          onClick={() => input.current.click()}
          onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => { e.preventDefault(); setArrastrando(false); elegir(e.dataTransfer.files[0]) }}
        >
          <input
            ref={input}
            type="file"
            accept=".csv,.txt,.xlsx"
            hidden
            onChange={(e) => { elegir(e.target.files[0]); e.target.value = '' }}
          />
          {archivo ? (
            <><strong>{archivo.name}</strong><span className="muted">{(archivo.size / 1024).toFixed(1)} KB · clic para cambiar</span></>
          ) : (
            <><strong>Arrastra el archivo aquí</strong><span className="muted">o haz clic para elegirlo</span></>
          )}
        </div>

        <div className="acciones">
          <button className="btn" disabled={!archivo || subiendo} onClick={subir}>
            {subiendo ? 'Importando…' : 'Importar'}
          </button>
        </div>
      </div>

      {error && <div className="alerta error">{error}</div>}

      {res && (
        <div className="card">
          <h2>Resultado</h2>
          <div className="kpis">
            <div className="kpi"><span>Filas leídas</span><strong>{res.leidas}</strong></div>
            <div className="kpi"><span>Nuevas</span><strong>{res.insertadas}</strong></div>
            <div className="kpi oro"><span>Actualizadas</span><strong>{res.actualizadas}</strong></div>
            <div className="kpi rojo"><span>Con error</span><strong>{res.errores.length}</strong></div>
          </div>
          {res.errores.length > 0 && (
            <table className="tabla">
              <thead><tr><th>Fila</th><th>Problema</th></tr></thead>
              <tbody>
                {res.errores.map((e) => (
                  <tr key={e.fila}><td>{e.fila}</td><td>{e.mensaje}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}
