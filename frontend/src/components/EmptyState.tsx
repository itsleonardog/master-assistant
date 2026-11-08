import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";

/** Positive state shown when the track already matches the reference. */
export function EmptyState() {
  const { t } = useTranslation();

  return (
    <Card
      role="status"
      className="border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"
    >
      <CardContent className="flex flex-col items-center gap-2 p-6 text-center">
        <div
          aria-hidden="true"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-600 text-lg text-white"
        >
          {"\u2713"}
        </div>
        <h3 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">
          {t("empty_state.title")}
        </h3>
        <p className="text-sm text-emerald-800 dark:text-emerald-200">
          {t("empty_state.body")}
        </p>
      </CardContent>
    </Card>
  );
}
