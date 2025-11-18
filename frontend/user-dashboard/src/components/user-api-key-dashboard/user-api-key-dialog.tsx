import { Plus } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/shadcn/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/shadcn/dialog';
import { Input } from '@/components/shadcn/input';
import { Label } from '@/components/shadcn/label';
import { UserAPIKeySaveDialog } from './user-api-key-save-dialog';

const UserAPIKeyDialog = () => {
  const [openCreate, setOpenCreate] = useState(false);
  const [openSave, setOpenSave] = useState(false);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    setOpenCreate(false);
    setOpenSave(true);
  };

  return (
    <>
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <form id="create-secret-key-form" onSubmit={handleSubmit}>
          <DialogTrigger asChild>
            <Button className="mt-3">
              <Plus />
              Create new secret key
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create new secret key</DialogTitle>
              <DialogDescription>
                This API key is tied to your user and can make requests against
                the selected project. If you are removed from the organiation or
                project, this key will be disabled.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4">
              <div className="grid gap-3">
                <Label htmlFor="name">Name</Label>
                <Input id="name" name="name" defaultValue="Pedro Duarte" />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button type="submit" form="create-secret-key-form">
                Create secret key
              </Button>
            </DialogFooter>
          </DialogContent>
        </form>
      </Dialog>

      <UserAPIKeySaveDialog open={openSave} onOpenChange={setOpenSave} />
    </>
  );
};

export { UserAPIKeyDialog };
