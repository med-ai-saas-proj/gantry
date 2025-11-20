import { CheckIcon, CopyIcon } from 'lucide-react';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from '@/components/shadcn/input-group';
import { useCopyToClipboard } from '@/hooks/use-copy-to-clipboard';

export const title = 'Copy Button';

const InputCopy = ({ copiedValue }: { copiedValue: string }) => {
  const { copy, isCopied } = useCopyToClipboard();
  const value = copiedValue;

  return (
    <InputGroup className="w-full max-w-sm bg-background">
      <InputGroupInput value={value} readOnly />
      <InputGroupAddon align="inline-end">
        {isCopied ? <CheckIcon /> : <CopyIcon onClick={() => copy(value)} />}
      </InputGroupAddon>
    </InputGroup>
  );
};

export default InputCopy;
