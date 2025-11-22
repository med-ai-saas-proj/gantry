import { SquarePen, Trash } from 'lucide-react';
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/shadcn/table';
import { useUserAPIKeyStore } from '@/store/user-api-key-store';
import type { UserAPIKey } from '@/types/user-api-key';
import UserAPIKeyUpdateDialog from './user-api-key-update-dialog';

const UserAPIKeyTable = ({ apiKeys }: { apiKeys: UserAPIKey[] }) => {
  const deleteAPIKey = useUserAPIKeyStore((state) => state.deleteAPIKey);
  const [openUpdateUserAPIKeyDialog, setOpenUpdateUserAPIKeyDialog] =
    React.useState(false);

  const onDeleteApiKey = (apikeyId: string) => {
    deleteAPIKey(apikeyId);
  };

  const onOpenUpdateUserAPIKeyDialog = () => {
    setOpenUpdateUserAPIKeyDialog(true);
  };

  return (
    <Table className="mt-6">
      <TableHeader>
        <TableRow>
          <TableHead className="w-[40%]">NAME</TableHead>
          <TableHead>SECRET KEY</TableHead>
          <TableHead>CREATED</TableHead>
          <TableHead>LAST USED</TableHead>
          <TableHead>CREATED BY</TableHead>
          <TableHead>PERMISSIONS</TableHead>
          <TableHead></TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {apiKeys.map((apiKey) => (
          <React.Fragment key={apiKey.id}>
            <TableRow>
              <TableCell className="font-medium">{apiKey.name}</TableCell>
              <TableCell>{apiKey.secretKey}</TableCell>
              <TableCell>{apiKey.createdAt.toLocaleDateString()}</TableCell>
              <TableCell>
                {apiKey.lastUsed
                  ? apiKey.lastUsed.toLocaleDateString()
                  : 'Never'}
              </TableCell>
              <TableCell>{apiKey.createdBy}</TableCell>
              <TableCell>{apiKey.permissions.join(', ')}</TableCell>
              <TableCell>
                <SquarePen size={16} onClick={onOpenUpdateUserAPIKeyDialog} />
              </TableCell>
              <TableCell>
                <Trash
                  size={16}
                  color="#ce4034"
                  onClick={() => onDeleteApiKey(apiKey.id)}
                />
              </TableCell>
            </TableRow>
            <UserAPIKeyUpdateDialog
              apikeyId={apiKey.id}
              open={openUpdateUserAPIKeyDialog}
              onOpenChange={() => setOpenUpdateUserAPIKeyDialog(false)}
            />
          </React.Fragment>
        ))}
      </TableBody>
    </Table>
  );
};

export default UserAPIKeyTable;
