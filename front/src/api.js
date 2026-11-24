const BASE = import.meta.env.VITE_API_URL ?? ''

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, opts)
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    let msg = data?.detail ?? `Error ${res.status}`
    if (Array.isArray(msg)) msg = msg.map((e) => `${e.loc?.at(-1)}: ${e.msg}`).join(' · ')
    throw new Error(msg)
  }
  return data
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

const qs = (params) =>
  new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null)).toString()

export const api = {
  consulta: (q, fecha) => req(`/api/consulta?${qs({ q, fecha })}`),
  resumen: () => req('/api/resumen'),
  boletas: (params) => req(`/api/boletas?${qs(params)}`),
  crear: (b) => req('/api/boletas', json('POST', b)),
  editar: (id, b) => req(`/api/boletas/${id}`, json('PUT', b)),
  eliminar: (id) => req(`/api/boletas/${id}`, { method: 'DELETE' }),
  catalogos: () => req('/api/catalogos'),
  importar: (archivo) => {
    const fd = new FormData()
    fd.append('archivo', archivo)
    return req('/api/importar', { method: 'POST', body: fd })
  },
  plantillaUrl: BASE + '/api/plantilla.csv',
}

export const fmtFecha = (iso) => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

export const fmtSoles = (n) =>
  'S/ ' + Number(n ?? 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const ETIQUETA = {
  VIGENTE: 'Vigente',
  POR_VENCER: 'Por vencer',
  VENCIDO: 'Vencido',
  ANULADO: 'Anulado',
}

export function textoDias(estado, dias) {
  if (estado === 'ANULADO') return 'Comprobante anulado'
  if (dias < 0) return `Venció hace ${-dias} día${dias === -1 ? '' : 's'}`
  if (dias === 0) return 'Hoy es su último día'
  return `Le queda${dias === 1 ? '' : 'n'} ${dias} día${dias === 1 ? '' : 's'}`
}
