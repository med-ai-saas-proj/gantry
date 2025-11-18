import UserAPIKeyDashboard from '@/components/user-api-key-dashboard/user-api-key-dashboard';
import DashboardLayout from '@/layouts/DashboardLayout';

export default function APIKeysPage() {
  return (
    <DashboardLayout pageTitle="API Keys">
      <UserAPIKeyDashboard />
    </DashboardLayout>
  );
}
