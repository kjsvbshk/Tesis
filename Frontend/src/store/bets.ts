import { create } from 'zustand'

export type BetType = 'home' | 'away' | 'over' | 'under'

export interface BetItem {
  id: string
  matchId: string
  eventLabel: string
  type: BetType
  odd: number
}

interface BetState {
  items: BetItem[]
  stake: number
  addBet: (bet: BetItem) => void
  removeBet: (id: string) => void
  clear: () => void
  setStake: (value: number) => void
}

export const useBetStore = create<BetState>((set) => ({
  items: [],
  stake: 0,
  addBet: (bet) => set((state) => {
    const exists = state.items.some((i) => i.id === bet.id)
    return exists ? state : { items: [...state.items, bet], stake: state.stake }
  }),
  removeBet: (id) => set((state) => ({ items: state.items.filter((i) => i.id !== id), stake: state.stake })),
  clear: () => set({ items: [], stake: 0 }),
  setStake: (value) => set({ stake: value }),
}))

export function computeParlayOdd(items: BetItem[]): number {
  if (items.length === 0) return 0
  return Number(items.reduce((acc, i) => acc * i.odd, 1).toFixed(3))
}

export function potentialPayout(stake: number, items: BetItem[]): number {
  const parlayOdd = computeParlayOdd(items)
  return Number((stake * parlayOdd).toFixed(2))
}


