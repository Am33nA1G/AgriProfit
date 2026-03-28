// mobile/src/navigation/InventoryStack.tsx
import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../theme/tokens';
import { InventoryScreen } from '../screens/inventory/InventoryScreen';
import { InventoryAnalysisScreen } from '../screens/inventory/InventoryAnalysisScreen';

export type InventoryStackParamList = {
    Inventory: undefined;
    InventoryAnalysis: undefined;
};

const Stack = createNativeStackNavigator<InventoryStackParamList>();

export function InventoryStack() {
    return (
        <Stack.Navigator>
            <Stack.Screen name="Inventory" component={InventoryScreen} options={{ headerShown: false }} />
            <Stack.Screen
                name="InventoryAnalysis"
                component={InventoryAnalysisScreen}
                options={{
                    title: 'Inventory Analysis',
                    headerBackTitle: 'Back',
                    headerTintColor: colors.primary,
                }}
            />
        </Stack.Navigator>
    );
}
