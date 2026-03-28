import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
    // @ts-expect-error - Plugin type mismatch between vite versions
    plugins: [react()],
    test: {
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.ts'],
        globals: true,
        alias: {
            '@': path.resolve(__dirname, './src'),
            '@test': path.resolve(__dirname, './src/test'),
        },
    },
})
