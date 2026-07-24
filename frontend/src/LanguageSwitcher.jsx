import React, { useEffect, useRef, useState } from "react";
import { LANGUAGES, useLanguage } from "./i18n/index.jsx";

/**
 * LanguageSwitcher — floating globe button (bottom-right corner).
 * Opens a glassmorphism popup to select English / हिन्दी / मराठी.
 */
export default function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  // Close panel when clicking outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    function handleKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  const current = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];

  return (
    <div
      className="lang-switcher"
      ref={containerRef}
    >
      {/* Floating globe trigger */}
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={`Language: ${current.nativeLabel}. Click to change.`}
        className={`lang-trigger ${open ? "lang-trigger-open" : ""}`}
        id="lang-switcher-btn"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span aria-hidden="true" className="lang-globe">🌐</span>
        <span className="lang-current-label">{current.nativeLabel}</span>
      </button>

      {/* Language menu */}
      {open && (
        <div
          aria-labelledby="lang-switcher-btn"
          className="lang-menu"
          role="listbox"
        >
          <div className="lang-menu-header">Select language</div>
          {LANGUAGES.map((lang) => (
            <button
              aria-selected={language === lang.code}
              className={`lang-option ${language === lang.code ? "lang-option-active" : ""}`}
              key={lang.code}
              onClick={() => {
                setLanguage(lang.code);
                setOpen(false);
              }}
              role="option"
              type="button"
            >
              <span className="lang-option-native">{lang.nativeLabel}</span>
              <span className="lang-option-english">{lang.label}</span>
              {language === lang.code && (
                <span aria-hidden="true" className="lang-checkmark">✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
