const DEFAULT_MESSAGES = Object.freeze({
  network: 'Could not connect to the server.',
  timeout: 'The request timed out. Please try again.',
  unauthorized: 'Your session expired. Please log in again.',
  forbidden: 'You do not have permission to perform this action.',
  notFound: 'The requested resource was not found.',
  validation: 'Validation failed.',
  server: 'Server error while processing the request.',
})

const GENERIC_MESSAGES = new Set([
  'an unexpected error occurred.',
  'internal server error.',
  'request failed.',
  'validation failed.',
])

const normalizeMessage = (value) => {
  if (typeof value !== 'string') {
    return ''
  }
  return value.trim()
}

const collectMessages = (value, bucket = []) => {
  if (Array.isArray(value)) {
    value.forEach((item) => collectMessages(item, bucket))
    return bucket
  }

  if (value && typeof value === 'object') {
    Object.values(value).forEach((item) => collectMessages(item, bucket))
    return bucket
  }

  const normalized = normalizeMessage(value)
  if (normalized) {
    bucket.push(normalized)
  }
  return bucket
}

const findFirstMeaningfulMessage = (...candidates) => {
  for (const candidate of candidates) {
    const normalized = normalizeMessage(candidate)
    if (!normalized) {
      continue
    }
    if (!GENERIC_MESSAGES.has(normalized.toLowerCase())) {
      return normalized
    }
  }
  return normalizeMessage(candidates.find(Boolean))
}

const hasExpiredTokenError = (status, errors) => {
  if (status !== 401) {
    return false
  }

  const combinedMessages = collectMessages(errors).join(' ').toLowerCase()
  return ['token', 'expired', 'invalid', 'credentials'].some((fragment) => combinedMessages.includes(fragment))
}

const mapStatusToMessage = (status, overrides = {}) => {
  if (status === 401) return overrides.unauthorizedMessage || DEFAULT_MESSAGES.unauthorized
  if (status === 403) return overrides.forbiddenMessage || DEFAULT_MESSAGES.forbidden
  if (status === 404) return overrides.notFoundMessage || DEFAULT_MESSAGES.notFound
  if (status >= 500) return overrides.serverMessage || DEFAULT_MESSAGES.server
  return overrides.fallbackMessage || DEFAULT_MESSAGES.validation
}

export const extractApiError = (error, overrides = {}) => {
  const payload = error?.response?.data
  const status = error?.response?.status ?? null
  const requestId = payload?.request_id ?? null
  const errors = payload?.errors && typeof payload.errors === 'object' ? payload.errors : payload?.errors ?? null
  const flattenedMessages = collectMessages(errors)
  const timedOut = !error?.response && (error?.code === 'ECONNABORTED' || /timed?\s*out/i.test(String(error?.message || '')))

  if (!error?.response) {
    return {
      status,
      requestId,
      errors,
      message: timedOut ? overrides.timeoutMessage || DEFAULT_MESSAGES.timeout : overrides.networkMessage || DEFAULT_MESSAGES.network,
      fieldErrors: errors && typeof errors === 'object' && !Array.isArray(errors) ? errors : {},
      isNetworkError: true,
    }
  }

  const payloadMessage = normalizeMessage(payload?.message)
  const primaryFieldMessage = findFirstMeaningfulMessage(...flattenedMessages)

  let message = primaryFieldMessage
  if (!message) {
    message = findFirstMeaningfulMessage(payloadMessage, error?.message)
  }
  if (!message || GENERIC_MESSAGES.has(message.toLowerCase())) {
    message = mapStatusToMessage(status, overrides)
  }
  if (hasExpiredTokenError(status, errors)) {
    message = overrides.unauthorizedMessage || DEFAULT_MESSAGES.unauthorized
  }

  return {
    status,
    requestId,
    errors,
    message,
    fieldErrors: errors && typeof errors === 'object' && !Array.isArray(errors) ? errors : {},
    isNetworkError: false,
  }
}
