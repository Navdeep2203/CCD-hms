import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message, tone = "success") => {
      const id = nextId.current++;

      setToasts((current) => [
        ...current,
        {
          id,
          message,
          tone: tone === "error" ? "error" : "success",
        },
      ]);

      window.setTimeout(() => {
        dismiss(id);
      }, 4000);

      return id;
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}

      <div className="toastStack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.tone}`} role="status">
            <span>{toast.message}</span>

            <button
              type="button"
              className="toastClose"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }

  return context;
}
