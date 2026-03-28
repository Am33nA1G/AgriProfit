'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
    Phone, KeyRound, Sparkles, Loader2, ArrowRight, ShieldCheck,
    User, MapPin, CheckCircle, Calendar, ChevronDown,
} from 'lucide-react';
import { authService } from '@/services/auth';
import { mandisService } from '@/services/mandis';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'sonner';
import AuthLayout from '@/components/auth/AuthLayout';

// Indian states list
const INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
    'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
    'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh',
    'Andaman and Nicobar Islands', 'Dadra and Nagar Haveli and Daman and Diu', 'Lakshadweep'
];

type RegistrationStep = 'phone' | 'otp' | 'profile';

const STEP_CONFIG = [
    { id: 'phone' as const, label: 'Phone', icon: Phone, num: 1 },
    { id: 'otp' as const, label: 'Verify', icon: KeyRound, num: 2 },
    { id: 'profile' as const, label: 'Profile', icon: User, num: 3 },
];

function StepIndicator({ currentStep }: { currentStep: RegistrationStep }) {
    const stepOrder: RegistrationStep[] = ['phone', 'otp', 'profile'];
    const currentIndex = stepOrder.indexOf(currentStep);

    return (
        <div className="flex items-center justify-between mb-8 px-2">
            {STEP_CONFIG.map((step, index) => {
                const Icon = step.icon;
                const isCompleted = index < currentIndex;
                const isCurrent = index === currentIndex;

                return (
                    <div key={step.id} className="flex items-center flex-1 last:flex-none">
                        <div className="flex flex-col items-center">
                            <div
                                className={`
                                    w-11 h-11 rounded-full flex items-center justify-center transition-all duration-300
                                    ${isCompleted
                                        ? 'bg-green-500 text-white shadow-md shadow-green-500/30 scale-95'
                                        : isCurrent
                                            ? 'bg-gradient-to-br from-green-600 to-green-700 text-white shadow-lg shadow-green-600/30 animate-auth-pulse-ring'
                                            : 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                                    }
                                `}
                            >
                                {isCompleted ? (
                                    <CheckCircle className="w-5 h-5" />
                                ) : (
                                    <Icon className="w-5 h-5" />
                                )}
                            </div>
                            <span className={`text-xs mt-1.5 font-medium transition-colors ${
                                isCurrent ? 'text-green-700' : isCompleted ? 'text-green-600' : 'text-gray-400'
                            }`}>
                                {step.label}
                            </span>
                        </div>
                        {index < STEP_CONFIG.length - 1 && (
                            <div className="flex-1 mx-3 mb-5">
                                <div className="h-1 rounded-full bg-gray-100 overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-500 ease-out ${
                                            index < currentIndex ? 'w-full bg-green-500' : 'w-0 bg-green-500'
                                        }`}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default function RegisterPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const setAuth = useAuthStore((state) => state.setAuth);

    // Check if we're coming from login with a new user
    const initialPhone = searchParams?.get('phone') || '';
    const initialStep = (searchParams?.get('step') as RegistrationStep) || 'phone';
    const token = searchParams?.get('token') || '';

    const [step, setStep] = useState<RegistrationStep>(initialStep);
    const [phoneNumber, setPhoneNumber] = useState(initialPhone);
    const [otp, setOtp] = useState('');
    const [loading, setLoading] = useState(false);

    // Inline validation
    const [phoneError, setPhoneError] = useState('');
    const [otpError, setOtpError] = useState('');
    const [nameError, setNameError] = useState('');
    const [ageError, setAgeError] = useState('');

    // Profile form state
    const [name, setName] = useState('');
    const [age, setAge] = useState('');
    const [selectedState, setSelectedState] = useState('');
    const [district, setDistrict] = useState('');
    const [districts, setDistricts] = useState<string[]>([]);
    const [loadingDistricts, setLoadingDistricts] = useState(false);

    // Resend timer
    const [resendTimer, setResendTimer] = useState(0);

    // Success animation
    const [showSuccess, setShowSuccess] = useState(false);

    // Phone validation
    const validatePhone = (value: string): boolean => {
        if (value.length === 0) { setPhoneError(''); return false; }
        if (value.length < 10) { setPhoneError(''); return false; }
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

    // Fetch districts when state changes
    useEffect(() => {
        if (selectedState) {
            setLoadingDistricts(true);
            setDistrict('');
            mandisService.getDistrictsByState(selectedState)
                .then(setDistricts)
                .catch(() => {
                    toast.error('Failed to load districts');
                    setDistricts([]);
                })
                .finally(() => setLoadingDistricts(false));
        } else {
            setDistricts([]);
            setDistrict('');
        }
    }, [selectedState]);

    // If we have a token from login, store it and go to profile step
    useEffect(() => {
        if (token && step !== 'profile') {
            localStorage.setItem('token', token);
            setStep('profile');
        }
    }, [token, step]);

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
                setStep('profile');
            } else {
                const user = await authService.getCurrentUser();
                if (user.is_profile_complete) {
                    setAuth(user, response.access_token);
                    toast.success('Welcome back!');
                    router.push('/dashboard');
                } else {
                    setStep('profile');
                }
            }
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Invalid OTP. Please try again.';
            setOtpError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    };

    // Complete profile
    const handleCompleteProfile = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate all fields
        let hasError = false;
        if (!name.trim()) { setNameError('Please enter your name'); hasError = true; }
        else { setNameError(''); }

        const ageNum = parseInt(age);
        if (isNaN(ageNum) || ageNum < 18 || ageNum > 120) { setAgeError('Enter a valid age (18-120)'); hasError = true; }
        else { setAgeError(''); }

        if (!selectedState) { toast.error('Please select your state'); hasError = true; }
        if (!district) { toast.error('Please select your district'); hasError = true; }

        if (hasError) return;

        setLoading(true);
        try {
            const user = await authService.completeProfile({
                name: name.trim(),
                age: ageNum,
                state: selectedState,
                district,
            });

            const storedToken = localStorage.getItem('token');
            setAuth(user, storedToken || '');

            // Show success animation
            setShowSuccess(true);
            toast.success('Registration complete! Welcome to AgriProfit!');
            setTimeout(() => router.push('/dashboard'), 1500);
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to save profile. Please try again.';
            toast.error(message);
        } finally {
            setLoading(false);
        }
    };

    const stepSubtitle = {
        phone: 'Enter your mobile number to get started',
        otp: 'Verify your phone number',
        profile: 'Tell us about yourself to personalize your experience',
    };

    // Success overlay
    if (showSuccess) {
        return (
            <AuthLayout title="Welcome!" subtitle="You're all set">
                <div className="flex flex-col items-center py-8 animate-auth-scale-in">
                    <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mb-5 animate-auth-bounce-in">
                        <CheckCircle className="w-10 h-10 text-green-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Registration Complete!</h3>
                    <p className="text-gray-500 text-sm text-center">
                        Welcome to AgriProfit, <span className="font-semibold text-green-700">{name}</span>!
                        <br />Redirecting to your dashboard...
                    </p>
                    <div className="mt-5">
                        <Loader2 className="w-5 h-5 animate-spin text-green-600" />
                    </div>
                </div>
            </AuthLayout>
        );
    }

    return (
        <AuthLayout
            title="Create Account"
            subtitle={stepSubtitle[step]}
        >
            {/* Step Indicator */}
            <StepIndicator currentStep={step} />

            {/* ── Phone Step ── */}
            {step === 'phone' && (
                <form onSubmit={handleRequestOtp} className="space-y-5 animate-auth-fade-in">
                    <div className="space-y-1.5">
                        <label htmlFor="reg-phone" className="block text-sm font-semibold text-gray-700">
                            Mobile Number <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                            <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                            <div className="absolute left-10 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium select-none">+91</div>
                            <input
                                id="reg-phone"
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
                                aria-describedby={phoneError ? 'reg-phone-error' : 'reg-phone-help'}
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
                            <p id="reg-phone-error" className="text-xs text-red-600 flex items-center gap-1" role="alert">
                                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
                                </svg>
                                {phoneError}
                            </p>
                        ) : (
                            <p id="reg-phone-help" className="text-xs text-gray-400">We&apos;ll send you a one-time verification code</p>
                        )}
                    </div>

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
                            <span className="px-3 bg-white text-gray-400">Already have an account?</span>
                        </div>
                    </div>

                    <Link
                        href="/login"
                        className="
                            block w-full text-center py-3 px-6 rounded-xl
                            border-2 border-green-200 text-green-700 font-semibold
                            hover:bg-green-50 hover:border-green-300
                            focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2
                            active:scale-[0.98] transition-all duration-200
                        "
                    >
                        Sign In Instead
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
                        <div className="space-y-1.5">
                            <label htmlFor="reg-otp" className="block text-sm font-semibold text-gray-700">
                                Verification Code <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                                <input
                                    id="reg-otp"
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
                                    aria-describedby={otpError ? 'reg-otp-error' : undefined}
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
                                <p id="reg-otp-error" className="text-xs text-red-600" role="alert">{otpError}</p>
                            )}
                        </div>

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
                                    <span>Verify &amp; Continue</span>
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

            {/* ── Profile Step ── */}
            {step === 'profile' && (
                <div className="space-y-5 animate-auth-slide-up">
                    {/* Welcome banner */}
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
                        <Sparkles className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="text-sm font-semibold text-green-800">Phone verified!</p>
                            <p className="text-xs text-green-700 mt-0.5">
                                Almost done — fill in your details below.
                            </p>
                        </div>
                    </div>

                    <form onSubmit={handleCompleteProfile} className="space-y-4">
                        {/* Full Name */}
                        <div className="space-y-1.5">
                            <label htmlFor="reg-name" className="block text-sm font-semibold text-gray-700">
                                Full Name <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                                <input
                                    id="reg-name"
                                    type="text"
                                    placeholder="Enter your full name"
                                    value={name}
                                    onChange={(e) => {
                                        setName(e.target.value);
                                        if (nameError) setNameError('');
                                    }}
                                    autoFocus
                                    aria-invalid={!!nameError}
                                    className={`
                                        w-full pl-11 pr-4 py-3 rounded-xl border-2 text-base transition-all duration-200
                                        placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-0
                                        ${nameError
                                            ? 'border-red-300 focus:border-red-500 focus:ring-red-200'
                                            : 'border-gray-200 focus:border-green-500 focus:ring-green-200'
                                        }
                                    `}
                                />
                            </div>
                            {nameError && (
                                <p className="text-xs text-red-600" role="alert">{nameError}</p>
                            )}
                        </div>

                        {/* Age */}
                        <div className="space-y-1.5">
                            <label htmlFor="reg-age" className="block text-sm font-semibold text-gray-700">
                                Age <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <Calendar className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400" />
                                <input
                                    id="reg-age"
                                    type="number"
                                    inputMode="numeric"
                                    placeholder="25"
                                    min="18"
                                    max="120"
                                    value={age}
                                    onChange={(e) => {
                                        setAge(e.target.value);
                                        if (ageError) setAgeError('');
                                    }}
                                    aria-invalid={!!ageError}
                                    className={`
                                        w-full pl-11 pr-4 py-3 rounded-xl border-2 text-base transition-all duration-200
                                        placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-0
                                        ${ageError
                                            ? 'border-red-300 focus:border-red-500 focus:ring-red-200'
                                            : 'border-gray-200 focus:border-green-500 focus:ring-green-200'
                                        }
                                    `}
                                />
                            </div>
                            {ageError && (
                                <p className="text-xs text-red-600" role="alert">{ageError}</p>
                            )}
                        </div>

                        {/* State */}
                        <div className="space-y-1.5">
                            <label htmlFor="reg-state" className="block text-sm font-semibold text-gray-700">
                                State <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400 z-10 pointer-events-none" />
                                <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                                <select
                                    id="reg-state"
                                    value={selectedState}
                                    onChange={(e) => setSelectedState(e.target.value)}
                                    disabled={loading}
                                    className={`
                                        w-full pl-11 pr-10 py-3 rounded-xl border-2 text-base transition-all duration-200 appearance-none bg-white
                                        focus:outline-none focus:ring-2 focus:ring-offset-0
                                        border-gray-200 focus:border-green-500 focus:ring-green-200
                                        disabled:bg-gray-50 disabled:cursor-not-allowed
                                        ${!selectedState ? 'text-gray-400' : 'text-gray-900'}
                                    `}
                                >
                                    <option value="" disabled>Select your state</option>
                                    {INDIAN_STATES.map((s) => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* District */}
                        <div className="space-y-1.5">
                            <label htmlFor="reg-district" className="block text-sm font-semibold text-gray-700">
                                District <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                                <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-gray-400 z-10 pointer-events-none" />
                                {loadingDistricts ? (
                                    <Loader2 className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-green-600 animate-spin pointer-events-none" />
                                ) : (
                                    <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                                )}
                                <select
                                    id="reg-district"
                                    value={district}
                                    onChange={(e) => setDistrict(e.target.value)}
                                    disabled={loading || !selectedState || loadingDistricts}
                                    className={`
                                        w-full pl-11 pr-10 py-3 rounded-xl border-2 text-base transition-all duration-200 appearance-none bg-white
                                        focus:outline-none focus:ring-2 focus:ring-offset-0
                                        border-gray-200 focus:border-green-500 focus:ring-green-200
                                        disabled:bg-gray-50 disabled:cursor-not-allowed
                                        ${!district ? 'text-gray-400' : 'text-gray-900'}
                                    `}
                                >
                                    <option value="" disabled>
                                        {!selectedState
                                            ? 'Select state first'
                                            : loadingDistricts
                                                ? 'Loading districts...'
                                                : 'Select your district'}
                                    </option>
                                    {districts.map((d) => (
                                        <option key={d} value={d}>{d}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading || !name.trim() || !age || !selectedState || !district}
                            className="
                                w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl mt-2
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
                                    <span>Creating Account...</span>
                                </>
                            ) : (
                                <>
                                    <span>Complete Registration</span>
                                    <ArrowRight className="w-5 h-5" />
                                </>
                            )}
                        </button>
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
