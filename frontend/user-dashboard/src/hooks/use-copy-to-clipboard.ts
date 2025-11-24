import * as React from 'react';

export function useCopyToClipboard({ timeout = 2000 } = {}) {
  const [isCopied, setIsCopied] = React.useState(false);

  const copy = React.useCallback(
    async (value: string) => {
      if (!navigator?.clipboard) return false;

      try {
        await navigator.clipboard.writeText(value);
        setIsCopied(true);

        setTimeout(() => setIsCopied(false), timeout);
        return true;
      } catch (err) {
        console.error('Failed to copy: ', err);
        return false;
      }
    },
    [timeout]
  );

  return { copy, isCopied };
}
