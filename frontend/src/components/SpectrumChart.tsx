import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatFrequencyTick, nearestBandIndex } from "@/lib/format";
import type { BandDelta } from "@/types";

/** Lowest dB value the chart is allowed to display. */
const CHART_FLOOR_DB = -60;

/** Frequencies that receive an explicit X-axis tick. */
const TICK_FREQUENCIES_HZ = [100, 1000, 10000] as const;

const chartConfig = {
  user_db: {
    label: "La tua traccia",
    color: "hsl(var(--chart-user))",
  },
  reference_db: {
    label: "Reference",
    color: "hsl(var(--chart-reference))",
  },
} satisfies ChartConfig;

interface SpectrumChartProps {
  /** Third-octave band comparison produced by the API. */
  bands: BandDelta[];
}

interface ChartRow {
  index: number;
  user_db: number;
  reference_db: number;
  floor: number;
  ceiling: number;
}

/**
 * Spectral balance chart: user track in blue, reference in dashed grey.
 *
 * The X axis is plotted by band *index* rather than by frequency, so the highly
 * uneven third-octave spacing stays readable. The Y axis floor is clamped at
 * -60 dB; values below it are clamped instead of compressing the whole axis.
 */
export function SpectrumChart({ bands }: SpectrumChartProps) {
  const rows = useMemo<ChartRow[]>(() => {
    const values = bands
      .flatMap((band) => [band.user_db, band.reference_db])
      .filter((value) => Number.isFinite(value));
    if (values.length === 0) {
      return [];
    }

    const rawMin = Math.min(...values);
    const rawMax = Math.max(...values);
    const floor = Math.max(CHART_FLOOR_DB, rawMin - 5);
    const ceiling = Math.max(rawMax + 5, floor + 10);

    return bands.map((band, index) => ({
      index,
      user_db: Math.max(floor, band.user_db),
      reference_db: Math.max(floor, band.reference_db),
      floor,
      ceiling,
    }));
  }, [bands]);

  const ticks = useMemo(() => {
    const indexes = TICK_FREQUENCIES_HZ.map((freq) => nearestBandIndex(bands, freq));
    return Array.from(new Set(indexes)).sort((a, b) => a - b);
  }, [bands]);

  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Dati spettrali non disponibili.</p>;
  }

  const floor = rows[0].floor;
  const ceiling = rows[0].ceiling;
  const maxIndex = Math.max(rows.length - 1, 1);

  return (
    <ChartContainer config={chartConfig} className="aspect-auto h-[300px] w-full">
      <LineChart data={rows} margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical horizontal />
        <XAxis
          dataKey="index"
          type="number"
          domain={[0, maxIndex]}
          ticks={ticks}
          tickLine={false}
          axisLine
          tickFormatter={(value: number) => {
            const band = bands[value];
            return band ? formatFrequencyTick(band.freq_hz) : "";
          }}
        />
        <YAxis
          domain={[floor, ceiling]}
          width={56}
          tickLine={false}
          axisLine
          tickFormatter={(value: number) => `${Math.round(value)} dB`}
        />
        <ChartLegend content={<ChartLegendContent />} />
        <Line
          type="linear"
          dataKey="reference_db"
          stroke="var(--color-reference_db)"
          strokeWidth={2}
          strokeDasharray="4 2"
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="linear"
          dataKey="user_db"
          stroke="var(--color-user_db)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
