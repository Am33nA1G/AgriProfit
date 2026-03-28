import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LoginPage from '../page'
import { authService } from '@/services/auth'
import { useRouter } from 'next/navigation'

// Mock dependencies
vi.mock('next/navigation', () => ({
    useRouter: vi.fn(),
}))

vi.mock('@/services/auth', () => ({
    authService: {
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        getCurrentUser: vi.fn(),
    },
}))

vi.mock('@/store/authStore', () => ({
    useAuthStore: vi.fn(() => vi.fn()),
}))

// Mock toast to avoid errors
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}))

describe('LoginPage', () => {
    const mockRouter = { push: vi.fn() }

    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(useRouter).mockReturnValue(mockRouter as any)
    })

    it('renders login form initially', () => {
        render(<LoginPage />)
        expect(screen.getByText('AgriProfit Login')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('9876543210')).toBeInTheDocument()
        expect(screen.getByText('Send OTP')).toBeInTheDocument()
    })

    it('validates phone number', async () => {
        render(<LoginPage />)
        const input = screen.getByPlaceholderText('9876543210')
        const button = screen.getByText('Send OTP')

        // Too short
        fireEvent.change(input, { target: { value: '123' } })
        fireEvent.click(button)
        // Validation handled by browser 'required' or toast? 
        // Logic says: if (phoneNumber.length !== 10) toast.error...
        // We can check if requestOtp was NOT called
        expect(authService.requestOtp).not.toHaveBeenCalled()

        // Invalid start char
        fireEvent.change(input, { target: { value: '1234567890' } })
        fireEvent.click(button)
        expect(authService.requestOtp).not.toHaveBeenCalled()
    })

    it('requests OTP successfully', async () => {
        render(<LoginPage />)
        const input = screen.getByPlaceholderText('9876543210')
        const button = screen.getByText('Send OTP')

        fireEvent.change(input, { target: { value: '9876543210' } })
        vi.mocked(authService.requestOtp).mockResolvedValue({ message: 'OTP sent', expires_in_seconds: 300 })

        fireEvent.click(button)

        await waitFor(() => {
            expect(authService.requestOtp).toHaveBeenCalledWith('9876543210')
        })

        // Should switch to OTP step
        expect(await screen.findByPlaceholderText('123456')).toBeInTheDocument()
    })

    it('verifies OTP and logs in', async () => {
        render(<LoginPage />)

        // Setup state to be in OTP step (simulate previous success)
        const inputPhone = screen.getByPlaceholderText('9876543210')
        fireEvent.change(inputPhone, { target: { value: '9876543210' } })
        vi.mocked(authService.requestOtp).mockResolvedValue({ message: 'OTP sent', expires_in_seconds: 300 })
        fireEvent.click(screen.getByText('Send OTP'))

        await waitFor(() => screen.getByPlaceholderText('123456'))

        const inputOtp = screen.getByPlaceholderText('123456')
        const verifyButton = screen.getByText('Verify OTP')

        fireEvent.change(inputOtp, { target: { value: '123456' } })

        vi.mocked(authService.verifyOtp).mockResolvedValue({
            access_token: 'fake-token',
            token_type: 'bearer',
            is_new_user: false
        })
        vi.mocked(authService.getCurrentUser).mockResolvedValue({
            id: '1',
            phone_number: '9876543210',
            role: 'farmer',
            name: 'Test User',
            is_profile_complete: true,
            created_at: '',
            updated_at: ''
        })

        fireEvent.click(verifyButton)

        await waitFor(() => {
            expect(authService.verifyOtp).toHaveBeenCalledWith('9876543210', '123456')
            expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
        })
    })
})
