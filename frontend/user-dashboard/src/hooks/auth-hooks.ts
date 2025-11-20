import { useMutation } from '@tanstack/react-query';
import apiClient from '@/query/api-client';
import { useAuthStore } from '@/store/auth-store';
import type { User } from '@/types/auth';

export const useLogin = () => {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const { data } = await apiClient.post<{
        token: string;
        user: User;
      }>('/login', credentials);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.token);
    },
  });
};

export const useRegister = () => {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const { data } = await apiClient.post<{
        token: string;
      }>('/register', credentials);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.token);
    },
  });
};

// export const useCurrentUser = () => {
//     return useQuery({
//         queryKey: ["currentUser"],
//         queryFn: async () => {
//             const { data } = await apiClient.get<User>("/me");
//             return data;
//         },
//     });
// };

export const useSignOut = () => {
  const logout = useAuthStore((state) => state.logout);

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/logout');
    },
    onSuccess: () => {
      logout();
    },
  });
};

// TODO: improve this hook, somehow
export const useAuthStatus = () => {
  const token = useAuthStore((state) => state.token);
  return !!token;
};
