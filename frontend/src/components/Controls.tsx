import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ControlsProps {
  /** Selected DAW identifier. */
  daw: string;
  onDawChange: (value: string) => void;
  /** While loading the select is disabled and the button shows a spinner. */
  loading: boolean;
  /** `false` until both slots hold a supported file. */
  canSubmit: boolean;
}

/** DAW picker plus the analyze button. */
export function Controls({ daw, onDawChange, loading, canSubmit }: ControlsProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="daw" className="text-sm font-medium">
          DAW
        </label>
        <Select value={daw} onValueChange={onDawChange} disabled={loading}>
          <SelectTrigger id="daw" className="w-full sm:w-[200px]">
            <SelectValue placeholder="Seleziona DAW" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ableton">Ableton Live</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button type="submit" disabled={!canSubmit || loading} className="sm:w-[200px]">
        {loading ? (
          <>
            <span
              aria-hidden="true"
              className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
            />
            Analisi in corso...
          </>
        ) : (
          "Analizza"
        )}
      </Button>
    </div>
  );
}
