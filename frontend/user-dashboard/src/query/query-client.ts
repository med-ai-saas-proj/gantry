import { QueryClient } from '@tanstack/react-query';

export const query_client = new QueryClient({
  // TODO: Set using ENV for dev and production values
  defaultOptions: {
    queries: {
      retry: 0,
      refetchOnWindowFocus: false,
      staleTime: 0,
    },
  },
});
