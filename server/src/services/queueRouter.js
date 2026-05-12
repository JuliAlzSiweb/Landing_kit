import { config } from '../config.js'

const WEEKDAYS = new Set(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])

const MORNING_START_MIN = 9 * 60
const MORNING_END_MIN = 16 * 60
const AFTERNOON_END_MIN = 18 * 60

function getBusinessParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: config.BUSINESS_TIMEZONE,
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date)
  const get = (type) => parts.find((p) => p.type === type)?.value ?? ''
  return {
    weekday: get('weekday'),
    hour: Number.parseInt(get('hour'), 10) || 0,
    minute: Number.parseInt(get('minute'), 10) || 0,
  }
}

export function selectQueueForNow(date = new Date()) {
  const { weekday, hour, minute } = getBusinessParts(date)
  const totalMin = hour * 60 + minute

  if (!WEEKDAYS.has(weekday)) {
    return { queueId: null, mode: 'closed_weekend', isOpen: false }
  }

  if (totalMin >= MORNING_START_MIN && totalMin < MORNING_END_MIN) {
    const queueId = config.VOIP_QUEUE_ID_MORNING || config.VOIP_QUEUE_ID || null
    return { queueId, mode: 'morning', isOpen: true }
  }

  if (totalMin >= MORNING_END_MIN && totalMin < AFTERNOON_END_MIN) {
    const queueId = config.VOIP_QUEUE_ID_AFTERNOON || config.VOIP_QUEUE_ID || null
    return { queueId, mode: 'afternoon', isOpen: true }
  }

  return { queueId: null, mode: 'closed_off_hours', isOpen: false }
}
