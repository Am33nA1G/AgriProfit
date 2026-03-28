// mobile/src/navigation/CommunityStack.tsx
import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../theme/tokens';
import { CommunityFeedScreen } from '../screens/community/CommunityFeedScreen';
import { PostDetailScreen } from '../screens/community/PostDetailScreen';

export type CommunityStackParamList = {
    CommunityFeed: undefined;
    PostDetail: { post_id: string };
};

const Stack = createNativeStackNavigator<CommunityStackParamList>();

export function CommunityStack() {
    return (
        <Stack.Navigator>
            <Stack.Screen name="CommunityFeed" component={CommunityFeedScreen} options={{ headerShown: false }} />
            <Stack.Screen
                name="PostDetail"
                component={PostDetailScreen}
                options={{
                    title: 'Post',
                    headerBackTitle: 'Back',
                    headerTintColor: colors.primary,
                }}
            />
        </Stack.Navigator>
    );
}
