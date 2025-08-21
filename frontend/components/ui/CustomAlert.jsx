import { addToast, cn } from "@heroui/react";

export const Toast = {
  success: (title, description, options = {}) => {
    addToast({
      title: title || "¡Éxito!",
      description: description,
      timeout: 3000,
      shouldShowTimeoutProgress: true,
      classNames: {
        base: cn([
          "bg-default-50 dark:bg-background shadow-sm",
          "border border-l-8 rounded-md rounded-l-none",
          "flex flex-col items-start",
          "border-success-200 dark:border-success-100 border-l-success",
        ]),
        icon: "w-6 h-6 fill-current",
      },
      color: "success",
      ...options
    });
  },

  error: (title, description, options = {}) => {
    addToast({
      title: title || "Error",
      description: description,
      timeout: 3000,
      shouldShowTimeoutProgress: true,
      classNames: {
        base: cn([
          "bg-default-50 dark:bg-background shadow-sm",
          "border border-l-8 rounded-md rounded-l-none",
          "flex flex-col items-start",
          "border-danger-200 dark:border-danger-100 border-l-danger",
        ]),
        icon: "w-6 h-6 fill-current",
      },
      color: "danger",
      ...options
    });
  },

  warning: (title, description, options = {}) => {
    addToast({
      title: title || "Advertencia",
      description: description,
      timeout: 3000,
      shouldShowTimeoutProgress: true,
      classNames: {
        base: cn([
          "bg-default-50 dark:bg-background shadow-sm",
          "border border-l-8 rounded-md rounded-l-none",
          "flex flex-col items-start",
          "border-warning-200 dark:border-warning-100 border-l-warning",
        ]),
        icon: "w-6 h-6 fill-current",
      },
      color: "warning",
      ...options
    });
  },

  info: (title, description, options = {}) => {
    addToast({
      title: title || "Información",
      description: description,
      timeout: 3000,
      shouldShowTimeoutProgress: true,
      classNames: {
        base: cn([
          "bg-default-50 dark:bg-background shadow-sm",
          "border border-l-8 rounded-md rounded-l-none",
          "flex flex-col items-start",
          "border-primary-200 dark:border-primary-100 border-l-primary",
        ]),
        icon: "w-6 h-6 fill-current",
      },
      color: "primary",
      ...options
    });
  }
};

export default Toast;