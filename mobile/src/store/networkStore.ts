import { create } from 'zustand';
import NetInfo from '@react-native-community/netinfo';

interface NetworkState {
  isConnected: boolean | null;
  connectionType: string;
  _initialized: boolean;
}

interface NetworkActions {
  initialize: () => () => void;
}

export const useNetworkStore = create<NetworkState & NetworkActions>((set, get) => ({
  isConnected: null as boolean | null,
  connectionType: 'unknown',
  _initialized: false,

  initialize: () => {
    if (get()._initialized) return () => {};

    set({ _initialized: true });

    const unsubscribe = NetInfo.addEventListener(state => {
      set({
        isConnected: state.isConnected ?? true,
        connectionType: state.type,
      });
    });

    return unsubscribe;
  },
}));
