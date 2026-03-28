'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Phone, KeyRound, Sparkles, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';
import { authService } from '@/services/auth';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'sonner';
import AuthLayout from '@/components/auth/AuthLayout';

export default function LoginPage() {
    const router = useRouter();
    const setAuth = useAuthStore((state) => state.setAuth);

    // Form state
    const [step, setStep] = useState<'phone' | 'otp'>('phone');
    const [phoneNumber, setPhoneNumber] = useState('');
    const [otp, setOtp] = useState('');
    const [loading, setLoading] = useState(false);

    // Inline validation
    const [phoneError, setPhoneError] = useState('');
    const [otpError, setOtpError] = useState('');

    // Resend timer
    const [resendTimer, setResendTimer] = useState(0);

    // Phone validation
    const validatePhone = (value: string): boolean => {
        if (value.length === 0) {
            setPhoneError('');
            return false;
        }
        if (value.length < 10) {
            setPhoneError('');
            return false;
        }
        if (!/^[6-9]\d{9}$/.test(value)) {
            setPhoneError('Must start with 6-9 and be 10 digits');
            return false;
        }
        setPhoneError('');
        return true;
    };

    const phoneValid = /^[6-9]\d{9}$/.test(phoneNumber);

    // Resend countdown
    const startResendTimer = useCallback(() => {
        setResendTimer(60);
    }, []);

    useEffect(() => {
        if (resendTimer <= 0) return;
        const t = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
        return () => clearTimeout(t);
    }, [resendTimer]);

    // Request OTP
    const handleRequestOtp = async (e?: React.FormEvent) => {
        e?.preventDefault();

        if (!validatePhone(phoneNumber)) {
            if (phoneNumber.length !== 10) {
                setPhoneError('Please enter a valid 10-digit mobile number');
            }
            return;
        }

        setLoading(true);
        try {
            await authService.requestOtp(phoneNumber);
            toast.success('OTP sent to your phone!');
            setStep('otp');
            startResendTimer();
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to send OTP. Please try again.';
            setPhoneError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    };

    // Verify OTP
    const handleVerifyOtp = async (e: React.FormEvent) => {
        e.preventDefault();

        if (otp.length !== 6) {
            setOtpError('Please enter the 6-digit OTP');
            return;
        }
        if (!/^\d+$/.test(otp)) {
            setOtpError('OTP must contain only digits');
            return;
        }
        setOtpError('');

        setLoading(true);
        try {
            const response = await authService.verifyOtp(phoneNumber, otp);
            localStorage.setItem('token', response.access_token);

            if (response.is_new_user) {
                toast.success('Phone verified! Please complete your profile.');
                router.push(`/register?step=profile&token=${response.access_token}`);
                return;
            }

            const user = await authService.getCurrentUser();

            if (!user.is_profile_complete) {
                toast.info('Please complete your profile to continue.');
                router.push('/register?step=profile');
                return;
            }

            setAuth(user, response.access_token);
            toast.success('Login successful!');
            router.push('/dashboard');
        } catch (error: any) {
            if (error.response?.status === 403) {
                const message = error.response?.data?.detail || 'Your account has been banned. Please contact support.';
                toast.error(message, { duration: 6000 });
                setStep('phone');
                setOtp('');
                setPhoneNumber('');
                return;
            }
            const message = error.response?.data?.detail || 'Invalid OTP. Please try again.';
            setOtpError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout
            title="Welcome Back"
            subtitle="Sign in to manage your agricultural business"
        >
            {/* ── Phone Step ── */}
            {step === 'phone' && (
                <form onSubmit={handleRequestOtp} className="space-y-5 animate-auth-fade-in">
                    {/* Phone input */}
                    <div className="space-y-1.5">
                        <label htmlFor="phone" className="block text-sm font-semibold text-gray-700">
                            Mobile Number <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                            <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                            <div className="absolute left-10 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium select-none">+91</div>
                            <input
                                id="phone"
                                type="tel"
                                inputMode="numeric"
                                autoComplete="tel"
                                placeholder="9876543210"
                                value={phoneNumber}
                                onChange={(e) => {
                                    const v = e.target.value.replace(/\D/g, '').slice(0, 10);
                                    setPhoneNumber(v);
                                    if (phoneError) validatePhone(v);
                                }}
                                onBlur={() => phoneNumber.length > 0 && validatePhone(phoneNumber)}
                                maxLength={10}
                                aria-invalid={!!phoneError}
                                aria-describedby={phoneError ? 'phone-error' : 'phone-help'}
                                className={`
                                    w-full pl-[4.5rem] pr-4 py-3 rounded-xl border-2 text-base transition-all duration-200
                                    placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-0
                                    ${phoneError
                                        ? 'border-red-300 focus:border-red-500 focus:ring-red-200'
                                        : phoneValid
                                            ? 'border-green-300 focus:border-green-500 focus:ring-green-200'
                                            : 'border-gray-200 focus:border-green-500 focus:ring-green-200'
                                    }
                                `}
                            />
                            {phoneValid && !phoneError && (
                                <div className="absolute right-3.5 top-1/2 -translate-y-1/2 text-green-500">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                            )}
                        </div>
                        {phoneError ? (
                            <p id="phone-error" className="text-xs text-red-600 flex items-center gap-1" role="alert">
                                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
                                </svg>
                                {phoneError}
                            </p>
                        ) : (
                            <p id="phone-help" className="text-xs text-gray-400">We&apos;ll send you a one-time verification code</p>
                        )}
                    </div>

                    {/* Submit */}
                    <button
                        type="submit"
                        disabled={loading || phoneNumber.length < 10}
                        className="
                            w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl
                            bg-gradient-to-r from-green-600 to-green-700 text-white font-semibold
                            shadow-lg shadow-green-600/25
                            hover:from-green-700 hover:to-green-800 hover:shadow-xl hover:shadow-green-600/30
                            focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2
                            disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none
                            active:scale-[0.98] transition-all duration-200
                        "
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span>Sending OTP...</span>
                            </>
                        ) : (
                            <>
                                <span>Send OTP</span>
                                <ArrowRight className="w-5 h-5" />
                            </>
                        )}
                    </button>

                    {/* Divider */}
                    <div className="relative py-1">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200" />
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="px-3 bg-white text-gray-400">New to AgriProfit?</span>
                        </div>
                    </div>

                    {/* Register link */}
                    <Link
                        href="/register"
                        className="
                            block w-full text-center py-3 px-6 rounded-xl
                            border-2 border-green-200 text-green-700 font-semibold
                            hover:bg-green-50 hover:border-green-300
                            focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2
                            active:scale-[0.98] transition-all duration-200
                        "
                    >
                        Create Free Account
                    </Link>
                </form>
            )}

            {/* ── OTP Step ── */}
            {step === 'otp' && (
                <div className="space-y-5 animate-auth-slide-up">
                    {/* Success banner */}
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
                        <Sparkles className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="text-sm font-semibold text-green-800">OTP sent successfully!</p>
                            <p className="text-xs text-green-700 mt-0.5">
                                Enter the 6-digit code sent to <span className="font-medium">+91 {phoneNumber}</span>
                            </p>
                        </div>
                    </div>

                    <form onSubmit={handleVerifyOtp} className="space-y-5">
                        {/* OTP input */}
                        <div className="space-y-1.5">
                            <label htmlFor="otp" className="block text-sm font-semibold text-gray-700">
                                Verification Code <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                                <input
                                    id="otp"
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    placeholder="000000"
                                    value={otp}
                                    onChange={(e) => {
                                        const v = e.target.value.replace(/\D/g, '').slice(0, 6);
                                        setOtp(v);
                                        if (otpError) setOtpError('');
                                    }}
                                    maxLength={6}
                                    autoFocus
                                    aria-invalid={!!otpError}
                                    aria-describedby={otpError ? 'otp-error' : undefined}
                                    className={`
                                        w-full pl-11 pr-4 py-3 rounded-xl border-2 text-center text-xl tracking-[0.3em] font-semibold
                                        transition-all duration-200
                                        placeholder:text-gray-300 placeholder:tracking-[0.3em]
                                        focus:outline-none focus:ring-2 focus:ring-offset-0
                                        ${otpError
                                            ? 'border-red-300 focus:border-red-500 focus:ring-red-200'
                                            : 'border-gray-200 focus:border-green-500 focus:ring-green-200'
                                        }
                                    `}
                                />
                            </div>
                            {otpError && (
                                <p id="otp-error" className="text-xs text-red-600" role="alert">{otpError}</p>
                            )}
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading || otp.length < 6}
                            className="
                                w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl
                                bg-gradient-to-r from-green-600 to-green-700 text-white font-semibold
                                shadow-lg shadow-green-600/25
                                hover:from-green-700 hover:to-green-800 hover:shadow-xl hover:shadow-green-600/30
                                focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2
                                disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none
                                active:scale-[0.98] transition-all duration-200
                            "
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    <span>Verifying...</span>
                                </>
                            ) : (
                                <>
                                    <span>Verify &amp; Login</span>
                                    <ArrowRight className="w-5 h-5" />
                                </>
                            )}
                        </button>

                        {/* Resend / Change number */}
                        <div className="flex items-center justify-between text-sm">
                            <button
                                type="button"
                                onClick={() => {
                                    setStep('phone');
                                    setOtp('');
                                    setOtpError('');
                                }}
                                className="text-gray-500 hover:text-gray-700 transition-colors"
                            >
                                &larr; Change number
                            </button>
                            {resendTimer > 0 ? (
                                <span className="text-gray-400">
                                    Resend in <span className="font-semibold text-green-600">{resendTimer}s</span>
                                </span>
                            ) : (
                                <button
                                    type="button"
                                    onClick={() => handleRequestOtp()}
                                    disabled={loading}
                                    className="text-green-600 hover:text-green-700 font-semibold transition-colors disabled:opacity-50"
                                >
                                    Resend OTP
                                </button>
                            )}
                        </div>
                    </form>
                </div>
            )}

            {/* Security badge */}
            <div className="mt-7 pt-5 border-t border-gray-100 flex items-center justify-center gap-2 text-xs text-gray-400">
                <ShieldCheck className="w-4 h-4 text-green-500" />
                <span>Your data is encrypted and secure</span>
            </div>
        </AuthLayout>
    );
}
