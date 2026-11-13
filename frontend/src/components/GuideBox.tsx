import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** "Come procedere" workflow reminder, shown only when suggestions exist. */
export function GuideBox() {
  const { t } = useTranslation();

  return (
    <Card className="border-l-4 border-vermilion bg-vermilion-soft">
      <CardHeader className="pb-3">
        <CardTitle className="font-display text-base text-sumi">{t("guide.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="list-inside list-decimal space-y-1 font-body text-sm text-sumi">
          <li>{t("guide.step1")}</li>
          <li>{t("guide.step2")}</li>
          <li>{t("guide.step3")}</li>
        </ol>
      </CardContent>
    </Card>
  );
}
