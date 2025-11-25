import { useMutation } from '@tanstack/react-query';
import { API_ENDPOINTS } from '@/hooks/endponts';
import apiClient from '@/query/api-client';
import { useAuthStore } from '@/store/auth-store';

interface LoginResponse {
  access_token: string;
  token_type: 'Bearer';
  expire_in: number;
  refresh_token: string;
}

interface LoginResponse {
  access_token: string;
  token_type: 'Bearer';
  expire_in: number;
  refresh_token: string;
}

export const useLogin = () => {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const { data } = await apiClient.post<LoginResponse>(
        API_ENDPOINTS.LOGIN,
        { ...credentials, grant_type: 'password' }
      );
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.access_token, data.refresh_token, data.expire_in);
    },
  });
};

// export const useRegister = () => {
//     const setAuth = useAuthStore((state) => state.setAuth);

//     return useMutation({
//         mutationFn: async (credentials: {
//             email: string;
//             password: string;
//         }) => {
//             const { data } = await apiClient.post<{
//                 token: string;
//             }>("auth/register", credentials);
//             return data;
//         },
//         onSuccess: (data) => {
//             setAuth(data.token, "", 3600);
//         },
//     });
// };

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
      await apiClient.post(API_ENDPOINTS.LOGOUT);
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
