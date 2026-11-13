import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

interface LoadingStatusProps {
  /** When `true`, an indeterminate progress bar replaces any message. */
  loading: boolean;
  /** Status or error message; an empty string hides the element. */
  message: string;
  /** Whether `message` is an error. */
  isError: boolean;
}

/** Live region for progress and result/error feedback. */
export function LoadingStatus({ loading, message, isError }: LoadingStatusProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="space-y-2" role="status" aria-live="polite">
        <p className="font-body text-sm text-sumi-soft">{t("analyzer.status_loading")}</p>
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
        </div>
      </div>
    );
  }

  if (!message) {
    return null;
  }

  return (
    <p
      role="status"
      aria-live="polite"
      className={cn("font-body text-sm", isError ? "text-vermilion" : "text-sage")}
    >
      {message}
    </p>
  );
}
