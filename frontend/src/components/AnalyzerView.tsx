import { useState } from "react";
import type { FormEvent } from "react";

import { Controls } from "@/components/Controls";
import { EmptyState } from "@/components/EmptyState";
import { GuideBox } from "@/components/GuideBox";
import { Header } from "@/components/Header";
import { LoadingStatus } from "@/components/LoadingStatus";
import { LoudnessSection } from "@/components/LoudnessSection";
import { PreviewCard } from "@/components/PreviewCard";
import { SpectrumSection } from "@/components/SpectrumSection";
import { StereoSection } from "@/components/StereoSection";
import { SuggestionsSection } from "@/components/SuggestionsSection";
import { UploadZone } from "@/components/UploadZone";
import { WarningsSection } from "@/components/WarningsSection";
import { useAudioDuration } from "@/hooks/useAudioDuration";
import { ApiError, analyzeFiles } from "@/lib/api";
import { isAudioFile } from "@/lib/format";
import type { AnalysisResponse } from "@/types";

interface Status {
  message: string;
  isError: boolean;
}

const EMPTY_STATUS: Status = { message: "", isError: false };

interface AnalyzerViewProps {
  onBack: () => void;
}

/**
 * Application shell: owns the upload slots, the request lifecycle, and the
 * composition of the result sections.
 */
export function AnalyzerView({ onBack }: AnalyzerViewProps) {
  const [userFile, setUserFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [daw, setDaw] = useState("ableton");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<Status>(EMPTY_STATUS);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const userDuration = useAudioDuration(userFile);
  const referenceDuration = useAudioDuration(referenceFile);

  const ready = isAudioFile(userFile) && isAudioFile(referenceFile);

  /**
   * Assign dropped or picked files to the slots.
   *
   * Two files fill both slots; one file fills the first free slot (falling back
   * to the user slot when both are taken); more than two are rejected.
   */
  function assignFiles(files: File[]) {
    if (files.length === 0) {
      return;
    }
    if (files.length > 2) {
      window.alert("Trascina 1 o 2 file");
      return;
    }
    if (files.length === 2) {
      setUserFile(files[0]);
      setReferenceFile(files[1]);
      return;
    }

    const [file] = files;
    if (!userFile) {
      setUserFile(file);
    } else if (!referenceFile) {
      setReferenceFile(file);
    } else {
      setUserFile(file);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) {
      return;
    }
    if (!userFile || !referenceFile || !ready) {
      setStatus({ message: "Seleziona due file audio validi prima di analizzare.", isError: true });
      return;
    }

    setLoading(true);
    setResult(null);
    setStatus(EMPTY_STATUS);

    try {
      const payload = await analyzeFiles({ userFile, referenceFile, daw });
      setResult(payload);
      setStatus({ message: "Analisi completata.", isError: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : `Impossibile contattare il server: ${String(error)}`;
      setStatus({ message, isError: true });
    } finally {
      setLoading(false);
    }
  }

  const hasAnyFile = !!(userFile || referenceFile);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6 sm:py-12">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        ← Home
      </button>

      <Header />

      <main className="flex flex-col gap-6">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <UploadZone onFilesSelected={assignFiles} />

          {hasAnyFile && (
            <div className="grid gap-3 sm:grid-cols-2">
              <PreviewCard
                label="La tua traccia"
                file={userFile}
                duration={userDuration}
                onRemove={() => setUserFile(null)}
              />
              <PreviewCard
                label="Reference"
                file={referenceFile}
                duration={referenceDuration}
                onRemove={() => setReferenceFile(null)}
              />
            </div>
          )}

          <Controls
            daw={daw}
            onDawChange={setDaw}
            loading={loading}
            canSubmit={ready}
          />
        </form>

        <LoadingStatus loading={loading} message={status.message} isError={status.isError} />

        {result && (
          <div className="space-y-6">
            {result.suggestions.length > 0 && <GuideBox />}
            <LoudnessSection report={result.report} />
            <SpectrumSection bands={result.report.spectrum?.bands ?? []} />
            <StereoSection stereo={result.report.stereo} />
            {result.suggestions.length > 0 ? (
              <SuggestionsSection
                suggestions={result.suggestions}
                rendered={result.rendered_suggestions}
              />
            ) : (
              <EmptyState />
            )}
            <WarningsSection warnings={result.report.warnings ?? []} />
          </div>
        )}
      </main>

      <footer className="mt-auto pt-4 text-center text-xs text-muted-foreground sm:text-left">
        I file vengono elaborati in memoria e cancellati subito.
      </footer>
    </div>
  );
}
