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

/** Spectral chart plus the table of bands whose severity is not `ok`. */
export function SpectrumSection({ bands }: SpectrumSectionProps) {
  const problems = bands.filter((band) => band.severity !== "ok");

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Spettro</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {bands.length === 0 ? (
          <p className="text-sm text-muted-foreground">Dati spettrali non disponibili.</p>
        ) : (
          <SpectrumChart bands={bands} />
        )}

        {problems.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuno squilibrio tonale rilevato.</p>
        ) : (
          <div className="overflow-x-auto">
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
                  <TableRow key={`${band.name}-${band.freq_hz}`}>
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
        )}
      </CardContent>
    </Card>
  );
}
