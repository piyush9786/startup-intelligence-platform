import {
  describe,
  expect,
  test,
} from "vitest";

import {
  canAccessReviewerWorkspace,
  normalizeCurrentUser,
} from "./identity";


describe("authenticated identity helpers", () => {
  test("normalizes the current-user response", () => {
    expect(
      normalizeCurrentUser({
        id: "user-one",
        username: "reviewer",
        email: "reviewer@example.com",
        role: "reviewer",
        role_label: "Data reviewer",
        email_verified: true,
        is_staff: false,
        is_superuser: false,
        can_review_eligibility: true,
      }),
    ).toEqual({
      id: "user-one",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      roleLabel: "Data reviewer",
      emailVerified: true,
      isStaff: false,
      isSuperuser: false,
      canReviewEligibility: true,
    });
  });

  test("does not infer reviewer access from staff status", () => {
    const user = normalizeCurrentUser({
      role: "founder",
      is_staff: true,
      can_review_eligibility: false,
    });

    expect(
      canAccessReviewerWorkspace(user),
    ).toBe(false);
  });

  test("uses only the server capability flag", () => {
    expect(
      canAccessReviewerWorkspace({
        canReviewEligibility: true,
      }),
    ).toBe(true);

    expect(
      canAccessReviewerWorkspace({
        role: "reviewer",
        canReviewEligibility: false,
      }),
    ).toBe(false);
  });
});
