import { Lock, Plus } from 'lucide-react';
import { Button } from '../shadcn/button';

const UserAPIKeyDashboard = () => {
  return (
    <div>
      <p className="mb-4">
        You have permission to view and manage all API keys in this project.
      </p>
      <p className="mb-4">
        Do not share your API key with others or expose it in the browser or
        other client-side code. To protect your account's security, OpenAI may
        automatically disable any API key that has leaked publicly.
      </p>
      <p className="mb-4">View usage per API key on the Usage page.</p>
      <div className="flex flex-col items-center justify-center mt-20">
        <div className="bg-gray-100 p-4 rounded-md mb-3">
          <Lock />
        </div>
        <p className="font-bold">Create an API key to access the OpenAI API</p>
        <Button className="mt-3">
          <Plus />
          Create new secret key
        </Button>
      </div>
    </div>
  );
};

export default UserAPIKeyDashboard;
