import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import messages from '../../messages/en.json'

// Mock Next.js navigation globally
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
        replace: vi.fn(),
        back: vi.fn(),
        forward: vi.fn(),
        refresh: vi.fn(),
        prefetch: vi.fn(),
    }),
    usePathname: () => '/test',
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
}))

// Helper: resolve a dotted key from a nested object
function resolve(obj: Record<string, unknown>, key: string): string {
    const parts = key.split('.')
    let cur: unknown = obj
    for (const p of parts) {
        if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
            cur = (cur as Record<string, unknown>)[p]
        } else {
            return key // key not found → return raw key
        }
    }
    return typeof cur === 'string' ? cur : key
}

// Build stable translator functions per namespace (avoids infinite re-render
// loops when `t` appears in useEffect dependency arrays).
function buildTranslator(section: Record<string, unknown>) {
    const t = (key: string, params?: Record<string, unknown>) => {
        let value = resolve(section, key)
        if (params && typeof value === 'string') {
            Object.entries(params).forEach(([k, v]) => {
                value = (value as string).replace(`{${k}}`, String(v))
            })
        }
        return value
    }
    t.rich = (key: string) => resolve(section, key)
    t.raw = (key: string) => resolve(section, key)
    t.markup = (key: string) => resolve(section, key)
    t.has = (key: string) => {
        const parts = key.split('.')
        let cur: unknown = section
        for (const p of parts) {
            if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
                cur = (cur as Record<string, unknown>)[p]
            } else {
                return false
            }
        }
        return true
    }
    return t
}

const translatorCache = new Map<string, ReturnType<typeof buildTranslator>>()

function getTranslator(namespace?: string): ReturnType<typeof buildTranslator> {
    const cacheKey = namespace ?? '__root__'
    let t = translatorCache.get(cacheKey)
    if (!t) {
        const section: Record<string, unknown> =
            namespace ? ((messages as Record<string, unknown>)[namespace] as Record<string, unknown>) ?? {} : messages
        t = buildTranslator(section)
        translatorCache.set(cacheKey, t)
    }
    return t
}

const stableFormatter = {
    number: (v: number) => String(v),
    dateTime: (v: Date) => v.toISOString(),
    relativeTime: (v: Date) => v.toISOString(),
}

// Mock next-intl globally - returns actual English translations with stable refs
vi.mock('next-intl', () => ({
    useTranslations: (namespace?: string) => getTranslator(namespace),
    useLocale: () => 'en',
    useFormatter: () => stableFormatter,
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Runs a cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
    cleanup()
})
