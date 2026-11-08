import { useTranslation } from "react-i18next";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import i18n, { setLanguage } from "@/i18n";

type Lang = "it" | "en";

/** Narrow the i18next language to the two locales we ship. */
function currentLang(): Lang {
  return i18n.language === "en" ? "en" : "it";
}

/** Language picker: writes the choice through `setLanguage` (localStorage). */
export function LanguageSwitcher() {
  const { t } = useTranslation();

  function handleChange(value: string) {
    setLanguage(value === "en" ? "en" : "it");
  }

  return (
    <Select value={currentLang()} onValueChange={handleChange}>
      <SelectTrigger className="w-[120px]" aria-label={t("common.language_label")}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="it">{t("common.language_it")}</SelectItem>
        <SelectItem value="en">{t("common.language_en")}</SelectItem>
      </SelectContent>
    </Select>
  );
}
