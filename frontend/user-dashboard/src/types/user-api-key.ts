export type UserAPIKey = {
  id: string;
  name: string;
  secretKey: string;
  createdAt: Date;
  lastUsed: Date | null;
  createdBy: string;
  permissions: string[];
};
