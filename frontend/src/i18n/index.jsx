import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import en from "./en.js";
import hi from "./hi.js";
import mr from "./mr.js";

export const LANGUAGES = [
  {
    code: "en",
    label: "English",
    nativeLabel: "English",
  },
  {
    code: "hi",
    label: "Hindi",
    nativeLabel: "हिन्दी",
  },
  {
    code: "mr",
    label: "Marathi",
    nativeLabel: "मराठी",
  },
];

const TRANSLATIONS = {
  en,
  hi,
  mr,
};

const DEFAULT_LANGUAGE = "en";
const STORAGE_KEY = "si_language";
const LEGACY_STORAGE_KEYS = [
  "startup_os_lang",
];

function validLanguage(code) {
  return Boolean(
    code &&
    Object.prototype.hasOwnProperty.call(
      TRANSLATIONS,
      code,
    ),
  );
}

function readStoredLanguage() {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  try {
    const currentValue =
      window.localStorage.getItem(STORAGE_KEY);

    if (validLanguage(currentValue)) {
      return currentValue;
    }

    for (const key of LEGACY_STORAGE_KEYS) {
      const legacyValue =
        window.localStorage.getItem(key);

      if (validLanguage(legacyValue)) {
        window.localStorage.setItem(
          STORAGE_KEY,
          legacyValue,
        );

        return legacyValue;
      }
    }
  } catch {
    // Storage may be unavailable in private browsing.
  }

  return DEFAULT_LANGUAGE;
}

const defaultT = (key, variables = {}) => {
  let result = en[key] ?? key;
  if (typeof result !== "string") {
    return String(result);
  }
  for (const [name, value] of Object.entries(variables)) {
    result = result.replace(new RegExp(`\\{${name}\\}`, "g"), String(value));
  }
  return result;
};

const LanguageContext = createContext({
  language: DEFAULT_LANGUAGE,
  setLanguage: () => {},
  t: defaultT,
});

export function LanguageProvider({
  children,
}) {
  const [language, setLanguageState] =
    useState(readStoredLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = "ltr";
  }, [language]);

  useEffect(() => {
    function handleStorage(event) {
      if (
        event.key === STORAGE_KEY &&
        validLanguage(event.newValue)
      ) {
        setLanguageState(event.newValue);
      }
    }

    window.addEventListener(
      "storage",
      handleStorage,
    );

    return () => {
      window.removeEventListener(
        "storage",
        handleStorage,
      );
    };
  }, []);

  const setLanguage = useCallback((code) => {
    if (!validLanguage(code)) {
      return;
    }

    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        code,
      );

      for (const key of LEGACY_STORAGE_KEYS) {
        window.localStorage.removeItem(key);
      }
    } catch {
      // Continue with in-memory state.
    }

    setLanguageState(code);
  }, []);

  const t = useCallback(
    (key, variables = {}) => {
      const dictionary =
        TRANSLATIONS[language] || en;

      let result =
        dictionary[key] ??
        en[key] ??
        key;

      if (typeof result !== "string") {
        return String(result);
      }

      for (const [name, value] of Object.entries(
        variables,
      )) {
        result = result.replace(
          new RegExp(
            `\\{${name}\\}`,
            "g",
          ),
          String(value),
        );
      }

      return result;
    },
    [language],
  );

  const contextValue = useMemo(
    () => ({
      language,
      setLanguage,
      t,
    }),
    [
      language,
      setLanguage,
      t,
    ],
  );

  return (
    <LanguageContext.Provider
      value={contextValue}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

export function useT() {
  const {
    language,
    setLanguage,
    t,
  } = useContext(LanguageContext);

  return {
    language,
    setLanguage,
    t,
  };
}
