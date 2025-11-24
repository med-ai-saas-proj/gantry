import { create } from 'zustand';

export type UserAPIKey = {
  id: string;
  name: string;
  secretKey: string;
  createdAt: Date;
  lastUsed: Date | null;
  createdBy: string;
  permissions: string[];
};

interface UserAPIKeyState {
  apiKeys: UserAPIKey[];
}

interface UserAPIKeyActions {
  addAPIKey: (key: Omit<UserAPIKey, 'id' | 'createdAt' | 'lastUsed'>) => void;
  updateAPIKey: (
    id: string,
    key: Pick<UserAPIKey, 'name' | 'permissions'>
  ) => void;
  deleteAPIKey: (id: string) => void;
}

type UserAPIKeyStore = UserAPIKeyState & UserAPIKeyActions;

export const useUserAPIKeyStore = create<UserAPIKeyStore>((set) => ({
  apiKeys: [],

  addAPIKey: (newKeyData) =>
    set((state) => ({
      apiKeys: [
        ...state.apiKeys,
        {
          id: crypto.randomUUID(),
          createdAt: new Date(),
          lastUsed: null,
          ...newKeyData,
        },
      ],
    })),

  updateAPIKey: (id, updatedKey) =>
    set((state) => ({
      apiKeys: state.apiKeys.map((key) =>
        key.id === id ? { ...key, ...updatedKey } : key
      ),
    })),

  deleteAPIKey: (id) =>
    set((state) => ({
      apiKeys: state.apiKeys.filter((key) => key.id !== id),
    })),
}));
