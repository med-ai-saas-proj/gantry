import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/shadcn/table';
import type { UserAPIKey } from '@/types/user-api-key';

const UserAPIKeyTable = ({ apiKeys }: { apiKeys: UserAPIKey[] }) => {
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
        </TableRow>
      </TableHeader>
      <TableBody>
        {apiKeys.map((apiKey) => (
          <TableRow key={apiKey.id}>
            <TableCell className="font-medium">{apiKey.name}</TableCell>
            <TableCell>{apiKey.secretKey}</TableCell>
            <TableCell>{apiKey.createdAt.toLocaleDateString()}</TableCell>
            <TableCell>
              {apiKey.lastUsed ? apiKey.lastUsed.toLocaleDateString() : 'Never'}
            </TableCell>
            <TableCell>{apiKey.createdBy}</TableCell>
            <TableCell>{apiKey.permissions.join(', ')}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default UserAPIKeyTable;
