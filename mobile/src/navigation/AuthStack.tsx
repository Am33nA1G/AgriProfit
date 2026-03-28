// mobile/src/navigation/AuthStack.tsx
// Stack navigator for auth screens using React Navigation v7 native-stack.

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { PhoneEntryScreen } from '../screens/auth/PhoneEntryScreen';
import { OTPEntryScreen } from '../screens/auth/OTPEntryScreen';

export type AuthStackParamList = {
    PhoneEntry: undefined;
    OTPEntry: { phoneNumber: string };
};

const Stack = createNativeStackNavigator<AuthStackParamList>();

export function AuthStack() {
    return (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
            <Stack.Screen name="PhoneEntry" component={PhoneEntryScreen} />
            <Stack.Screen name="OTPEntry" component={OTPEntryScreen} />
        </Stack.Navigator>
    );
}
