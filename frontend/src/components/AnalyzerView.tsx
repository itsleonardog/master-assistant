import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Controls } from "@/components/Controls";
import { EmptyState } from "@/components/EmptyState";
import { GuideBox } from "@/components/GuideBox";
import { Header } from "@/components/Header";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { LoadingStatus } from "@/components/LoadingStatus";
import { LoudnessSection } from "@/components/LoudnessSection";
import { PreviewCard } from "@/components/PreviewCard";
import { SpectrumSection } from "@/components/SpectrumSection";
import { StereoSection } from "@/components/StereoSection";
import { SuggestionsSection } from "@/components/SuggestionsSection";
import { UploadZone } from "@/components/UploadZone";
import { WarningsSection } from "@/components/WarningsSection";
import { useAudioDuration } from "@/hooks/useAudioDuration";
import i18n from "@/i18n";
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
  const { t } = useTranslation();
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
      window.alert(t("analyzer.too_many_files"));
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

  /** Translate a failed request into the status message for the active locale. */
  function resolveErrorMessage(error: unknown): string {
    if (!(error instanceof ApiError)) {
      return t("analyzer.status_network_error", { error: String(error) });
    }
    switch (error.kind) {
      case "timeout":
        return t("analyzer.status_timeout");
      case "validation":
        return t("analyzer.status_validation_error");
      case "network":
        return t("analyzer.status_network_error", { error: error.message });
      case "unknown":
        return t("analyzer.status_unknown_error");
      case "server":
      default:
        return error.message;
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) {
      return;
    }
    if (!userFile || !referenceFile || !ready) {
      setStatus({ message: t("analyzer.status_select_both"), isError: true });
      return;
    }

    setLoading(true);
    setResult(null);
    setStatus(EMPTY_STATUS);

    try {
      const payload = await analyzeFiles({
        userFile,
        referenceFile,
        daw,
        lang: i18n.language === "en" ? "en" : "it",
      });
      setResult(payload);
      setStatus({ message: t("analyzer.status_done"), isError: false });
    } catch (error) {
      setStatus({ message: resolveErrorMessage(error), isError: true });
    } finally {
      setLoading(false);
    }
  }

  const hasAnyFile = !!(userFile || referenceFile);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6 sm:py-12">
      <div className="mb-4 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          {t("analyzer.back_home")}
        </button>
        <LanguageSwitcher />
      </div>

      <Header />

      <main className="flex flex-col gap-6">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <UploadZone onFilesSelected={assignFiles} />

          {hasAnyFile && (
            <div className="grid gap-3 sm:grid-cols-2">
              <PreviewCard
                label={t("preview.label_user")}
                file={userFile}
                duration={userDuration}
                onRemove={() => setUserFile(null)}
              />
              <PreviewCard
                label={t("preview.label_reference")}
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
        {t("analyzer.footer_note")}
      </footer>
    </div>
  );
}
