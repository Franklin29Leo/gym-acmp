import { useEffect, useState } from 'react'
import Consulta from './pages/Consulta.jsx'
import Boletas from './pages/Boletas.jsx'
import Importar from './pages/Importar.jsx'

const PAGINAS = [
  { id: 'consulta', titulo: 'Consultar vigencia', Comp: Consulta },
  { id: 'boletas', titulo: 'Boletas', Comp: Boletas },
  { id: 'importar', titulo: 'Carga masiva', Comp: Importar },
]

const desdeHash = () => {
  const h = window.location.hash.replace('#/', '')
  return PAGINAS.some((p) => p.id === h) ? h : 'consulta'
}

export default function App() {
  const [pagina, setPagina] = useState(desdeHash)

  useEffect(() => {
    const f = () => setPagina(desdeHash())
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])

  const { Comp } = PAGINAS.find((p) => p.id === pagina)

  return (
    <>
      <header className="topbar">
        <div className="topbar-in">
          <div className="marca">
            <img src="/favicon.svg" alt="" width="34" height="34" />
            <div>
              <strong>Gimnasio · Sauna</strong>
              <span>Intranet de membresías mensuales</span>
            </div>
          </div>
          <nav>
            {PAGINAS.map((p) => (
              <a key={p.id} href={`#/${p.id}`} className={p.id === pagina ? 'activo' : ''}>
                {p.titulo}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main className="contenido">
        <Comp />
      </main>
    </>
  )
}
