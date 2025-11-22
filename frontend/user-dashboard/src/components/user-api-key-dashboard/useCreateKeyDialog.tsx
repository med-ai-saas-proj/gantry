import { type ReactNode, useState } from 'react';
import { Button } from '../shadcn/button';

export type TriggerProps = {
  children?: ReactNode;
  className?: string;
};

export function useCreateKeyDialog() {
  const [open, setOpen] = useState(false);

  function Trigger({ children, className }: TriggerProps) {
    return (
      <Button className={className} onClick={() => setOpen(true)}>
        {children}
      </Button>
    );
  }

  return { open, setOpen, Trigger } as const;
}

export default useCreateKeyDialog;
