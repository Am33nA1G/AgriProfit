'use client';

import React from 'react';
import Link from 'next/link';
import { Sprout, Shield, Users, TrendingUp, Leaf } from 'lucide-react';

interface AuthLayoutProps {
    children: React.ReactNode;
    title: string;
    subtitle: string;
}

export default function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-amber-50/30 flex">
            {/* Skip to content (accessibility) */}
            <a
                href="#auth-form"
                className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-green-600 text-white px-4 py-2 rounded-lg z-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
                Skip to form
            </a>

            {/* Left Side - Branding & Benefits (desktop only) */}
            <div className="hidden lg:flex lg:w-[45%] xl:w-1/2 bg-gradient-to-br from-green-700 via-green-800 to-green-900 p-10 xl:p-14 flex-col justify-between relative overflow-hidden">
                {/* Decorative blurs */}
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-green-500/15 rounded-full blur-3xl -translate-y-1/3 translate-x-1/3" />
                <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-emerald-400/10 rounded-full blur-3xl translate-y-1/3 -translate-x-1/3" />
                <div className="absolute top-1/2 left-1/2 w-[300px] h-[300px] bg-yellow-500/5 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />

                {/* Logo & Hero */}
                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-12">
                        <div className="bg-white/95 p-3 rounded-2xl shadow-lg shadow-green-900/20">
                            <Sprout className="w-8 h-8 text-green-700" />
                        </div>
                        <div>
                            <h1 className="text-2xl xl:text-3xl font-bold text-white tracking-tight">AgriProfit</h1>
                            <p className="text-green-200/80 text-sm">Smart Farming, Better Returns</p>
                        </div>
                    </div>

                    <div className="bg-white/[0.07] backdrop-blur-sm rounded-2xl p-8 xl:p-10 border border-white/10">
                        <div className="flex items-center gap-2 mb-4">
                            <Leaf className="w-6 h-6 text-yellow-400" />
                            <span className="text-yellow-300/90 text-sm font-medium uppercase tracking-wider">For Indian Farmers</span>
                        </div>
                        <h2 className="text-3xl xl:text-4xl font-bold text-white leading-tight mb-4">
                            Empowering Farmers<br />with Market Data
                        </h2>
                        <p className="text-green-100/70 text-base xl:text-lg leading-relaxed">
                            Track real-time commodity prices, calculate transport costs,
                            and connect with farmers across India — all in one platform.
                        </p>
                    </div>
                </div>

                {/* Feature grid */}
                <div className="relative z-10 grid grid-cols-2 gap-4 mt-8">
                    {[
                        { icon: Shield, title: '100% Secure', desc: 'Your data is protected', color: 'text-yellow-300' },
                        { icon: Users, title: '10,000+ Farmers', desc: 'Growing community', color: 'text-yellow-300' },
                        { icon: TrendingUp, title: 'Live Prices', desc: '500+ mandis tracked', color: 'text-yellow-300' },
                        { icon: Sprout, title: 'Free Forever', desc: 'No hidden charges', color: 'text-yellow-300' },
                    ].map(({ icon: Icon, title: t, desc, color }) => (
                        <div
                            key={t}
                            className="bg-white/[0.07] backdrop-blur-sm rounded-xl p-4 border border-white/10 hover:bg-white/[0.12] transition-colors duration-300"
                        >
                            <Icon className={`w-7 h-7 ${color} mb-2`} />
                            <h3 className="text-white font-semibold text-sm">{t}</h3>
                            <p className="text-green-200/60 text-xs mt-0.5">{desc}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right Side - Auth Form */}
            <div className="flex-1 flex items-center justify-center px-5 py-8 sm:px-8 lg:px-12">
                <div className="w-full max-w-[440px]">
                    {/* Mobile logo */}
                    <div className="lg:hidden mb-8 text-center">
                        <Link href="/" className="inline-flex items-center gap-2.5 bg-white rounded-full pl-4 pr-6 py-2.5 shadow-lg shadow-green-900/5 border border-green-100">
                            <Sprout className="w-6 h-6 text-green-700" />
                            <span className="text-lg font-bold text-gray-900 tracking-tight">AgriProfit</span>
                        </Link>
                    </div>

                    {/* Form card */}
                    <div
                        id="auth-form"
                        className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 p-7 sm:p-8 border border-gray-100/80"
                    >
                        {/* Header */}
                        <div className="text-center mb-7">
                            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight">
                                {title}
                            </h2>
                            <p className="text-gray-500 mt-1.5 text-sm sm:text-base">
                                {subtitle}
                            </p>
                        </div>

                        {/* Form content */}
                        {children}
                    </div>

                    {/* Footer */}
                    <div className="mt-6 text-center text-xs text-gray-400">
                        <p>
                            By continuing, you agree to our{' '}
                            <span className="text-gray-500 hover:text-green-700 cursor-pointer">Terms</span>
                            {' & '}
                            <span className="text-gray-500 hover:text-green-700 cursor-pointer">Privacy Policy</span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
