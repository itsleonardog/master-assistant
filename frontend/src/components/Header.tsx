import { useTranslation } from "react-i18next";

/** Page heading and one-line description. */
export function Header() {
  const { t } = useTranslation();

  return (
    <header className="space-y-2 text-center sm:text-left">
      <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
        {t("header.title")}
      </h1>
      <p className="font-body text-sm text-sumi-soft sm:text-base">{t("header.subtitle")}</p>
    </header>
  );
}
