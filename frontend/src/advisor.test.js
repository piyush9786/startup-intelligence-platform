import { expect, test } from "vitest";

import {
  briefingCounts,
  buildEvidenceById,
  evidenceExcerpt,
  evidenceTitle,
  formatDateTime,
  formatEvidenceScore,
  humanizeApiError,
  normalizeCollection,
  sourceReferenceLabel,
} from "./advisor.js";

test("normalizeCollection supports paginated and plain API responses", () => {
  const profiles = [{ id: "one" }, { id: "two" }];

  expect(normalizeCollection(profiles)).toEqual(profiles);
  expect(normalizeCollection({ results: profiles, count: 2 })).toEqual(profiles);
  expect(normalizeCollection({ detail: "unexpected" })).toEqual([]);
  expect(normalizeCollection(null)).toEqual([]);
});

test("humanizeApiError prioritizes DRF detail messages", () => {
  const error = {
    response: {
      data: {
        detail: "The local model is unavailable.",
      },
    },
  };

  expect(humanizeApiError(error)).toBe("The local model is unavailable.");
});

test("humanizeApiError flattens field validation errors", () => {
  const error = {
    response: {
      data: {
        username: ["This field is required."],
        password: ["This field may not be blank."],
      },
    },
  };

  expect(humanizeApiError(error)).toBe(
    "username: This field is required. password: This field may not be blank.",
  );
});

test("humanizeApiError explains timeout and network failures", () => {
  expect(humanizeApiError({ code: "ECONNABORTED" })).toBe(
    "The request timed out. The local model may still be loading.",
  );
  expect(humanizeApiError({ message: "Network Error" })).toBe(
    "The platform API could not be reached.",
  );
});

test("sourceReferenceLabel renders source type and JSON Pointer path", () => {
  expect(
    sourceReferenceLabel({
      source_type: "recommendation_generation",
      field_path: "/status",
    }),
  ).toBe("recommendation generation · /status");
});

test("briefingCounts handles complete and missing briefing payloads", () => {
  expect(
    briefingCounts({
      briefing: {
        top_priorities: [{}, {}],
        scheme_guidance: [{}],
        risks: [{}, {}, {}],
        questions_for_founder: ["Question"],
      },
    }),
  ).toEqual({
    priorities: 2,
    schemes: 1,
    risks: 3,
    questions: 1,
  });

  expect(briefingCounts(null)).toEqual({
    priorities: 0,
    schemes: 0,
    risks: 0,
    questions: 0,
  });
});

test("formatDateTime safely handles missing and invalid values", () => {
  expect(formatDateTime(null)).toBe("Time unavailable");
  expect(formatDateTime("not-a-date")).toBe("Time unavailable");
  expect(formatDateTime("2026-07-21T08:31:31Z")).not.toBe("Time unavailable");
});



test("evidence helpers expose readable official-source metadata", () => {
  const briefing = {
    prompt_snapshot: {
      retrieved_evidence: [
        {
          id: "chunk-1",
          score: 0.371235,
          title:
            "https://example.gov.in/Startup-Schemes-Playbook-June-2026.pdf",
          source_url:
            "https://example.gov.in/Startup-Schemes-Playbook-June-2026.pdf",
          text: "A long official evidence excerpt ".repeat(20),
        },
      ],
    },
  };

  const evidence = buildEvidenceById(briefing)["chunk-1"];
  expect(evidenceTitle(evidence)).toBe(
    "Startup Schemes Playbook June 2026",
  );
  expect(formatEvidenceScore(evidence.score)).toBe(
    "37% semantic match",
  );
  expect(evidenceExcerpt(evidence, 40).endsWith("…")).toBe(true);
  expect(buildEvidenceById(null)).toEqual({});
});
