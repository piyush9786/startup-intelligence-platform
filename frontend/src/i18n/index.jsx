import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import en from "./en.js";
import hi from "./hi.js";
import mr from "./mr.js";

// ── Language registry ────────────────────────────────────────────────────────
export const LANGUAGES = [
  { code: "en", label: "English", nativeLabel: "English" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी" },
  { code: "mr", label: "Marathi", nativeLabel: "मराठी" },
];

const TRANSLATIONS = { en, hi, mr };
const STORAGE_KEY = "si_language";
const DEFAULT_LANG = "en";

// ── Context ──────────────────────────────────────────────────────────────────
const LanguageContext = createContext({
  language: DEFAULT_LANG,
  setLanguage: () => {},
  t: (key) => key,
});

// ── Provider ─────────────────────────────────────────────────────────────────
export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return TRANSLATIONS[stored] ? stored : DEFAULT_LANG;
    } catch {
      return DEFAULT_LANG;
    }
  });

  // Apply lang attribute to <html> for proper font rendering and a11y
  useEffect(() => {
    document.documentElement.setAttribute("lang", language);
  }, [language]);

  const setLanguage = useCallback((code) => {
    if (!TRANSLATIONS[code]) return;
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // ignore storage errors
    }
    setLanguageState(code);
  }, []);

  // Translation function — supports {variable} interpolation
  const t = useCallback(
    (key, vars = {}) => {
      const dict = TRANSLATIONS[language] || en;
      let value = dict[key] ?? en[key] ?? key;
      // Interpolate {variable} placeholders
      Object.entries(vars).forEach(([k, v]) => {
        value = value.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      });
      return value;
    },
    [language],
  );

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useLanguage() {
  return useContext(LanguageContext);
}

// Convenience hook — returns just the t() function and language code
export function useT() {
  const { t, language } = useContext(LanguageContext);
  return { t, language };
}
