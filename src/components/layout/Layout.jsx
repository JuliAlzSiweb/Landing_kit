import { Header } from './Header'
import { MainSection } from './MainSection'
import { PatrociniosSection } from './PatrociniosSection'
import { PortatilPromoSection } from './PortatilPromoSection'
import { Footer } from './Footer'

export function Layout() {
  return (
    <>
      <Header />
      <main className="site-main">
        <MainSection />
        <PatrociniosSection />
        <PortatilPromoSection />
      </main>
      <Footer />
    </>
  )
}
