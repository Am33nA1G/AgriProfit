import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import type { MainTabParamList } from '../types/navigation';
import { useAuthStore } from '../store/authStore';
import { colors } from '../theme/colors';
import DashboardScreen from '../screens/dashboard/DashboardScreen';
import PricesStack from './PricesStack';
import TransportScreen from '../screens/transport/TransportScreen';
import MoreStack from './MoreStack';
import AdminStack from './AdminStack';

const Tab = createBottomTabNavigator<MainTabParamList>();

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Dashboard: '🏠',
    Prices: '📈',
    Transport: '🚛',
    More: '☰',
    Admin: '⚙️',
  };
  return <Text style={{ fontSize: focused ? 22 : 20 }}>{icons[name] ?? '•'}</Text>;
}

export default function MainTabs() {
  const user = useAuthStore(s => s.user);
  const isAdmin = user?.role === 'admin';

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => <TabIcon name={route.name} focused={focused} />,
        tabBarActiveTintColor: colors.primary[600],
        tabBarInactiveTintColor: colors.gray[400],
        headerShown: false,
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Prices" component={PricesStack} />
      <Tab.Screen name="Transport" component={TransportScreen} />
      <Tab.Screen name="More" component={MoreStack} />
      {isAdmin && <Tab.Screen name="Admin" component={AdminStack} />}
    </Tab.Navigator>
  );
}
