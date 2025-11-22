import { zodResolver } from '@hookform/resolvers/zod';
import { Label } from '@radix-ui/react-label';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import z from 'zod';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/shadcn/dialog';
import {
  type UserAPIKey,
  useUserAPIKeyStore,
} from '@/store/user-api-key-store';
import { Button } from '../shadcn/button';
import { Input } from '../shadcn/input';

const apiUpdateSchema = z.object({
  name: z.string().min(1, 'Name must be at least 1 character long'),
});

type ApiUpdateFormData = z.infer<typeof apiUpdateSchema>;

const UserAPIKeyUpdateDialog = ({
  apikeyId,
  open,
  onOpenChange,
}: {
  apikeyId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) => {
  const apiKey = useUserAPIKeyStore((state) =>
    state.apiKeys.find((key) => key.id === apikeyId)
  );
  const updateAPIKey = useUserAPIKeyStore((state) => state.updateAPIKey);

  const {
    register,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm<ApiUpdateFormData>({
    resolver: zodResolver(apiUpdateSchema),
  });

  const onSubmit = (data: ApiUpdateFormData) => {
    onOpenChange(false);

    const name = data.name;

    const newKey: Pick<UserAPIKey, 'name' | 'permissions'> = {
      name,
      permissions: ['read', 'write'],
    };

    updateAPIKey(apikeyId, newKey);
  };

  useEffect(() => {
    if (apiKey) {
      reset({
        name: apiKey.name,
      });
    }
  }, [apiKey, reset]);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit secret key</DialogTitle>
            <DialogDescription>Edit your api key information</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="grid gap-4">
              <div className="grid gap-3">
                <Label>Name</Label>
                <Input
                  id="name"
                  aria-invalid={!!errors.name}
                  {...register('name')}
                />
                <div className="h-5 mt-1.5 px-4">
                  {errors.name && (
                    <p className="text-destructive text-xs">
                      {errors.name.message}
                    </p>
                  )}
                </div>
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button type="submit">Save</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UserAPIKeyUpdateDialog;
