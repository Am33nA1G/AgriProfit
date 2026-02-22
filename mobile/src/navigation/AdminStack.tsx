import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { AdminStackParamList } from '../types/navigation';
import AdminDashboardScreen from '../screens/admin/AdminDashboardScreen';
import BroadcastScreen from '../screens/admin/BroadcastScreen';
import AdminUsersScreen from '../screens/admin/AdminUsersScreen';
import AdminPostsScreen from '../screens/admin/AdminPostsScreen';

const Stack = createNativeStackNavigator<AdminStackParamList>();

export default function AdminStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="AdminDashboard" component={AdminDashboardScreen} options={{ title: 'Admin' }} />
      <Stack.Screen name="Broadcast" component={BroadcastScreen} options={{ title: 'Broadcast Alert' }} />
      <Stack.Screen name="AdminUsers" component={AdminUsersScreen} options={{ title: 'Manage Users' }} />
      <Stack.Screen name="AdminPosts" component={AdminPostsScreen} options={{ title: 'Manage Posts' }} />
    </Stack.Navigator>
  );
}
