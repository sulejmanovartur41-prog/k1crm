// Источник истины о роли пользователя — JWT, а не localStorage.
// localStorage.role оставлен только как кеш для UI, но НИКОГДА не используется
// для решений о доступе: всегда декодируем токен.

interface JwtPayload {
  sub?: string
  role?: string
  exp?: number
}

function decodeJwt(token: string): JwtPayload | null {
  try {
    const part = token.split('.')[1]
    if (!part) return null
    // base64url -> base64
    const b64 = part.replace(/-/g, '+').replace(/_/g, '/').padEnd(part.length + (4 - part.length % 4) % 4, '=')
    return JSON.parse(atob(b64))
  } catch {
    return null
  }
}

export function getRole(): string {
  const token = localStorage.getItem('token')
  if (!token) return ''
  const p = decodeJwt(token)
  if (!p) return ''
  if (p.exp && p.exp * 1000 < Date.now()) return ''
  return p.role ?? ''
}

export function getName(): string {
  return localStorage.getItem('name') ?? ''
}

export function isAuthenticated(): boolean {
  return getRole() !== ''
}

export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.removeItem('name')
}
