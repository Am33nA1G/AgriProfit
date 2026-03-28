// mobile/src/providers/QueryProvider.tsx
// TanStack React Query provider — API-03: all server state via React Query.

import React, { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000,     // 5 minutes — data stays fresh
            gcTime: 10 * 60 * 1000,       // 10 minutes — cache retention
            retry: 2,
            refetchOnWindowFocus: false,   // RN has no window focus concept — prevents
            // spurious refetches on tab switch (NAV-04)
        },
        mutations: {
            retry: 0,
        },
    },
});

interface QueryProviderProps {
    children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
    return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
}
