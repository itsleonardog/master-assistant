import { useTranslation } from "react-i18next";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { LanguageSwitcher } from "./LanguageSwitcher";

// TODO: replace with the actual repository URL before publishing.
const GITHUB_URL = "https://github.com/itsleonardog/master-assistant";

interface LandingPageProps {
  onEnterApp: () => void;
}

/** Translation keys of the four numbered steps, in display order. */
const STEP_KEYS = ["step1", "step2", "step3", "step4"] as const;

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
    <main className="min-h-screen bg-background text-foreground">
      <section className="bg-muted/20">
        <div className="mx-auto max-w-4xl px-6 py-12 md:py-20">
          <div className="flex items-center justify-between gap-4">
            <Badge variant="secondary">{t("landing.badge")}</Badge>
            <LanguageSwitcher />
          </div>
          <h1 className="mt-4 max-w-3xl text-3xl font-bold tracking-tight md:text-5xl">
            {t("landing.headline")}
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            {t("landing.subheadline")}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" onClick={onEnterApp}>
              {t("landing.cta_primary")}
            </Button>
            <Button size="lg" variant="outline" onClick={scrollToMission}>
              {t("landing.cta_secondary")}
            </Button>
          </div>
        </div>
      </section>

      <section id="mission" className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">{t("landing.mission_title")}</h2>
        <p className="mt-4 text-base text-muted-foreground">{t("landing.mission_body")}</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t("landing.audience_title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{t("landing.audience_body")}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t("landing.how_title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{t("landing.how_body")}</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="my-16 px-6">
        <Alert className="mx-auto max-w-4xl border-l-4 border-primary bg-muted/30 p-6">
          <h3 className="text-xl font-bold">{t("landing.no_auto_title")}</h3>
          <p className="mt-2 text-base text-muted-foreground">{t("landing.no_auto_body")}</p>
        </Alert>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">{t("landing.steps_title")}</h2>
        <ol className="mt-8 space-y-6">
          {STEP_KEYS.map((key, index) => (
            <li key={key} className="flex items-start gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">
                {index + 1}
              </span>
              <p className="text-base text-muted-foreground">{t(`landing.${key}`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">{t("landing.purpose_title")}</h2>
        <p className="mt-4 text-base text-muted-foreground">{t("landing.purpose_body")}</p>
      </section>

      <section className="bg-muted/20">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <h2 className="text-2xl font-semibold tracking-tight">{t("landing.open_title")}</h2>
          <p className="mt-4 text-base text-muted-foreground">{t("landing.open_body")}</p>
          <Button variant="outline" asChild className="mt-6">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              {t("landing.github_cta")}
            </a>
          </Button>
        </div>
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        {t("footer.text", { year: currentYear })}
      </footer>
    </main>
  );
}
