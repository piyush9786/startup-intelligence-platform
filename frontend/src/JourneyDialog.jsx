import React from "react";
import { useT } from "./i18n/index.jsx";
import * as m from "motion/react-m";

export function JourneyDialog({ onExistingStartup, onNewIdea }) {
  const { t } = useT();
  return (
    <m.div
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.95, opacity: 0 }}
      initial={{ scale: 0.95, opacity: 0 }}
      style={{
        backgroundColor: "#fff",
        borderRadius: "12px",
        padding: "2rem",
        maxWidth: "480px",
        width: "100%",
        boxShadow:
          "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      }}
    >
      <h2 style={{ margin: "0 0 1rem 0", color: "#0f172a" }}>
        {t("journey.title")}
      </h2>
      <p style={{ margin: "0 0 1.5rem 0", color: "#475569", lineHeight: 1.5 }}>
        {t("journey.subtitle")}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <button
          className="button button-primary"
          onClick={onExistingStartup}
          style={{
            width: "100%",
            justifyContent: "center",
            padding: "0.75rem",
          }}
        >
          {t("journey.existing_startup")}
        </button>
        <button
          className="button button-secondary"
          onClick={onNewIdea}
          style={{
            width: "100%",
            justifyContent: "center",
            padding: "0.75rem",
          }}
        >
          {t("journey.new_idea")}
        </button>
      </div>
    </m.div>
  );
}
