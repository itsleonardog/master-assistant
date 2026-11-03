import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BandDelta } from "@/types";

import { SpectrumChart } from "./SpectrumChart";

interface SpectrumSectionProps {
  /** Per-band comparison; may be empty when spectral data is unavailable. */
  bands: BandDelta[];
}

/**
 * Spectral chart plus the table of bands whose severity is not `ok`.
 *
 * The selection is keyed on `freq_hz`, never on the row index: the table only
 * lists the problematic bands, so `problems[i]` is not `bands[i]`. This assumes
 * `freq_hz` is unique within `bands`, which holds for ISO third-octave centre
 * frequencies.
 *
 * Hover and pin are two independent states: hover is a transient preview that
 * is cleared as soon as the pointer or focus leaves a row, while the pin is the
 * persistent selection toggled by click/Enter/Space and cleared by Esc or by a
 * click outside the chart and table. The chart highlights the hovered band when
 * there is one, otherwise the pinned band, so hovering another row never makes a
 * stale selection stick around.
 */
export function SpectrumSection({ bands }: SpectrumSectionProps) {
  const [hoveredFreqHz, setHoveredFreqHz] = useState<number | null>(null);
  const [pinnedFreqHz, setPinnedFreqHz] = useState<number | null>(null);

  const problems = bands.filter((band) => band.severity !== "ok");

  const highlightedFreqHz = hoveredFreqHz ?? pinnedFreqHz;
  const isPinned =
    pinnedFreqHz !== null && (hoveredFreqHz === null || hoveredFreqHz === pinnedFreqHz);

  /** Toggle the persistent selection; the transient hover is left untouched. */
  function togglePin(freqHz: number) {
    setPinnedFreqHz((current) => (current === freqHz ? null : freqHz));
  }

  // Esc unlocks the selection from anywhere on the page.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      setHoveredFreqHz(null);
      setPinnedFreqHz(null);
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // A click outside both the chart and the table clears the selection.
  useEffect(() => {
    function handleMouseDown(event: MouseEvent) {
      const target = event.target;
      if (target instanceof Element && target.closest("[data-spectrum-scope]")) {
        return;
      }
      setHoveredFreqHz(null);
      setPinnedFreqHz(null);
    }

    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  function rowClass(freqHz: number): string {
    const pinned = pinnedFreqHz === freqHz;
    const hovered = hoveredFreqHz === freqHz;
    return cn(
      "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      pinned && "bg-accent/60 ring-2 ring-primary",
      !pinned && hovered && "bg-accent/40 ring-1 ring-accent-foreground/20",
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Spettro</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {bands.length === 0 ? (
          <p className="text-sm text-muted-foreground">Dati spettrali non disponibili.</p>
        ) : (
          <div data-spectrum-scope="chart">
            <SpectrumChart
              bands={bands}
              highlightedFreqHz={highlightedFreqHz}
              isPinned={isPinned}
            />
          </div>
        )}

        {problems.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuno squilibrio tonale rilevato.</p>
        ) : (
          <div className="space-y-2">
            <p className="text-right text-xs text-muted-foreground">
              Passa il mouse per esplorare · Clicca per fissare · Esc per sbloccare
            </p>
            <div className="overflow-x-auto" data-spectrum-scope="table">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Banda (Hz)</TableHead>
                    <TableHead className="text-right">User (dB)</TableHead>
                    <TableHead className="text-right">Reference (dB)</TableHead>
                    <TableHead className="text-right">Delta (dB)</TableHead>
                    <TableHead>Severity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {problems.map((band) => (
                    <TableRow
                      key={`${band.name}-${band.freq_hz}`}
                      tabIndex={0}
                      aria-selected={pinnedFreqHz === band.freq_hz}
                      className={rowClass(band.freq_hz)}
                      onMouseEnter={() => setHoveredFreqHz(band.freq_hz)}
                      onMouseLeave={() => setHoveredFreqHz(null)}
                      onFocus={() => setHoveredFreqHz(band.freq_hz)}
                      onBlur={() => setHoveredFreqHz(null)}
                      onClick={() => togglePin(band.freq_hz)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          togglePin(band.freq_hz);
                        }
                      }}
                    >
                      <TableCell className="tabular-nums">{formatNumber(band.freq_hz, 0)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(band.user_db, 1)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(band.reference_db, 1)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-medium tabular-nums",
                          band.severity === "major"
                            ? "text-red-600 dark:text-red-400"
                            : "text-amber-600 dark:text-amber-400",
                        )}
                      >
                        {formatNumber(band.delta_db, 1)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{band.severity}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
