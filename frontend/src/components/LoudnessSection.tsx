import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  LRA_DELTA_THRESHOLD_DB,
  LUFS_DELTA_THRESHOLD_DB,
  TRUE_PEAK_DELTA_THRESHOLD_DB,
  deltaColorClass,
  formatNumber,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ComparisonReport } from "@/types";

interface LoudnessRow {
  label: string;
  user: number;
  reference: number;
  delta: number;
  threshold: number;
}

interface LoudnessSectionProps {
  report: ComparisonReport;
}

/** Loudness summary with colour-coded deltas. */
export function LoudnessSection({ report }: LoudnessSectionProps) {
  const rows: LoudnessRow[] = [
    {
      label: "Integrated LUFS",
      user: report.user_loudness.integrated_lufs,
      reference: report.reference_loudness.integrated_lufs,
      delta: report.loudness_delta.integrated_lufs_delta,
      threshold: LUFS_DELTA_THRESHOLD_DB,
    },
    {
      label: "True Peak (dBTP)",
      user: report.user_loudness.true_peak_dbtp,
      reference: report.reference_loudness.true_peak_dbtp,
      delta: report.loudness_delta.true_peak_dbtp_delta,
      threshold: TRUE_PEAK_DELTA_THRESHOLD_DB,
    },
    {
      label: "Loudness Range (LU)",
      user: report.user_loudness.loudness_range_lu,
      reference: report.reference_loudness.loudness_range_lu,
      delta: report.loudness_delta.loudness_range_lu_delta,
      threshold: LRA_DELTA_THRESHOLD_DB,
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Sintesi loudness</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Metrica</TableHead>
              <TableHead className="text-right">User</TableHead>
              <TableHead className="text-right">Reference</TableHead>
              <TableHead className="text-right">Delta</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.label}>
                <TableHead scope="row" className="font-medium">
                  {row.label}
                </TableHead>
                <TableCell className="text-right tabular-nums">
                  {formatNumber(row.user, 1)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatNumber(row.reference, 1)}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right font-medium tabular-nums",
                    deltaColorClass(row.delta, row.threshold),
                  )}
                >
                  {formatNumber(row.delta, 1)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
