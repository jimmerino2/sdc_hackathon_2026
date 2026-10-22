// VITE_API_URL wins when set. Otherwise the dev server proxies /api to the backend (see vite.config.ts),
// and other builds fall back to a backend on this machine.
export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? '/api' : 'http://localhost:8000');
