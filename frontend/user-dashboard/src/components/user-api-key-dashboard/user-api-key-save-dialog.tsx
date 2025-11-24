import { Button } from '@/components/shadcn/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/shadcn/dialog';
import { useUserAPIKeyStore } from '@/store/user-api-key-store';
import InputCopy from '../shadcn/input-copy';

const UserAPIKeySaveDialog = ({
  open,
  onOpenChange,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) => {
  const newKey = useUserAPIKeyStore((state) => state.apiKeys.at(-1)?.secretKey);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <form>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Save your key</DialogTitle>
              <DialogDescription>
                Please save your secret key in a safe place since you won't be
                able to view it again. Keep it secure, as anyone with your API
                key can make requests on your behalf. If you do lose it, you'll
                need to generate a new one.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4">
              <div className="grid gap-3">
                <InputCopy copiedValue={newKey ?? ''} />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Done</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </form>
      </Dialog>
    </>
  );
};

export { UserAPIKeySaveDialog };
