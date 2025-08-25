/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_ENV: string
  // altre variabili env...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}