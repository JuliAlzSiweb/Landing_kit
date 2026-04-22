import './PortatilPromoSection.css'

export function PortatilPromoSection() {
  return (
    <section
      className="promo-strip"
      aria-label="Incluimos un portátil gratis al consumir tu bono con nosotros"
    >
      <div className="promo-strip__inner">
        <div className="promo-strip__copy">
          <p className="promo-strip__paragraph">Consume tu bono con nosotros y te regalamos a</p>
          <p className="promo-strip__paragraph">gestión de clientes y facturación electrónica con</p>
          <p className="promo-strip__paragraph">Verifactu, control horario y portátil incluidos</p>
        </div>
      </div>
    </section>
  )
}
