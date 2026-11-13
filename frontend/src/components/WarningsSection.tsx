import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface WarningsSectionProps {
  /** Non-fatal caveats reported by the API. */
  warnings: string[];
}

/** List of analysis warnings; renders nothing when there are none. */
export function WarningsSection({ warnings }: WarningsSectionProps) {
  const { t } = useTranslation();

  if (warnings.length === 0) {
    return null;
  }

  return (
    <Card className="border-sumi-hairline">
      <CardHeader className="pb-3">
        <CardTitle className="font-display text-lg text-sumi">
          {t("warnings.section_title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="list-inside list-disc space-y-1 font-body text-sm text-sumi-soft">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
