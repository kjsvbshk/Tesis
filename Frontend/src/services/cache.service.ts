/**
 * Cache Service for Frontend
 * Simple in-memory cache to avoid repeated API calls during the same session
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number // Time to live in milliseconds
}

class CacheService {
  private cache: Map<string, CacheEntry<any>> = new Map()
  private defaultTTL = 5 * 60 * 1000 // 5 minutes in milliseconds

  /**
   * Generate a cache key from parameters
   */
  private generateKey(prefix: string, ...args: any[]): string {
    const keyData = JSON.stringify({ prefix, args })
    return `${prefix}:${this.hashCode(keyData)}`
  }

  /**
   * Simple hash function for strings
   */
  private hashCode(str: string): string {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = (hash << 5) - hash + char
      hash = hash & hash // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36)
  }

  /**
   * Get data from cache
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key)
    
    if (!entry) {
      return null
    }

    // Check if entry has expired
    const now = Date.now()
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key)
      return null
    }

    return entry.data as T
  }

  /**
   * Set data in cache
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL
    }
    this.cache.set(key, entry)
  }

  /**
   * Get or set data in cache
   * If data exists and is fresh, return it
   * Otherwise, call the fetch function and cache the result
   */
  async getOrSet<T>(
    key: string,
    fetchFn: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    const cached = this.get<T>(key)
    
    if (cached !== null) {
      return cached
    }

    // Fetch fresh data
    const data = await fetchFn()
    this.set(key, data, ttl)
    
    return data
  }

  /**
   * Delete a specific cache entry
   */
  delete(key: string): boolean {
    return this.cache.delete(key)
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear()
  }

  /**
   * Clear expired entries
   */
  cleanup(): number {
    const now = Date.now()
    let cleaned = 0

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key)
        cleaned++
      }
    }

    return cleaned
  }

  /**
   * Generate cache key for matches endpoints
   */
  matchesKey(type: 'today' | 'upcoming' | 'list' | 'by_id', params?: any): string {
    if (type === 'today') {
      return this.generateKey('matches', 'today')
    }
    if (type === 'upcoming') {
      return this.generateKey('matches', 'upcoming', params?.days || 7)
    }
    if (type === 'by_id') {
      return this.generateKey('matches', 'by_id', params?.matchId)
    }
    // list
    return this.generateKey('matches', 'list', params)
  }
}

export const cacheService = new CacheService()

// Cleanup expired entries every 5 minutes
if (typeof window !== 'undefined') {
  setInterval(() => {
    cacheService.cleanup()
  }, 5 * 60 * 1000) // Every 5 minutes
}

