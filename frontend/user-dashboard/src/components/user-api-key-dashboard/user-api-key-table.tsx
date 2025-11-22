import { SquarePen, Trash } from 'lucide-react';
import React, { useState } from 'react';
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
  const [selectedApiKeyId, setSelectedApiKeyId] = useState<string | null>(null);

  const onDeleteApiKey = (apikeyId: string) => {
    deleteAPIKey(apikeyId);
  };

  const onOpenUpdateUserAPIKeyDialog = (selectedApiKeyId: string) => {
    setOpenUpdateUserAPIKeyDialog(true);
    setSelectedApiKeyId(selectedApiKeyId);
  };

  const maskKey = (key: string, maskLength = 10): string => {
    if (key.length <= maskLength) return key;

    const visibleStart = key.slice(0, 4);
    const visibleEnd = key.slice(-4);

    const mask = '*'.repeat(maskLength);

    return `${visibleStart}${mask}${visibleEnd}`;
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
          <TableRow key={apiKey.id}>
            <TableCell className="font-medium">{apiKey.name}</TableCell>
            <TableCell>{maskKey(apiKey.secretKey)}</TableCell>
            <TableCell>{apiKey.createdAt.toLocaleDateString()}</TableCell>
            <TableCell>
              {apiKey.lastUsed ? apiKey.lastUsed.toLocaleDateString() : 'Never'}
            </TableCell>
            <TableCell>{apiKey.createdBy}</TableCell>
            <TableCell>{apiKey.permissions.join(', ')}</TableCell>
            <TableCell>
              <SquarePen
                size={16}
                onClick={() => onOpenUpdateUserAPIKeyDialog(apiKey.id)}
              />
            </TableCell>
            <TableCell>
              <Trash
                size={16}
                color="#ce4034"
                onClick={() => onDeleteApiKey(apiKey.id)}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
      {selectedApiKeyId && (
        <UserAPIKeyUpdateDialog
          apikeyId={selectedApiKeyId}
          open={openUpdateUserAPIKeyDialog}
          onOpenChange={() => setOpenUpdateUserAPIKeyDialog(false)}
        />
      )}
    </Table>
  );
};

export default UserAPIKeyTable;
