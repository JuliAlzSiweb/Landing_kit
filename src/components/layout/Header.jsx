import './Header.css'

export function Header() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <a className="site-header__brand" href="#">
          Siweb
        </a>
        <div className="site-header__actions">
          <a className="site-header__btn site-header__btn--outline" href="tel:+34900000000">
            Llámanos
          </a>
          <a className="site-header__btn site-header__btn--primary" href="#">
            Quiero mi bono
          </a>
        </div>
      </div>
    </header>
  )
}
