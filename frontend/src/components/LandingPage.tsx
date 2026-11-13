import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

import { LanguageSwitcher } from "./LanguageSwitcher";

// TODO: replace with the actual repository URL before publishing.
const GITHUB_URL = "https://github.com/itsleonardog/master-assistant";

interface LandingPageProps {
  onEnterApp: () => void;
}

/** Translation keys of the four numbered steps, in display order. */
const STEP_KEYS = ["step1", "step2", "step3", "step4"] as const;

/**
 * Decorative hero markers. Deliberately non-quantitative: they describe the
 * project, they are not audio specs. Translation keys under "landing.*".
 */
const HERO_MARKER_KEYS = [
  "hero_marker_edu",
  "hero_marker_open_source",
  "hero_marker_reference",
] as const;

/** Sample rows of the instrument card. The analyzer computes the real ones. */
const SAMPLE_METRICS = [
  { label: "LUFS INT", value: "-14.1" },
  { label: "TRUE PEAK", value: "-0.8" },
  { label: "LRA", value: "9.2" },
] as const;

/**
 * Marketing landing page: explains the project mission and gates the analyzer
 * behind an explicit call to action. Owns no app state.
 */
export function LandingPage({ onEnterApp }: LandingPageProps) {
  const { t } = useTranslation();
  const currentYear = new Date().getFullYear();

  function scrollToMission() {
    document.getElementById("mission")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <main className="min-h-screen bg-washi text-sumi washi-grain font-body">
      <header className="sticky top-0 z-50 border-b border-sumi-hairline/40 bg-washi/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <span className="font-mono text-xs tracking-widest text-sumi">MASTER ASSISTANT</span>
          <LanguageSwitcher />
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-16 md:py-24">
        <div className="grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <span className="hanko-stamp inline-block px-2 py-0.5 font-mono text-[11px] font-medium tracking-widest">
              {t("landing.badge")}
            </span>
            <h1 className="mt-6 font-display text-4xl font-light leading-[1.1] tracking-tight md:text-6xl">
              {t("landing.headline")}
            </h1>
            <p className="mt-6 max-w-xl font-body text-lg text-sumi-soft">
              {t("landing.subheadline")}
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button
                size="lg"
                onClick={onEnterApp}
                className="bg-sumi text-washi shadow-none hover:bg-vermilion"
              >
                {t("landing.cta_primary")}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={scrollToMission}
                className="border-sumi-hairline bg-transparent text-sumi shadow-none hover:bg-washi-high hover:text-sumi"
              >
                {t("landing.cta_secondary")}
              </Button>
            </div>
            <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 border-t border-sumi-hairline/40 pt-4">
              {HERO_MARKER_KEYS.map((key) => (
                <li key={key} className="font-mono text-xs text-sumi-outline">
                  {t(`landing.${key}`)}
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-5">
            <div className="rounded border border-sumi-hairline bg-washi-container p-4">
              <span className="telemetry text-[10px] tracking-widest text-sumi-outline">
                {t("landing.sample_caption")}
              </span>
              <dl className="mt-4 space-y-2">
                {SAMPLE_METRICS.map((metric) => (
                  <div
                    key={metric.label}
                    className="flex items-baseline justify-between gap-4 font-mono text-sm"
                  >
                    <dt className="text-sumi-soft">{metric.label}</dt>
                    <dd className="text-sumi">{metric.value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 border-t border-sumi-hairline pt-3 font-mono text-[11px] leading-relaxed text-sumi-outline">
                {t("landing.sample_disclaimer")}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="mission" className="mx-auto max-w-3xl px-6 py-16">
        <h2 className="font-display text-3xl font-light md:text-4xl">
          {t("landing.mission_title")}
        </h2>
        <p className="mt-4 font-body text-base text-sumi-soft">{t("landing.mission_body")}</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded border border-sumi-hairline p-6">
            <h3 className="font-display text-xl">{t("landing.audience_title")}</h3>
            <p className="mt-2 font-body text-sm text-sumi-soft">{t("landing.audience_body")}</p>
          </div>
          <div className="rounded border border-sumi-hairline p-6">
            <h3 className="font-display text-xl">{t("landing.how_title")}</h3>
            <p className="mt-2 font-body text-sm text-sumi-soft">{t("landing.how_body")}</p>
          </div>
        </div>
      </section>

      <section className="my-16 px-6">
        <div className="hanko-stamp mx-auto max-w-3xl p-6">
          <h3 className="font-display text-2xl">{t("landing.no_auto_title")}</h3>
          <p className="mt-3 font-body text-base text-sumi-soft">{t("landing.no_auto_body")}</p>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-16">
        <h2 className="font-display text-3xl font-light md:text-4xl">
          {t("landing.steps_title")}
        </h2>
        <ol className="mt-8 space-y-6">
          {STEP_KEYS.map((key, index) => (
            <li key={key} className="flex items-start gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-sumi-hairline font-mono text-sm text-sumi-soft">
                {index + 1}
              </span>
              <p className="font-body text-base text-sumi-soft">{t(`landing.${key}`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="px-6 py-16">
        <div className="mx-auto max-w-2xl">
          <h2 className="font-display text-3xl font-light md:text-4xl">
            {t("landing.purpose_title")}
          </h2>
          <p className="mt-4 font-body text-base leading-relaxed text-sumi-soft">
            {t("landing.purpose_body")}
          </p>
        </div>
      </section>

      <section className="border-t border-sumi-hairline px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <h2 className="font-display text-3xl font-light md:text-4xl">
            {t("landing.open_title")}
          </h2>
          <p className="mt-4 font-body text-base text-sumi-soft">{t("landing.open_body")}</p>
          <Button
            variant="outline"
            asChild
            className="mt-6 border-sumi bg-transparent text-sumi shadow-none hover:bg-sumi hover:text-washi"
          >
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              {t("landing.github_cta")}
            </a>
          </Button>
        </div>
      </section>

      <footer className="border-t border-sumi-hairline px-6 py-8 text-center font-mono text-xs tracking-wide text-sumi-outline">
        {t("footer.text", { year: currentYear })}
      </footer>
    </main>
  );
}
