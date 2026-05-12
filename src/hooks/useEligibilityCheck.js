import { useCallback, useState } from 'react'
import { ELIGIBILIDAD_URL } from '../config/leadWebhook'

const REQUEST_TIMEOUT_MS = 20000

const FALLBACK_BY_CODE = {
  upstream_timeout: 'El servicio tarda más de lo normal. Vuelve a intentarlo en unos minutos.',
  upstream_unreachable: 'Servicio temporalmente no disponible. Inténtalo en unos minutos.',
  upstream_error: 'El portal de Red.es no responde correctamente. Inténtalo más tarde.',
  session_unavailable: 'El servicio se está reiniciando. Inténtalo en unos minutos.',
  session_expired: 'El servicio se está reiniciando. Inténtalo en unos minutos.',
}

/**
 * Hook para consultar elegibilidad contra el backend Node.
 *
 * El Node hace de proxy hacia kd-service (FastAPI) que a su vez consulta
 * el portal de Red.es. La landing NUNCA habla directamente con el portal.
 *
 * Estados:
 *   idle    -> aun sin enviar
 *   loading -> peticion en curso
 *   success -> respuesta 200 (eligible true o false con info)
 *   error   -> error de red, validacion, o backend caido
 */
export function useEligibilityCheck() {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [errorCode, setErrorCode] = useState('')

  const reset = useCallback(() => {
    setStatus('idle')
    setResult(null)
    setErrorMessage('')
    setErrorCode('')
  }, [])

  const check = useCallback(async ({ nif, bono, categoria }) => {
    setStatus('loading')
    setResult(null)
    setErrorMessage('')
    setErrorCode('')

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    try {
      const res = await fetch(ELIGIBILIDAD_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          nif: String(nif ?? '').trim().toUpperCase(),
          bono: String(bono ?? '').trim(),
          categoria: String(categoria ?? '').trim(),
        }),
        signal: controller.signal,
      })

      const contentType = res.headers.get('content-type') || ''
      const body = contentType.includes('application/json')
        ? await res.json().catch(() => null)
        : null

      if (!res.ok) {
        const code = typeof body?.error === 'string' ? body.error : `http_${res.status}`
        const message =
          (typeof body?.message === 'string' && body.message) ||
          FALLBACK_BY_CODE[code] ||
          `El servidor respondió ${res.status}. Inténtalo de nuevo más tarde.`
        setStatus('error')
        setErrorCode(code)
        setErrorMessage(message)
        return null
      }

      setStatus('success')
      setResult(body)
      return body
    } catch (err) {
      const isAbort = err?.name === 'AbortError'
      setStatus('error')
      setErrorCode(isAbort ? 'timeout' : 'network_error')
      setErrorMessage(
        isAbort
          ? 'La consulta tardó demasiado. Vuelve a intentarlo en unos segundos.'
          : 'No se ha podido conectar. Comprueba tu conexión e inténtalo de nuevo.',
      )
      return null
    } finally {
      window.clearTimeout(timeoutId)
    }
  }, [])

  return { status, result, errorMessage, errorCode, check, reset }
}
