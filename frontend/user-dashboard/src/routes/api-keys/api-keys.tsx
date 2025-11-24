import { Plus } from 'lucide-react';
import useCreateKeyDialog from '@/components/user-api-key-dashboard/useCreateKeyDialog';
import UserAPIKeyDashboard from '@/components/user-api-key-dashboard/user-api-key-dashboard';
import DashboardLayout from '@/layouts/DashboardLayout';

export default function APIKeysPage() {
  const { open, setOpen, Trigger } = useCreateKeyDialog();

  const headerActions = (
    <Trigger>
      <Plus /> Create new secret key
    </Trigger>
  );

  return (
    <DashboardLayout pageTitle="API Keys" headerRight={headerActions}>
      <UserAPIKeyDashboard open={open} setOpen={setOpen} Trigger={Trigger} />
    </DashboardLayout>
  );
}
