import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
  type DotProps,
} from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatFrequencyTick, nearestBandIndex } from "@/lib/format";
import type { BandDelta } from "@/types";

/** Lowest dB value the chart is allowed to display. */
const CHART_FLOOR_DB = -60;

/** Frequencies that receive an explicit X-axis tick. */
const TICK_FREQUENCIES_HZ = [100, 1000, 10000] as const;

/** Line colours; reused by the highlighted dots so fill and stroke match. */
const CHART_USER_COLOR = "hsl(var(--chart-user))";
const CHART_REFERENCE_COLOR = "hsl(var(--chart-reference))";

/** Radius of the dot drawn on the highlighted band. */
const HIGHLIGHT_DOT_RADIUS = 6;

const chartConfig = {
  user_db: {
    label: "La tua traccia",
    color: CHART_USER_COLOR,
  },
  reference_db: {
    label: "Reference",
    color: CHART_REFERENCE_COLOR,
  },
} satisfies ChartConfig;

interface SpectrumChartProps {
  /** Third-octave band comparison produced by the API. */
  bands: BandDelta[];
  /**
   * Centre frequency of the band to highlight, or `null` for no highlight.
   *
   * Assumption: `freq_hz` is unique within `bands` (they are ISO third-octave
   * centre frequencies), so a single frequency identifies a single band.
   */
  highlightedFreqHz?: number | null;
  /** Whether the highlight is pinned by a click instead of hover-only. */
  isPinned?: boolean;
}

interface ChartRow {
  index: number;
  user_db: number;
  reference_db: number;
  floor: number;
  ceiling: number;
}

/** Props Recharts hands to a custom `dot` renderer; `index` is added at runtime. */
type HighlightDotProps = DotProps & {
  index?: number;
  key?: string | number;
};

/**
 * Build the `dot` renderer used by both lines.
 *
 * Only the point sitting on `highlightedIndex` is drawn; every other point gets
 * `r=0`, which keeps the chart visually identical to `dot={false}`.
 */
function createHighlightDot(highlightedIndex: number, color: string) {
  return function HighlightDot({ cx, cy, index, key }: HighlightDotProps) {
    if (index !== highlightedIndex || typeof cx !== "number" || typeof cy !== "number") {
      return <circle key={key} cx={cx} cy={cy} r={0} fill="none" stroke="none" />;
    }
    return (
      <circle
        key={key}
        cx={cx}
        cy={cy}
        r={HIGHLIGHT_DOT_RADIUS}
        fill={color}
        stroke="#fff"
        strokeWidth={2}
      />
    );
  };
}

/** Text colour matching a band severity. */
function severityTextClass(severity: BandDelta["severity"]): string {
  if (severity === "major") {
    return "text-red-600 dark:text-red-400";
  }
  if (severity === "minor") {
    return "text-amber-600 dark:text-amber-400";
  }
  return "text-emerald-600 dark:text-emerald-400";
}

interface HighlightedBandTooltipProps {
  /** Band currently highlighted from the table, captured by closure. */
  band: BandDelta;
  /** Injected by Recharts: `true` while the pointer is over the chart. */
  active?: boolean;
}

/** Tooltip shown only while a band is highlighted; otherwise no tooltip. */
function HighlightedBandTooltip({ band, active }: HighlightedBandTooltipProps) {
  if (!active) {
    return null;
  }

  return (
    <div className="grid gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <span className="font-medium">{formatFrequencyTick(band.freq_hz)} Hz</span>
      <span className="flex items-center justify-between gap-4 text-muted-foreground">
        La tua traccia
        <span className="font-mono font-medium tabular-nums text-foreground">
          {band.user_db.toFixed(1)} dB
        </span>
      </span>
      <span className="flex items-center justify-between gap-4 text-muted-foreground">
        Reference
        <span className="font-mono font-medium tabular-nums text-foreground">
          {band.reference_db.toFixed(1)} dB
        </span>
      </span>
      <span
        className={`flex items-center justify-between gap-4 font-medium ${severityTextClass(band.severity)}`}
      >
        Delta
        <span className="font-mono tabular-nums">{band.delta_db.toFixed(1)} dB</span>
      </span>
    </div>
  );
}

/**
 * Spectral balance chart: user track in blue, reference in dashed grey.
 *
 * The X axis is plotted by band *index* rather than by frequency, so the highly
 * uneven third-octave spacing stays readable. The Y axis floor is clamped at
 * -60 dB; values below it are clamped instead of compressing the whole axis.
 *
 * When `highlightedFreqHz` matches a band, a vertical reference line and one
 * dot per series mark that band. `isPinned` only affects how strong the marker
 * is; the selection itself is owned by `SpectrumSection`.
 */
export function SpectrumChart({
  bands,
  highlightedFreqHz = null,
  isPinned = false,
}: SpectrumChartProps) {
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

  const highlightedIndex =
    highlightedFreqHz === null
      ? -1
      : bands.findIndex((band) => band.freq_hz === highlightedFreqHz);
  const highlighted = highlightedIndex >= 0 ? bands[highlightedIndex] : undefined;

  const referenceDot = createHighlightDot(highlightedIndex, CHART_REFERENCE_COLOR);
  const userDot = createHighlightDot(highlightedIndex, CHART_USER_COLOR);

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
        {highlighted && (
          <ReferenceLine
            x={highlightedIndex}
            stroke="hsl(var(--foreground))"
            strokeDasharray="4 4"
            strokeOpacity={isPinned ? 0.8 : 0.4}
            strokeWidth={isPinned ? 1.5 : 1}
            ifOverflow="extendDomain"
          />
        )}
        {highlighted && (
          <ChartTooltip
            cursor={false}
            content={<HighlightedBandTooltip band={highlighted} />}
          />
        )}
        <Line
          type="linear"
          dataKey="reference_db"
          stroke="var(--color-reference_db)"
          strokeWidth={2}
          strokeDasharray="4 2"
          dot={referenceDot}
          isAnimationActive={false}
        />
        <Line
          type="linear"
          dataKey="user_db"
          stroke="var(--color-user_db)"
          strokeWidth={2}
          dot={userDot}
          isAnimationActive={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
