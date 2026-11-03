import type { Suggestion } from "@/types";

import { EmptyState } from "./EmptyState";
import { SuggestionCard } from "./SuggestionCard";

interface SuggestionsSectionProps {
  /** DAW-agnostic suggestions, in API order. */
  suggestions: Suggestion[];
  /** DAW-rendered texts, index-aligned with `suggestions`. */
  rendered: string[];
}

/** Suggestion cards ordered by ascending priority. */
export function SuggestionsSection({ suggestions, rendered }: SuggestionsSectionProps) {
  const ordered = suggestions
    .map((suggestion, index) => ({ suggestion, rendered: rendered[index] ?? "" }))
    .sort((a, b) => (a.suggestion.priority || 0) - (b.suggestion.priority || 0));

  if (ordered.length === 0) {
    return <EmptyState />;
  }

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">Suggerimenti</h3>
      <div className="space-y-3">
        {ordered.map((entry) => (
          <SuggestionCard
            key={entry.suggestion.id}
            suggestion={entry.suggestion}
            rendered={entry.rendered}
          />
        ))}
      </div>
    </section>
  );
}
