import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";

/** Positive state shown when the track already matches the reference. */
export function EmptyState() {
  const { t } = useTranslation();

  return (
    <Card role="status" className="border-sage/30 bg-sage/5">
      <CardContent className="flex flex-col items-center gap-2 p-6 text-center">
        <div
          aria-hidden="true"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-sage text-lg text-washi"
        >
          {"\u2713"}
        </div>
        <h3 className="font-display text-lg font-semibold text-sumi">{t("empty_state.title")}</h3>
        <p className="font-body text-sm text-sumi-soft">{t("empty_state.body")}</p>
      </CardContent>
    </Card>
  );
}
