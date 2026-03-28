// mobile/src/lib/haptics.ts
// Phase 6 plan 06-02 — UX-04: haptic feedback via expo-haptics.
// Note: Haptics are silent on emulators — only works on physical device.

import * as Haptics from 'expo-haptics';

export const haptics = {
    /** Medium impact — commodity tap, button press */
    tap: () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => { });
    },
    /** Success notification — OTP verify success */
    success: () => {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => { });
    },
    /** Light impact — pull-to-refresh complete */
    refresh: () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => { });
    },
};
