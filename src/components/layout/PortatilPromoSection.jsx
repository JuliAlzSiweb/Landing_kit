import './PortatilPromoSection.css'

export function PortatilPromoSection() {
  return (
    <section
      className="promo-strip"
      aria-label="Incluimos un portátil gratis al consumir tu bono con nosotros"
    >
      <div className="promo-strip__inner">
        <div className="promo-strip__copy">
          <p className="promo-strip__paragraph">
            Por consumir tu bono con nosotros te incluimos un
          </p>
          <p className="promo-strip__paragraph promo-strip__paragraph--accent">
            portátil <strong>completamente gratis</strong>
          </p>
        </div>
      </div>
    </section>
  )
}
