import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';

export const locales = ['en', 'ml'] as const;
export type Locale = (typeof locales)[number];

export default getRequestConfig(async () => {
    const cookieStore = await cookies();
    const cookieLocale = cookieStore.get('NEXT_LOCALE')?.value;

    const locale: Locale =
        cookieLocale && locales.includes(cookieLocale as Locale)
            ? (cookieLocale as Locale)
            : 'en';

    return {
        locale,
        messages: (await import(`../../messages/${locale}.json`)).default,
    };
});
