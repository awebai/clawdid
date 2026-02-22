export function apiBaseUrl(): string {
  const v = import.meta.env.VITE_CLAWDID_API_BASE as string | undefined
  return v && v.length > 0 ? v : 'http://127.0.0.1:18111'
}

