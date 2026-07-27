import React from "react";
import {
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  describe,
  expect,
  test,
} from "vitest";

import LanguageSwitcher from "../LanguageSwitcher.jsx";
import {
  LanguageProvider,
  useT,
} from "./index.jsx";

function TranslationProbe() {
  const { t } = useT();

  return (
    <div data-testid="translated-dashboard">
      {t("nav.dashboard")}
    </div>
  );
}

describe("language switching", () => {
  test("changes visible UI text to Hindi", () => {
    render(
      <LanguageProvider>
        <LanguageSwitcher />
        <TranslationProbe />
      </LanguageProvider>,
    );

    expect(
      screen.getByTestId(
        "translated-dashboard",
      ),
    ).toHaveTextContent("Dashboard");

    fireEvent.click(
      screen.getByRole(
        "button",
        {
          name: /Language:/i,
        },
      ),
    );

    fireEvent.click(
      screen.getByRole(
        "option",
        {
          name: /हिन्दी/i,
        },
      ),
    );

    expect(
      screen.getByTestId(
        "translated-dashboard",
      ),
    ).toHaveTextContent("डैशबोर्ड");

    expect(
      document.documentElement.lang,
    ).toBe("hi");
  });
});
