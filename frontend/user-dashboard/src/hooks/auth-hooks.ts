import { useMutation, useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api/client';
import type { User } from '@/types/api';

export const useLogin = () => {
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const { data } = await apiClient.post<{
        token: string;
        user: User;
      }>('/auth/login', credentials);
      return data;
    },
  });
};

export const useRegister = () => {
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const { data } = await apiClient.post<{
        token: string;
        user: User;
      }>('/auth/register', credentials);
      return data;
    },
  });
};

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
  });
};
