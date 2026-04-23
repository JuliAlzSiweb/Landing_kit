import './PortatilPromoSection.css'
import { getSiteVariant } from '../../utils/siteVariant'

export function PortatilPromoSection() {
  const variant = getSiteVariant()
  const isEs = variant === 'es'

  return (
    <section
      className="promo-strip"
      aria-label={
        isEs
          ? 'Incluimos un portátil gratis al consumir tu bono con nosotros'
          : 'Consume tu bono con nosotros: gestión, Verifactu, control horario y portátil incluidos'
      }
    >
      <div className={`promo-strip__inner ${isEs ? 'promo-strip__inner--es' : 'promo-strip__inner--com'}`}>
        <div className={`promo-strip__copy ${isEs ? 'promo-strip__copy--es' : 'promo-strip__copy--com'}`}>
          {isEs ? (
            <>
              <p className="promo-strip__paragraph promo-strip__paragraph--es-intro">
                Por consumir tu bono con nosotros te incluimos un
              </p>
              <p className="promo-strip__paragraph promo-strip__paragraph--es-highlight">
                portátil <strong>completamente gratis</strong>
              </p>
            </>
          ) : (
            <>
              <p className="promo-strip__paragraph">Consume tu bono con nosotros y llévate <strong> Verifactu y</strong></p>
              <p className="promo-strip__paragraph"><strong>control horario digital</strong> hasta 2027, además de un</p>
              <p className="promo-strip__paragraph"><strong>portátil incluido </strong> sin coste adicional</p>
            </>
          )}
        </div>
      </div> 
    </section>
  )
}
