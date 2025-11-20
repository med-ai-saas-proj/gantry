import { Lock, Plus } from 'lucide-react';
import { useUserAPIKeyStore } from '@/store/user-api-key-store';
import type { TriggerProps } from './useCreateKeyDialog';
import UserAPIKeyDialog from './user-api-key-dialog';
import UserAPIKeyTable from './user-api-key-table';

const UserAPIKeyDashboard = ({
  open,
  setOpen,
  Trigger,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
  Trigger: React.ComponentType<TriggerProps>;
}) => {
  const apiKeys = useUserAPIKeyStore((state) => state.apiKeys);

  const hasKeys = apiKeys.length > 0;
  let createKeyFromEmptyContent = null;

  if (!hasKeys) {
    createKeyFromEmptyContent = (
      <div className="flex flex-col items-center justify-center mt-20">
        <div className="bg-gray-100 p-4 rounded-md mb-3">
          <Lock />
        </div>
        <p className="font-bold">Create an API key to access the OpenAI API</p>
        <Trigger className="mt-3">
          <Plus />
          Create new secret key
        </Trigger>
      </div>
    );
  } else {
    createKeyFromEmptyContent = <UserAPIKeyTable apiKeys={apiKeys} />;
  }

  return (
    <>
      <p className="mb-4">
        You have permission to view and manage all API keys in this project.
      </p>
      <p className="mb-4">
        Do not share your API key with others or expose it in the browser or
        other client-side code. To protect your account's security, OpenAI may
        automatically disable any API key that has leaked publicly.
      </p>
      <p className="mb-4">View usage per API key on the Usage page.</p>
      {createKeyFromEmptyContent}
      <UserAPIKeyDialog open={open} onOpenChange={setOpen} />
    </>
  );
};

export default UserAPIKeyDashboard;
