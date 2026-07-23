import {
  parseVerificationClaimValue,
} from "./verification";


export const REVIEWER_VERIFICATION_STATUSES =
  Object.freeze({
    PENDING: "pending",
    APPROVED: "approved",
    REJECTED: "rejected",
    EXPIRED: "expired",
  });


export function reviewerVerificationStatusLabel(status) {
  const labels = {
    [REVIEWER_VERIFICATION_STATUSES.PENDING]:
      "Pending review",
    [REVIEWER_VERIFICATION_STATUSES.APPROVED]:
      "Approved",
    [REVIEWER_VERIFICATION_STATUSES.REJECTED]:
      "Rejected",
    [REVIEWER_VERIFICATION_STATUSES.EXPIRED]:
      "Expired",
  };

  return labels[status] || "Unknown";
}


export function reviewerVerificationStatusTone(status) {
  if (
    status === REVIEWER_VERIFICATION_STATUSES.APPROVED
  ) {
    return "success";
  }

  if (
    status === REVIEWER_VERIFICATION_STATUSES.REJECTED
    || status === REVIEWER_VERIFICATION_STATUSES.EXPIRED
  ) {
    return "danger";
  }

  return "info";
}


export function normalizeReviewerVerificationQueue(
  payload = {},
) {
  const submissions = Array.isArray(payload.submissions)
    ? payload.submissions
    : [];

  return {
    asOfDate: payload.as_of_date || null,
    count: Number(payload.count) || submissions.length,
    submissions,
  };
}


export function buildReviewerDecisionPayload({
  submission,
  outcome,
  rawVerifiedValue,
  reviewNotes = "",
  validFrom,
  expiresOn = "",
}) {
  if (!submission?.id) {
    throw new Error("A verification submission is required.");
  }

  if (!["approved", "rejected"].includes(outcome)) {
    throw new Error("Choose approve or reject.");
  }

  if (!validFrom) {
    throw new Error("Choose when this decision becomes effective.");
  }

  if (
    expiresOn
    && expiresOn < validFrom
  ) {
    throw new Error(
      "Expiry cannot precede the valid-from date.",
    );
  }

  const payload = {
    submissionId: submission.id,
    outcome,
    reviewNotes: reviewNotes.trim(),
    validFrom,
    expiresOn: expiresOn || undefined,
  };

  if (outcome === "approved") {
    payload.verifiedValue =
      parseVerificationClaimValue(
        rawVerifiedValue,
        submission.expected_value,
      );
  }

  return payload;
}
