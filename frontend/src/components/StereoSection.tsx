import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="font-display text-lg">{t("stereo.section_title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {!stereo ? (
          <p className="font-body text-sm text-sumi-soft">{t("stereo.no_stereo")}</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="font-mono text-[10px] uppercase tracking-wider text-sumi-outline">
                    {t("stereo.col_metric")}
                  </TableHead>
                  <TableHead className="text-right font-mono text-[10px] uppercase tracking-wider text-sumi-outline">
                    {t("stereo.col_delta")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableHead scope="row" className="font-body font-medium">
                    {t("stereo.metric_correlation")}
                  </TableHead>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatNumber(stereo.overall_correlation_delta, 2)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableHead scope="row" className="font-body font-medium">
                    {t("stereo.metric_side_mid")}
                  </TableHead>
                  <TableCell className="text-right font-mono tabular-nums">
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
