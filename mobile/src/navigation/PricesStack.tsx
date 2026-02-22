import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { PricesStackParamList } from '../types/navigation';
import CommodityListScreen from '../screens/prices/CommodityListScreen';
import CommodityDetailScreen from '../screens/prices/CommodityDetailScreen';

const Stack = createNativeStackNavigator<PricesStackParamList>();

export default function PricesStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="CommodityList" component={CommodityListScreen} options={{ title: 'Prices' }} />
      <Stack.Screen
        name="CommodityDetail"
        component={CommodityDetailScreen}
        options={({ route }) => ({ title: route.params.commodityName })}
      />
    </Stack.Navigator>
  );
}
