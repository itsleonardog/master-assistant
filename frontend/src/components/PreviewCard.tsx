import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatBytes, formatDuration, isAudioFile } from "@/lib/format";
import { cn } from "@/lib/utils";

interface PreviewCardProps {
  /** Slot heading, for example "La tua traccia". */
  label: string;
  /** File held by the slot, or `null` when empty. */
  file: File | null;
  /** Duration in seconds; `null` while metadata loads, `0` when unreadable. */
  duration: number | null;
  /** Clears the slot. */
  onRemove: () => void;
}

/**
 * Preview of one upload slot.
 *
 * The border turns red and an inline message appears when the extension is not
 * one the backend can decode.
 */
export function PreviewCard({ label, file, duration, onRemove }: PreviewCardProps) {
  const { t } = useTranslation();

  if (!file) {
    return (
      <Card className="border-dashed bg-muted/20">
        <CardContent className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">{t("preview.no_file")}</p>
        </CardContent>
      </Card>
    );
  }

  const valid = isAudioFile(file);
  const durationText = valid ? formatDuration(duration) : "\u2014";

  return (
    <Card className={cn(valid ? "border-sage" : "border-vermilion bg-vermilion-soft/30")}>
      <CardContent className="p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>

        <p className="mt-2 flex items-center gap-2 text-sm font-medium">
          <span
            aria-hidden="true"
            className={cn(
              "inline-flex h-5 w-5 items-center justify-center rounded-full text-xs leading-none",
              valid ? "bg-sage text-washi" : "bg-vermilion text-washi",
            )}
          >
            {valid ? "\u2713" : "\u2717"}
          </span>
          <span className="truncate font-mono" title={file.name}>
            {file.name}
          </span>
        </p>

        <p className="mt-1 font-mono text-xs text-sumi-outline">
          {formatBytes(file.size)} · {durationText}
        </p>

        {!valid && (
          <p className="mt-2 text-xs text-vermilion">{t("preview.unsupported_format")}</p>
        )}

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="mt-3"
          aria-label={t("preview.remove_aria", { name: file.name })}
          onClick={onRemove}
        >
          {t("preview.remove")}
        </Button>
      </CardContent>
    </Card>
  );
}
