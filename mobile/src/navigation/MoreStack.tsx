import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { MoreStackParamList } from '../types/navigation';
import MoreMenuScreen from '../screens/more/MoreMenuScreen';
import InventoryScreen from '../screens/inventory/InventoryScreen';
import AddInventoryScreen from '../screens/inventory/AddInventoryScreen';
import SalesScreen from '../screens/sales/SalesScreen';
import AddSaleScreen from '../screens/sales/AddSaleScreen';
import CommunityStack from './CommunityStack';
import NotificationsScreen from '../screens/notifications/NotificationsScreen';
import ProfileScreen from '../screens/more/ProfileScreen';
import SettingsScreen from '../screens/more/SettingsScreen';

const Stack = createNativeStackNavigator<MoreStackParamList>();

export default function MoreStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="MoreMenu" component={MoreMenuScreen} options={{ title: 'More' }} />
      <Stack.Screen name="Inventory" component={InventoryScreen} options={{ title: 'Inventory' }} />
      <Stack.Screen name="AddInventory" component={AddInventoryScreen} options={{ title: 'Add Inventory' }} />
      <Stack.Screen name="Sales" component={SalesScreen} options={{ title: 'Sales' }} />
      <Stack.Screen name="AddSale" component={AddSaleScreen} options={{ title: 'Record Sale' }} />
      <Stack.Screen name="Community" component={CommunityStack as any} options={{ headerShown: false }} />
      <Stack.Screen name="Notifications" component={NotificationsScreen} options={{ title: 'Notifications' }} />
      <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
    </Stack.Navigator>
  );
}
