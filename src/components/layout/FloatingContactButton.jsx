import { useEffect, useState } from 'react'
import { useContactModal } from '../../context/ContactModalContext'
import './FloatingContactButton.css'

const PILL_TEXT = '¿Te llamamos ahora?'
const PILL_DELAY_MS = 1000

export function FloatingContactButton() {
  const { openModal, isOpen } = useContactModal()
  const [isPillVisible, setIsPillVisible] = useState(false)

  useEffect(() => {
    if (isOpen) return undefined
    const id = window.setTimeout(() => setIsPillVisible(true), PILL_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [isOpen])

  const handleOpenModal = () => {
    openModal()
  }

  if (isOpen) return null

  return (
    <div className="floating-contact" aria-label="Abrir opciones de contacto">
      {isPillVisible && (
        <button
          type="button"
          className="floating-contact__pill"
          onClick={handleOpenModal}
        >
          <span className="floating-contact__pill-text">{PILL_TEXT}</span>
        </button>
      )}

      <button
        type="button"
        className="floating-contact__cta"
        onClick={handleOpenModal}
        aria-label="Te llamamos"
      >
        <span className="floating-contact__cta-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" focusable="false">
            <path
              d="M5.00659 6.93309C5.04956 5.7996 5.70084 4.77423 6.53785 3.93723C7.9308 2.54428 10.1532 2.73144 11.0376 4.31617L11.6866 5.4791C12.2723 6.52858 12.0372 7.90533 11.1147 8.8278M17.067 18.9934C18.2004 18.9505 19.2258 18.2992 20.0628 17.4622C21.4558 16.0692 21.2686 13.8468 19.6839 12.9624L18.5209 12.3134C17.4715 11.7277 16.0947 11.9628 15.1722 12.8853"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
            <path
              opacity="0.6"
              d="M5.00655 6.93311C4.93421 8.84124 5.41713 12.0817 8.6677 15.3323C11.9183 18.5829 15.1588 19.0658 17.0669 18.9935M15.1722 12.8853C15.1722 12.8853 14.0532 14.0042 12.0245 11.9755C9.99578 9.94676 11.1147 8.82782 11.1147 8.82782"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <span className="floating-contact__cta-text">Te llamamos</span>
      </button>
    </div>
  )
}
