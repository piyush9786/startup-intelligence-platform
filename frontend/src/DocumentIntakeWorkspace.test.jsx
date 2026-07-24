import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { autofillStartupProfileFromDocument } from "./api";
import DocumentIntakeWorkspace from "./DocumentIntakeWorkspace";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    autofillStartupProfileFromDocument: vi.fn(),
  };
});

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
      evidence: { text: "Acme BioTech Private Limited incorporated on 2026", page_number: 1, heading: "Header" },
    },
    {
      field: "sectors",
      value: ["CleanTech", "BioTech"],
      confidence: 85,
      reason: "Sectors listed on page 2.",
      evidence: { text: "Sector: CleanTech, BioTech", page_number: 2, heading: "Overview" },
    },
  ],
  warnings: [],
};

describe("DocumentIntakeWorkspace component", () => {
  test("renders document intake upload form", () => {
    render(
      <DocumentIntakeWorkspace
        onApplyConfirmedFacts={vi.fn()}
        profile={{ startup_name: "Acme" }}
      />
    );

    expect(
      screen.getByRole("heading", { name: "AI Document Intake" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Extract startup facts" }),
    ).toBeInTheDocument();
  });

  test("extracts facts and allows founder to select and apply confirmed facts", async () => {
    vi.mocked(autofillStartupProfileFromDocument).mockResolvedValue(sampleExtractionResult);
    const handleApply = vi.fn().mockResolvedValue({});
    const user = userEvent.setup();

    render(
      <DocumentIntakeWorkspace
        onApplyConfirmedFacts={handleApply}
        profile={{ startup_name: "Acme", legal_name: "Old Name" }}
      />
    );

    const file = new File(["dummy content"], "acme_pitch_deck.pdf", {
      type: "application/pdf",
    });

    const fileInput = screen.getByLabelText(/select document file/i);
    await user.upload(fileInput, file);

    const submitBtn = screen.getByRole("button", { name: "Extract startup facts" });
    await user.click(submitBtn);

    expect(
      await screen.findByRole("heading", { name: "Document summary" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Acme BioTech Private Limited")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Apply confirmed facts to startup profile" }));

    expect(handleApply).toHaveBeenCalledWith({
      legal_name: "Acme BioTech Private Limited",
      autofilled_fields: ["legal_name"],
    });
  });
});
