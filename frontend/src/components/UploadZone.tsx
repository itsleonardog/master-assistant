import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent, KeyboardEvent, MouseEvent } from "react";

import { cn } from "@/lib/utils";

interface UploadZoneProps {
  /** Receives the dropped or picked files, whatever their count. */
  onFilesSelected: (files: File[]) => void;
}

/**
 * Drag & drop area doubling as a file picker.
 *
 * The hidden input is nested inside the zone, so its programmatic click is
 * stopped from bubbling back and reopening the picker recursively.
 */
export function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function openPicker() {
    inputRef.current?.click();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    const files = Array.from(event.dataTransfer?.files ?? []);
    if (files.length === 0) {
      return;
    }
    onFilesSelected(files);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    onFilesSelected(files);
    // Reset so selecting the same file again still fires a change event.
    event.target.value = "";
  }

  function handleInputClick(event: MouseEvent<HTMLInputElement>) {
    // Prevent the click from bubbling to the zone and reopening the picker.
    event.stopPropagation();
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Trascina qui i tuoi file audio oppure clicca per selezionarli"
      onClick={openPicker}
      onKeyDown={handleKeyDown}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-muted/20 px-6 py-12 text-center transition-colors",
        "hover:border-primary/40 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        dragOver && "border-primary bg-primary/5",
      )}
    >
      <p className="text-base font-medium">Trascina qui i tuoi file audio</p>
      <p className="text-sm text-muted-foreground">oppure clicca per selezionare</p>
      <p className="text-xs text-muted-foreground">
        1 file → la tua traccia · 2 file → la tua traccia + reference
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,.wav,.flac,.aiff"
        multiple
        hidden
        onChange={handleInputChange}
        onClick={handleInputClick}
      />
    </div>
  );
}
