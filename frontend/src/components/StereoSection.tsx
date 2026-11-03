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
import type { StereoComparison } from "@/types";

interface StereoSectionProps {
  /** `null` when either file is mono, which makes mid/side metrics undefined. */
  stereo: StereoComparison | null;
}

/** Overall stereo deltas, or the mono fallback message. */
export function StereoSection({ stereo }: StereoSectionProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Stereo</CardTitle>
      </CardHeader>
      <CardContent>
        {!stereo ? (
          <p className="text-sm text-muted-foreground">
            Analisi stereo non disponibile (file mono).
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metrica</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableHead scope="row" className="font-medium">
                    Correlation media
                  </TableHead>
                  <TableCell className="text-right tabular-nums">
                    {formatNumber(stereo.overall_correlation_delta, 2)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableHead scope="row" className="font-medium">
                    Side/Mid medio (dB)
                  </TableHead>
                  <TableCell className="text-right tabular-nums">
                    {formatNumber(stereo.overall_side_to_mid_delta_db, 1)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
