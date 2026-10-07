import { useCallback, useState } from "react";
import { useToast } from "../components/Toast";

export function useAction(action) {
  const { notify } = useToast();
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async (...args) => {
      setBusy(true);

      try {
        return await action(...args);
      } catch (error) {
        notify(error?.message || "Something went wrong", "error");

        throw error;
      } finally {
        setBusy(false);
      }
    },
    [action, notify],
  );

  return {
    run,
    busy,
  };
}
