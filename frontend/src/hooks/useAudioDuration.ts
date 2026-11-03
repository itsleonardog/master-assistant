import { useEffect, useState } from "react";

/**
 * Read the duration of an audio file through the `<audio>` element.
 *
 * Resolves to `0` when the browser cannot decode the metadata (for example FLAC
 * on Safari, or a corrupted file); callers render an em dash for that value.
 * The object URL is revoked when the file changes and on unmount.
 *
 * @param file Audio file, or `null` when the slot is empty.
 * @returns Duration in seconds, `0` when unreadable, or `null` while loading.
 */
export function useAudioDuration(file: File | null): number | null {
  const [duration, setDuration] = useState<number | null>(null);

  useEffect(() => {
    if (!file) {
      setDuration(null);
      return;
    }

    let objectUrl: string | null = null;
    let settled = false;
    const audio = new Audio();

    function cleanup() {
      audio.removeEventListener("loadedmetadata", handleLoaded);
      audio.removeEventListener("error", handleError);
      audio.removeAttribute("src");
      audio.load();
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
    }

    function finish(seconds: number) {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      setDuration(seconds);
    }

    function handleLoaded() {
      const value = audio.duration;
      finish(typeof value === "number" && Number.isFinite(value) && value > 0 ? value : 0);
    }

    function handleError() {
      finish(0);
    }

    try {
      objectUrl = URL.createObjectURL(file);
    } catch {
      setDuration(0);
      return;
    }

    setDuration(null);
    audio.addEventListener("loadedmetadata", handleLoaded);
    audio.addEventListener("error", handleError);
    audio.preload = "metadata";
    audio.src = objectUrl;

    return () => {
      settled = true;
      cleanup();
    };
  }, [file]);

  return duration;
}
