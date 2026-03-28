// mobile/src/lib/toast.ts
// Phase 6 plan 06-01 — UX-03: toast notifications via react-native-toast-message.

import Toast from 'react-native-toast-message';

export const toast = {
    success: (message: string, description?: string) => {
        Toast.show({ type: 'success', text1: message, text2: description, visibilityTime: 3000, position: 'top' });
    },
    error: (message: string, description?: string) => {
        Toast.show({ type: 'error', text1: message, text2: description, visibilityTime: 4000, position: 'top' });
    },
    info: (message: string, description?: string) => {
        Toast.show({ type: 'info', text1: message, text2: description, visibilityTime: 3000, position: 'top' });
    },
};
