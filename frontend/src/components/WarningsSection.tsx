import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface WarningsSectionProps {
  /** Non-fatal caveats reported by the API. */
  warnings: string[];
}

/** List of analysis warnings; renders nothing when there are none. */
export function WarningsSection({ warnings }: WarningsSectionProps) {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-amber-900 dark:text-amber-100">Warning</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="list-inside list-disc space-y-1 text-sm text-amber-900 dark:text-amber-100">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
