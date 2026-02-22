import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { mmkvStorage } from '../services/mmkvStorage';

interface SettingsState {
  language: 'en' | 'hi';
  theme: 'light' | 'dark';
}

interface SettingsActions {
  setLanguage: (lang: 'en' | 'hi') => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useSettingsStore = create<SettingsState & SettingsActions>()(
  persist(
    set => ({
      language: 'en',
      theme: 'light',
      setLanguage: language => set({ language }),
      setTheme: theme => set({ theme }),
    }),
    {
      name: 'settings-storage',
      storage: mmkvStorage,
    },
  ),
);
