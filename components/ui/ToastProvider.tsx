"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastType = "success" | "error" | "warning" | "info";

type Toast = {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
};

type ToastInput = Omit<Toast, "id">;

type ToastContextValue = {
  showToast: (toast: ToastInput) => void;
  dismissToast: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const toneByType: Record<ToastType, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  error: "border-rose-200 bg-rose-50 text-rose-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
};

const iconByType: Record<ToastType, string> = {
  success: "✓",
  error: "!",
  warning: "⚠",
  info: "i",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((toast: ToastInput) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((current) => [{ id, ...toast }, ...current].slice(0, 4));
    window.setTimeout(() => dismissToast(id), toast.type === "error" ? 6500 : 4200);
  }, [dismissToast]);

  const value = useMemo(() => ({ showToast, dismissToast }), [showToast, dismissToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[100] flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`rounded-2xl border p-4 shadow-[0_18px_60px_rgba(15,23,42,0.18)] backdrop-blur transition ${toneByType[toast.type]}`}
            role="status"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/80 text-xs font-black shadow-sm">
                {iconByType[toast.type]}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold">{toast.title}</p>
                {toast.message ? <p className="mt-1 text-xs font-medium opacity-80">{toast.message}</p> : null}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="rounded-lg px-2 py-1 text-xs font-bold opacity-60 transition hover:bg-white/60 hover:opacity-100"
                aria-label="Dismiss notification"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
