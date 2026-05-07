import React from 'react';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Screens
import MenuScreen from '../screens/menu/MenuScreen';
import OrdersScreen from '../screens/orders/OrdersScreen';
import InventoryScreen from '../screens/inventory/InventoryScreen';
import ProfileScreen from '../screens/profile/ProfileScreen';

const Tab = createBottomTabNavigator();

const MainTabNavigator = () => {
  return (
    <Tab.Navigator
      screenOptions={({route}) => ({
        tabBarIcon: ({focused, color, size}) => {
          let iconName;

          if (route.name === 'Menu') {
            iconName = focused ? 'restaurant' : 'restaurant-outline';
          } else if (route.name === 'Orders') {
            iconName = focused ? 'clipboard-list' : 'clipboard-list-outline';
          } else if (route.name === 'Inventory') {
            iconName = focused ? 'package-variant' : 'package-variant-closed';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'account' : 'account-outline';
          }

          return <Icon name={iconName} size={focused ? 28 : 24} color={color} />;
        },
        tabBarActiveTintColor: '#1976D2',
        tabBarInactiveTintColor: '#666',
        tabBarActiveBackgroundColor: 'rgba(25, 118, 210, 0.1)',
        tabBarInactiveBackgroundColor: 'transparent',
        tabBarStyle: {
          height: 70,
          paddingBottom: 10,
          paddingTop: 10,
          elevation: 8,
          borderTopWidth: 0,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
        },
        headerShown: false,
      })}>
      <Tab.Screen
        name="Menu"
        component={MenuScreen}
        options={{tabBarLabel: 'Order'}}
      />
      <Tab.Screen
        name="Orders"
        component={OrdersScreen}
        options={{tabBarLabel: 'Orders'}}
      />
      <Tab.Screen
        name="Inventory"
        component={InventoryScreen}
        options={{tabBarLabel: 'Stock'}}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{tabBarLabel: 'Me'}}
      />
    </Tab.Navigator>
  );
};

export default MainTabNavigator;