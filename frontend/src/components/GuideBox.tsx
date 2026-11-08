import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** "Come procedere" workflow reminder, shown only when suggestions exist. */
export function GuideBox() {
  const { t } = useTranslation();

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{t("guide.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
          <li>{t("guide.step1")}</li>
          <li>{t("guide.step2")}</li>
          <li>{t("guide.step3")}</li>
        </ol>
      </CardContent>
    </Card>
  );
}
