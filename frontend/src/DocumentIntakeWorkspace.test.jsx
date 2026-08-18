import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { autofillStartupProfileFromDocument } from "./api";
import DocumentIntakeWorkspace from "./DocumentIntakeWorkspace";
import { LanguageProvider } from "./i18n/index.jsx";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    autofillStartupProfileFromDocument: vi.fn(),
  };
});

vi.mock("./FounderOperationsPanel", () => ({
  default: () => null,
}));

vi.mock("./ExpertMarketplaceRequestPanel", () => ({
  default: () => null,
}));

const sampleExtractionResult = {
  parser_version: "startup-document-autofill-v1",
  requires_confirmation: true,
  document: {
    filename: "acme_pitch_deck.pdf",
    mime_type: "application/pdf",
    sha256: "abc123hash",
    detected_title: "Acme Pitch Deck",
    page_count: 5,
  },
  document_type: {
    value: "pitch_deck",
    confidence: 90,
    source: "detected",
  },
  suggestions: [
    {
      field: "legal_name",
      value: "Acme BioTech Private Limited",
      confidence: 96,
      reason: "Enterprise name in document.",
      evidence: {
        text: "Acme BioTech Private Limited incorporated on 2026",
        page_number: 1,
        heading: "Header",
      },
    },
    {
      field: "sectors",
      value: ["CleanTech", "BioTech"],
      confidence: 85,
      reason: "Sectors listed on page 2.",
      evidence: {
        text: "Sector: CleanTech, BioTech",
        page_number: 2,
        heading: "Overview",
      },
    },
  ],
  warnings: [],
};

function renderWorkspace({
  language = "en",
  onApplyConfirmedFacts = vi.fn(),
  profile = { startup_name: "Acme" },
} = {}) {
  window.localStorage.setItem("si_language", language);
  return render(
    <LanguageProvider>
      <DocumentIntakeWorkspace
        onApplyConfirmedFacts={onApplyConfirmedFacts}
        profile={profile}
      />
    </LanguageProvider>,
  );
}

describe("DocumentIntakeWorkspace component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  test("renders the English document intake upload form", () => {
    renderWorkspace();

    expect(
      screen.getByRole("heading", { name: "AI Document Intake" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Extract startup facts" }),
    ).toBeInTheDocument();
  });

  test.each([
    ["hi", "AI दस्तावेज़ ग्रहण", "स्टार्टअप तथ्य निकालें"],
    ["mr", "AI कागदपत्र ग्रहण", "स्टार्टअप तथ्ये मिळवा"],
  ])("renders %s regional-language controls", (language, title, action) => {
    renderWorkspace({ language });

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: action })).toBeInTheDocument();
  });

  test("extracts facts and applies confirmed suggestions", async () => {
    vi.mocked(autofillStartupProfileFromDocument).mockResolvedValue(
      sampleExtractionResult,
    );
    const handleApply = vi.fn().mockResolvedValue({});
    const user = userEvent.setup();

    renderWorkspace({
      onApplyConfirmedFacts: handleApply,
      profile: { startup_name: "Acme", legal_name: "Old Name" },
    });

    const file = new File(["dummy content"], "acme_pitch_deck.pdf", {
      type: "application/pdf",
    });

    await user.upload(
      screen.getByLabelText(/select document file/i),
      file,
    );
    await user.click(
      screen.getByRole("button", { name: "Extract startup facts" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Document summary" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Acme BioTech Private Limited"),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Apply confirmed facts to startup profile",
      }),
    );

    expect(handleApply).toHaveBeenCalledWith({
      legal_name: "Acme BioTech Private Limited",
      autofilled_fields: ["legal_name"],
    });
  });
});
