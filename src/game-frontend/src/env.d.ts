/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_RUNNER_MODE?: 'live' | 'preview'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
