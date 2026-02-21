'use client';

import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { Globe, Loader2 } from 'lucide-react';

const LANGUAGES = [
    { code: 'en', label: 'English', nativeLabel: 'English' },
    { code: 'ml', label: 'Malayalam', nativeLabel: 'മലയാളം' },
] as const;

export default function LanguageSwitcher() {
    const locale = useLocale();
    const router = useRouter();
    const [isPending, startTransition] = useTransition();

    const handleLanguageChange = (newLocale: string) => {
        // Set cookie for server-side locale detection
        document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=31536000;SameSite=Lax`;

        // Also store in localStorage as fallback
        localStorage.setItem('preferredLanguage', newLocale);

        // Refresh the page to re-render with new locale
        startTransition(() => {
            router.refresh();
        });
    };

    return (
        <div className="relative flex items-center">
            <Globe className="absolute left-2.5 w-4 h-4 text-muted-foreground pointer-events-none" />
            {isPending && (
                <Loader2 className="absolute right-2.5 w-3.5 h-3.5 text-muted-foreground animate-spin pointer-events-none" />
            )}
            <select
                value={locale}
                onChange={(e) => handleLanguageChange(e.target.value)}
                disabled={isPending}
                aria-label="Select language"
                className="
                    pl-8 pr-8 py-1.5 rounded-lg border border-border bg-background
                    text-sm font-medium appearance-none cursor-pointer
                    hover:bg-muted/50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1
                    disabled:opacity-50 disabled:cursor-wait
                    transition-colors
                "
            >
                {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                        {lang.nativeLabel}
                    </option>
                ))}
            </select>
        </div>
    );
}
