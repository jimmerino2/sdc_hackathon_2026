const escape = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

/** Minimal inline markup for authored lesson text: **bold**, *italic* and `code`. */
export function inline(text: string): string {
  return escape(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

export function pretty(value: unknown): string {
  if (value === undefined) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}

export function statusClass(code: number | undefined) {
  if (!code) return 'status-err'
  if (code < 300) return 'status-2xx'
  if (code < 500) return 'status-4xx'
  return 'status-5xx'
}

export const STATUS_TEXT: Record<number, string> = {
  200: 'OK',
  201: 'Created',
  400: 'Bad Request',
  403: 'Forbidden',
  404: 'Not Found',
  405: 'Method Not Allowed',
  422: 'Unprocessable Entity',
  500: 'Internal Server Error',
}
