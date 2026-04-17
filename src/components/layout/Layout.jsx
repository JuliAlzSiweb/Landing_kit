import { Header } from './Header'
import { MainSection } from './MainSection'
import { PatrociniosSection } from './PatrociniosSection'
import { PortatilPromoSection } from './PortatilPromoSection'
import { FeaturesSection } from './FeaturesSection'
import { KitDigitalSection } from './KitDigitalSection'
import { KitSolutionsSection } from './KitSolutionsSection'
import { EligeEquipoSection } from './EligeEquipoSection'
import { StepsSection } from './StepsSection'
import { Footer } from './Footer'

export function Layout() {
  return (
    <>
      <Header />
      <main className="site-main">
        <MainSection />
        <PatrociniosSection />
        <PortatilPromoSection />
        <FeaturesSection />
        <KitDigitalSection />
        <StepsSection />
        <KitSolutionsSection />
        <EligeEquipoSection />
      </main>
      <Footer />
    </>
  )
}
