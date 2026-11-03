import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Suggestion, SuggestionSeverity } from "@/types";

/** Circular priority badge colours per severity. */
const SEVERITY_CLASSES: Record<SuggestionSeverity, string> = {
  critical: "bg-red-600 text-white",
  major: "bg-orange-500 text-white",
  minor: "bg-yellow-400 text-yellow-950",
  info: "bg-zinc-400 text-white",
};

interface SuggestionCardProps {
  suggestion: Suggestion;
  /** DAW-ready text for the same suggestion, at the same index. */
  rendered: string;
}

/** One structured suggestion with its DAW-specific instruction. */
export function SuggestionCard({ suggestion, rendered }: SuggestionCardProps) {
  const severity = suggestion.severity ?? "info";

  return (
    <Card>
      <CardContent className="flex gap-4 p-4">
        <div
          aria-label={`Priorità ${suggestion.priority}, severità ${severity}`}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
            SEVERITY_CLASSES[severity],
          )}
        >
          P{suggestion.priority}
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          <h4 className="text-base font-semibold leading-tight">{suggestion.title}</h4>

          <div className="rounded-md bg-muted px-3 py-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              In Ableton:
            </span>
            <p className="mt-1 break-words font-mono text-sm">{rendered || "\u2014"}</p>
          </div>

          <p className="text-xs text-muted-foreground">{suggestion.explanation}</p>
        </div>
      </CardContent>
    </Card>
  );
}
