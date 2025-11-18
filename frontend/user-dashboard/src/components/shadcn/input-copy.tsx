import { CheckIcon, CopyIcon } from 'lucide-react';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
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
        <InputGroupButton
          aria-label="Copy"
          size="icon-xs"
          onClick={() => copy(value)}
        >
          {isCopied ? <CheckIcon /> : <CopyIcon />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
  );
};

export default InputCopy;
