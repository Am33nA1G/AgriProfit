import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Polyfill pointer capture and scroll APIs for Radix UI components in JSDOM
Object.assign(window.HTMLElement.prototype, {
    hasPointerCapture: () => false,
    setPointerCapture: () => {},
    releasePointerCapture: () => {},
    scrollIntoView: () => {},
})

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

// Runs a cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
    cleanup()
})
