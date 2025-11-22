import { useMutation } from '@tanstack/react-query';
import apiClient from '@/query/api-client';

interface CreateApiKeyRequest {
  name: string | null;
  project_id: string;
  permissions: string[];
}

interface CreateApiKeyResponse {
  key: string;
}

export const useCreateUserApiKey = () => {
  return useMutation({
    mutationFn: async (credentials: CreateApiKeyRequest) => {
      const { data } = await apiClient.post<CreateApiKeyResponse>(
        '/api_keys',
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
      name?: string;
      permissions?: string[];
    }) => {
      const { data } = await apiClient.put(
        `/api_keys/${credentials.apikeyId}`,
        {
          name: credentials.name,
          permissions: credentials.permissions,
        }
      );
      return data;
    },
  });
};

export const useDeleteUserApiKey = () => {
  return useMutation({
    mutationFn: async (apikeyId: string) => {
      const { data } = await apiClient.delete(`/api_keys/${apikeyId}`);
      return data;
    },
  });
};
