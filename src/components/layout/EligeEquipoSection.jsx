import './EligeEquipoSection.css'

const imageSrc = `/imagenes/${encodeURIComponent('lapcolour.png')}`

const equipos = [
  'Ryzen 5, 16GB de RAM, 512GB SSD',
  'Lenovo ThinkPad E16 16”',
  'Lenovo M75q + pantalla 23.8”',
  'Apple MacBook NEO',
]

function ListIcon() {
  return (
    <svg className="elige-equipo__bullet-icon" width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <circle cx="11" cy="11" r="10" fill="rgba(45, 156, 219, 0.14)" stroke="#2d9cdb" strokeWidth="1.2" />
      <circle cx="11" cy="11" r="4.5" stroke="#2d9cdb" strokeWidth="0.9" fill="none" opacity="0.85" />
      <path d="M11 1.5v19M2 11h18" stroke="#2d9cdb" strokeWidth="0.85" strokeLinecap="round" opacity="0.65" />
      <path
        d="M4.5 6.5c3 1.2 10 1.2 13 0M4.5 15.5c3-1.2 10-1.2 13 0"
        stroke="#2d9cdb"
        strokeWidth="0.75"
        fill="none"
        opacity="0.55"
      />
    </svg>
  )
}

export function EligeEquipoSection() {
  return (
    <section className="elige-equipo" aria-labelledby="elige-equipo-heading">
      <div className="elige-equipo__inner">
        <div className="elige-equipo__grid">
          <div className="elige-equipo__media">
            <img
              className="elige-equipo__img"
              src={imageSrc}
              alt="Variedad de portátiles disponibles para tu Kit Digital"
              width={720}
              height={480}
              loading="lazy"
              decoding="async"
            />
          </div>

          <div className="elige-equipo__content">
            <h2 id="elige-equipo-heading" className="elige-equipo__title">
              <span className="elige-equipo__title-dark">Elige tu </span>
              <span className="elige-equipo__title-accent">equipo</span>
            </h2>
            <p className="elige-equipo__lead">
              Disponemos de varias opciones para completar tu solución <strong>Kit Digital</strong>. Consulta el PDF
              descargable para ver modelos, características y condiciones.
            </p>
            <ul className="elige-equipo__list">
              {equipos.map((line) => (
                <li key={line} className="elige-equipo__list-item">
                  <span className="elige-equipo__list-icon-wrap">
                    <ListIcon />
                  </span>
                  <span className="elige-equipo__list-text">{line}</span>
                </li>
              ))}
            </ul>
            <a className="elige-equipo__btn" href="#">
              Descargar PDF
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
