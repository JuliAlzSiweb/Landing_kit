import './PatrociniosSection.css'

const patrociniosSrc = `/imagenes/${encodeURIComponent('2.Patrocinios.png')}`

export function PatrociniosSection() {
  return (
    <section className="patrocinios" aria-labelledby="patrocinios-heading">
      <div className="patrocinios__frame">
        <img
          className="patrocinios__img"
          src={patrociniosSrc}
          alt="Logos de patrocinadores y colaboradores"
          width={1200}
          height={200}
          loading="lazy"
          decoding="async"
        />
      </div>
    </section>
  )
}
