import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import it from "./locales/it.json";

const STORAGE_KEY = "master-assistant:lang";

function detectInitialLang(): "it" | "en" {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "it" || stored === "en") return stored;
  const browser = navigator.language.toLowerCase();
  return browser.startsWith("it") ? "it" : "en";
}

i18n.use(initReactI18next).init({
  resources: { it: { translation: it }, en: { translation: en } },
  lng: detectInitialLang(),
  fallbackLng: "it",
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: "it" | "en") {
  localStorage.setItem(STORAGE_KEY, lang);
  i18n.changeLanguage(lang);
}

export default i18n;
