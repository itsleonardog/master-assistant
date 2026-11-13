import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Suggestion, SuggestionSeverity } from "@/types";

/** Circular priority badge colours per severity. */
const SEVERITY_CLASSES: Record<SuggestionSeverity, string> = {
  critical: "bg-vermilion text-washi",
  major: "bg-amber text-washi",
  minor: "bg-sage text-washi",
  info: "bg-sumi-outline text-washi",
};

interface SuggestionCardProps {
  suggestion: Suggestion;
  /** DAW-ready text for the same suggestion, at the same index. */
  rendered: string;
}

/** One structured suggestion with its DAW-specific instruction. */
export function SuggestionCard({ suggestion, rendered }: SuggestionCardProps) {
  const { t } = useTranslation();
  const severity = suggestion.severity ?? "info";

  return (
    <Card>
      <CardContent className="flex gap-4 p-4">
        <div
          aria-label={t("suggestions.priority_aria", {
            priority: suggestion.priority,
            severity,
          })}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-mono text-sm font-semibold",
            SEVERITY_CLASSES[severity],
          )}
        >
          P{suggestion.priority}
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          <h4 className="font-body text-base font-semibold leading-tight">{suggestion.title}</h4>

          <div className="rounded-md bg-washi-container px-3 py-2">
            <span className="font-mono text-xs font-medium uppercase tracking-wide text-sumi-outline">
              {t("suggestions.in_daw")}
            </span>
            <p className="mt-1 break-words font-mono text-sm text-sumi">
              {rendered || "\u2014"}
            </p>
          </div>

          <p className="font-body text-xs text-sumi-soft">{suggestion.explanation}</p>
        </div>
      </CardContent>
    </Card>
  );
}
