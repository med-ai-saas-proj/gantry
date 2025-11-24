import { useMutation } from '@tanstack/react-query';
import apiClient from '@/query/api-client';
import type { UserAPIKey } from '@/types/user-api-key';

export const useCreateUserApiKey = () => {
  return useMutation({
    mutationFn: async (credentials: { projectName: string }) => {
      const { data } = await apiClient.post<UserAPIKey>(
        '/api-key',
        credentials
      );
      return data;
    },
  });
};

export const useUpdateUserApiKey = () => {
  return useMutation({
    mutationFn: async (credentials: {
      apikeyId: string;
      projectName?: string;
      permissions?: string[];
    }) => {
      const { data } = await apiClient.put<UserAPIKey>('/api-key', credentials);
      return data;
    },
  });
};

export const useDeleteUserApiKey = () => {
  return useMutation({
    mutationFn: async (credentials: { apikeyId: string }) => {
      const { data } = await apiClient.delete<{ success: boolean }>(
        '/api-key',
        { data: credentials.apikeyId }
      );
      return data;
    },
  });
};
