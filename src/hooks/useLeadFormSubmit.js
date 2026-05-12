import { useCallback, useState } from 'react'
import { CALLBACK_SHEET_WEBHOOK_URL, LEAD_WEBHOOK_URL } from '../config/leadWebhook'

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms)),
  ])
}

function normalizePhone(value) {
  return String(value ?? '').replace(/\D/g, '')
}

function formatSlotMadrid(iso) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  const dateParts = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'Europe/Madrid',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).formatToParts(d)
  const timeParts = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'Europe/Madrid',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (parts, type) => parts.find((p) => p.type === type)?.value ?? ''
  const date = `${get(dateParts, 'day')}/${get(dateParts, 'month')}/${get(dateParts, 'year')}`
  const time = `${get(timeParts, 'hour')}:${get(timeParts, 'minute')}`
  return `${date} ${time}`
}

function toMadridIso(iso) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Madrid',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZoneName: 'longOffset',
  }).formatToParts(d)
  const get = (type) => parts.find((p) => p.type === type)?.value ?? ''
  const year = get('year')
  const month = get('month')
  const day = get('day')
  let hour = get('hour')
  if (hour === '24') hour = '00'
  const minute = get('minute')
  const second = get('second') || '00'
  const tzn = get('timeZoneName') || ''
  const offsetMatch = /GMT([+-]\d{2}:\d{2})/.exec(tzn)
  const offset = offsetMatch ? offsetMatch[1] : '+00:00'
  return `${year}-${month}-${day}T${hour}:${minute}:${second}${offset}`
}

async function getPublicIp() {
  if (typeof window === 'undefined') return ''
  try {
    const res = await withTimeout(fetch('https://api.ipify.org?format=json'), 1800)
    if (!res.ok) return ''
    const data = await res.json()
    return typeof data?.ip === 'string' ? data.ip : ''
  } catch {
    return ''
  }
}

function getClientMetadata(form) {
  if (typeof window === 'undefined') return {}
  const now = Date.now()
  const startedAtRaw = form?.dataset?.startedAt
  const startedAt = Number(startedAtRaw)
  const submitTimeMs = Number.isFinite(startedAt) && startedAt > 0 ? Math.max(0, now - startedAt) : null

  return {
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    userAgent: navigator.userAgent || '',
    screen: `${window.screen.width}x${window.screen.height}`,
    pagePath: `${window.location.pathname}${window.location.hash || ''}`,
    submitTimeMs,
  }
}

export function useLeadFormSubmit({ endpoint = LEAD_WEBHOOK_URL, mode = 'lead' } = {}) {
  const [status, setStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const submitForm = useCallback(async (form) => {
    if (!(form instanceof HTMLFormElement)) return

    setStatus('loading')
    setErrorMessage('')
    setSuccessMessage('')

    let payload = {}
    if (mode === 'callback') {
      const formData = new FormData(form)
      const name = String(formData.get('nombre') ?? '').trim()
      const phone = normalizePhone(formData.get('telefono'))
      const slotIso = String(formData.get('slot_iso') ?? '').trim()
      const slotLabel = String(formData.get('slot_label') ?? '').trim()
      if (!phone) {
        setStatus('error')
        setErrorMessage('Introduce tu número de teléfono.')
        return
      }
      const scheduledSlotTime = formatSlotMadrid(slotIso)
      const scheduledSlotIsoMadrid = toMadridIso(slotIso)
      payload = {
        phone,
        name: name || null,
        consent: true,
        scheduled_slot_iso: scheduledSlotIsoMadrid,
        scheduled_slot_label: slotLabel || null,
        scheduled_slot_time: scheduledSlotTime,
      }

      // Fire-and-forget: registrar el lead en el sheet vía Make antes del POST
      // a /click-to-call. No bloqueamos ni rompemos la llamada si Make falla.
      try {
        const now = new Date()
        const fechaParts = new Intl.DateTimeFormat('es-ES', {
          timeZone: 'Europe/Madrid',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
        }).formatToParts(now)
        const horaParts = new Intl.DateTimeFormat('es-ES', {
          timeZone: 'Europe/Madrid',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }).formatToParts(now)
        const get = (parts, type) => parts.find((p) => p.type === type)?.value ?? ''
        const fecha = `${get(fechaParts, 'day')}/${get(fechaParts, 'month')}/${get(fechaParts, 'year')}`
        const hora = `${get(horaParts, 'hour')}:${get(horaParts, 'minute')}`

        fetch(CALLBACK_SHEET_WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: name || null,
            telefono: phone,
            fecha,
            hora,
            horario_solicitado: slotLabel || null,
            horario_solicitado_iso: slotIso || null,
            horario_solicitado_local: scheduledSlotTime,
          }),
          keepalive: true,
        }).catch(() => {})
      } catch {
        // ignorar
      }
    } else {
      const data = Object.fromEntries(new FormData(form).entries())
      const [publicIp, clientMeta] = await Promise.all([getPublicIp(), Promise.resolve(getClientMetadata(form))])
      payload = {
        ...data,
        source: 'landing-kit',
        submittedAt: new Date().toISOString(),
        ip_public: publicIp,
        meta: {
          ...clientMeta,
          ipPublic: publicIp,
        },
      }
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      let body = null
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        body = await res.json().catch(() => null)
      } else {
        const text = await res.text().catch(() => '')
        body = text ? { message: text } : null
      }

      const backendMessage = typeof body?.message === 'string' ? body.message.trim() : ''

      if (!res.ok || (mode === 'callback' && body?.ok === false)) {
        const fallbackByCode = {
          invalid_phone: 'El número de teléfono no es válido.',
          consent_required: 'Debes aceptar el consentimiento para que te llamemos.',
          rate_limited: 'Demasiados intentos. Vuelve a intentarlo en unos minutos.',
          agent_unavailable: 'Nuestros agentes no están disponibles ahora. Inténtalo en unos minutos.',
          voip_error: 'Servicio temporalmente no disponible. Inténtalo en unos minutos.',
          config_error: 'Error de configuración del servicio. Inténtalo más tarde.',
        }
        const code = typeof body?.code === 'string' ? body.code : ''
        const message =
          backendMessage ||
          fallbackByCode[code] ||
          `El servidor respondió ${res.status}. Inténtelo de nuevo más tarde.`
        throw new Error(message)
      }

      if (mode === 'callback' && backendMessage) {
        setSuccessMessage(backendMessage)
      }
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setErrorMessage(
        err instanceof TypeError && err.message.includes('fetch')
          ? 'No se ha podido enviar. Compruebe su conexión e inténtelo de nuevo.'
          : err instanceof Error
            ? err.message
            : 'Ha ocurrido un error. Inténtelo de nuevo.',
      )
    }
  }, [endpoint, mode])

  const reset = useCallback(() => {
    setStatus('idle')
    setErrorMessage('')
    setSuccessMessage('')
  }, [])

  return { status, errorMessage, successMessage, submitForm, reset }
}
