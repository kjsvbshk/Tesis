import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const decimalFormatter = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export const currencyFormatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatDecimal(value: number | undefined | null): string {
  const n = typeof value === 'number' && isFinite(value) ? value : 0
  return decimalFormatter.format(n)
}

export function formatCurrency(value: number | undefined | null): string {
  const n = typeof value === 'number' && isFinite(value) ? value : 0
  return currencyFormatter.format(n)
}

export function parseLocaleNumber(input: string): number {
  if (!input) return 0
  // Remove all non-digit separators except comma/point
  const cleaned = input.replace(/[^0-9,\.]/g, '')
  // If comma is used as decimal, normalize to dot (es locales)
  const normalized = cleaned.replace(/,(?=\d{1,2}$)/, '.').replace(/,/g, '')
  const n = parseFloat(normalized)
  return isNaN(n) ? 0 : n
}


