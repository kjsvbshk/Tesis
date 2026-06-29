/**
 * App version — single source of truth from package.json via Vite define.
 * Import this instead of hardcoding version strings in components.
 */
declare const __APP_VERSION__: string

// Safe fallback in case the build constant is undefined (e.g., unit tests)
export const APP_VERSION: string =
  typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '2.4.0'
