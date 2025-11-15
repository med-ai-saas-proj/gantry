import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/shadcn/button';
import { Input } from '@/components/shadcn/input';
import { useLogin } from '@/hooks/auth-hooks';
import { useAuthStore } from '@/store/auth-store';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const { mutate: login, isPending, isError, error } = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(
      { email, password },
      {
        onSuccess: (data) => {
          setAuth(data.token, data.user);
          navigate('/dashboard');
        },
      }
    );
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight">Login</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <Input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isPending}
              className="rounded-full"
            />

            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isPending}
              className="rounded-full"
            />
          </div>

          {isError && (
            <div className="text-destructive text-sm text-center">
              {error?.message || 'Login failed. Please try again.'}
            </div>
          )}

          <Button type="submit" disabled={isPending}>
            {isPending ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default Login;
