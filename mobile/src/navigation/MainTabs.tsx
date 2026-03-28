// mobile/src/navigation/MainTabs.tsx
// Bottom tab navigator with 5 tabs: Inventory, Forecast, Transport, Community, Sales.

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigatorScreenParams } from '@react-navigation/native';
import { Archive, TrendingUp, Truck, Users, ShoppingCart, UserCircle } from 'lucide-react-native';
import { colors, typography } from '../theme/tokens';
import { InventoryStack, type InventoryStackParamList } from './InventoryStack';
import { CommunityStack, type CommunityStackParamList } from './CommunityStack';
import { ForecastScreen } from '../screens/forecast/ForecastScreen';
import { TransportScreen } from '../screens/transport/TransportScreen';
import { SalesScreen } from '../screens/sales/SalesScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';

export type MainTabsParamList = {
    Inventory: NavigatorScreenParams<InventoryStackParamList>;
    Forecast: undefined;
    Transport: undefined;
    Community: NavigatorScreenParams<CommunityStackParamList>;
    Sales: undefined;
    Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

const ICON_SIZE = 22;

export function MainTabs() {
    return (
        <Tab.Navigator
            screenOptions={{
                headerShown: false,
                tabBarActiveTintColor: colors.primary,
                tabBarInactiveTintColor: colors.muted,
                tabBarStyle: {
                    backgroundColor: colors.background,
                    borderTopColor: colors.border,
                    borderTopWidth: 1,
                    height: 64,
                    paddingBottom: 10,
                    paddingTop: 6,
                },
                tabBarLabelStyle: {
                    fontSize: typography.fontSize.xs,
                    fontWeight: typography.fontWeight.medium,
                },
            }}
        >
            <Tab.Screen
                name="Inventory"
                component={InventoryStack}
                options={{ tabBarIcon: ({ color }) => <Archive size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Forecast"
                component={ForecastScreen}
                options={{ tabBarIcon: ({ color }) => <TrendingUp size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Transport"
                component={TransportScreen}
                options={{ tabBarIcon: ({ color }) => <Truck size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Community"
                component={CommunityStack}
                options={{ tabBarIcon: ({ color }) => <Users size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Sales"
                component={SalesScreen}
                options={{ tabBarIcon: ({ color }) => <ShoppingCart size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Profile"
                component={ProfileScreen}
                options={{ tabBarIcon: ({ color }) => <UserCircle size={ICON_SIZE} color={color} /> }}
            />
        </Tab.Navigator>
    );
}
