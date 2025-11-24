import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { query_client } from '@/query/query-client';
import APIKeysPage from './routes/api-keys/api-keys';
import DashboardPage from './routes/home';

function App() {
  return (
    <QueryClientProvider client={query_client}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/api-keys" element={<APIKeysPage />} />
          <Route path="/login" element={<div>Login</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
