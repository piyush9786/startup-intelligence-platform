import assert from "node:assert/strict";
import test from "node:test";

import {
  briefingCounts,
  formatDateTime,
  humanizeApiError,
  normalizeCollection,
  sourceReferenceLabel,
} from "./advisor.js";

test("normalizeCollection supports paginated and plain API responses", () => {
  const profiles = [{ id: "one" }, { id: "two" }];

  assert.deepEqual(normalizeCollection(profiles), profiles);
  assert.deepEqual(normalizeCollection({ results: profiles, count: 2 }), profiles);
  assert.deepEqual(normalizeCollection({ detail: "unexpected" }), []);
  assert.deepEqual(normalizeCollection(null), []);
});

test("humanizeApiError prioritizes DRF detail messages", () => {
  const error = {
    response: {
      data: {
        detail: "The local model is unavailable.",
      },
    },
  };

  assert.equal(
    humanizeApiError(error),
    "The local model is unavailable.",
  );
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

  assert.equal(
    humanizeApiError(error),
    "username: This field is required. password: This field may not be blank.",
  );
});

test("humanizeApiError explains timeout and network failures", () => {
  assert.equal(
    humanizeApiError({ code: "ECONNABORTED" }),
    "The request timed out. The local model may still be loading.",
  );
  assert.equal(
    humanizeApiError({ message: "Network Error" }),
    "The platform API could not be reached.",
  );
});

test("sourceReferenceLabel renders source type and JSON Pointer path", () => {
  assert.equal(
    sourceReferenceLabel({
      source_type: "recommendation_generation",
      field_path: "/status",
    }),
    "recommendation generation · /status",
  );
});

test("briefingCounts handles complete and missing briefing payloads", () => {
  assert.deepEqual(
    briefingCounts({
      briefing: {
        top_priorities: [{}, {}],
        scheme_guidance: [{}],
        risks: [{}, {}, {}],
        questions_for_founder: ["Question"],
      },
    }),
    {
      priorities: 2,
      schemes: 1,
      risks: 3,
      questions: 1,
    },
  );

  assert.deepEqual(briefingCounts(null), {
    priorities: 0,
    schemes: 0,
    risks: 0,
    questions: 0,
  });
});

test("formatDateTime safely handles missing and invalid values", () => {
  assert.equal(formatDateTime(null), "Time unavailable");
  assert.equal(formatDateTime("not-a-date"), "Time unavailable");
  assert.notEqual(
    formatDateTime("2026-07-21T08:31:31Z"),
    "Time unavailable",
  );
});
