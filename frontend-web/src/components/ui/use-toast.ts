import * as React from "react";

export type ToastProps = {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  variant?: "default" | "destructive" | "success";
};

type State = {
  toasts: ToastProps[];
};

type Action =
  | { type: "ADD_TOAST"; toast: ToastProps }
  | { type: "DISMISS_TOAST"; toastId?: string };

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

let memoryState: State = { toasts: [] };
let listeners: Array<(state: State) => void> = [];

function dispatch(action: Action) {
  switch (action.type) {
    case "ADD_TOAST":
      memoryState = {
        toasts: [action.toast, ...memoryState.toasts].slice(0, 3),
      };
      break;
    case "DISMISS_TOAST":
      memoryState = {
        toasts: memoryState.toasts.filter((t) => t.id !== action.toastId),
      };
      break;
  }
  listeners.forEach((listener) => listener(memoryState));
}

export function toast({
  title,
  description,
  variant = "default",
}: Omit<ToastProps, "id">) {
  const id = Math.random().toString(36).substring(2, 9);

  dispatch({
    type: "ADD_TOAST",
    toast: { id, title, description, variant },
  });

  const timeout = setTimeout(() => {
    dispatch({ type: "DISMISS_TOAST", toastId: id });
    toastTimeouts.delete(id);
  }, 4000);

  toastTimeouts.set(id, timeout);
}

export function useToast() {
  const [state, setState] = React.useState<State>(memoryState);

  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      listeners = listeners.filter((l) => l !== setState);
    };
  }, []);

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => dispatch({ type: "DISMISS_TOAST", toastId }),
  };
}

