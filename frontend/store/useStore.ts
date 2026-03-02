import { create } from 'zustand';

interface AppState {
  user: string | null;
  setUser: (_user: string) => void;
}

export const useStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user })
}));