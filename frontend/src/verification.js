export const VERIFICATION_GATE_STATUSES = Object.freeze({
  NOT_SUBMITTED: "not_submitted",
  PENDING: "pending",
  APPROVED: "approved",
  REJECTED: "rejected",
  EXPIRED: "expired",
});


export function verificationGateStatusLabel(status) {
  const labels = {
    [VERIFICATION_GATE_STATUSES.NOT_SUBMITTED]:
      "Evidence required",
    [VERIFICATION_GATE_STATUSES.PENDING]:
      "Awaiting review",
    [VERIFICATION_GATE_STATUSES.APPROVED]:
      "Verified",
    [VERIFICATION_GATE_STATUSES.REJECTED]:
      "Changes required",
    [VERIFICATION_GATE_STATUSES.EXPIRED]:
      "Verification expired",
  };

  return labels[status] || "Verification required";
}


export function verificationGateStatusTone(status) {
  if (status === VERIFICATION_GATE_STATUSES.APPROVED) {
    return "success";
  }

  if (
    status === VERIFICATION_GATE_STATUSES.REJECTED
    || status === VERIFICATION_GATE_STATUSES.EXPIRED
  ) {
    return "danger";
  }

  return "info";
}


export function verificationGateNeedsSubmission(gate = {}) {
  return [
    VERIFICATION_GATE_STATUSES.NOT_SUBMITTED,
    VERIFICATION_GATE_STATUSES.REJECTED,
    VERIFICATION_GATE_STATUSES.EXPIRED,
  ].includes(gate.status);
}


export function verificationGateCanUploadEvidence(gate = {}) {
  return (
    gate.status === VERIFICATION_GATE_STATUSES.PENDING
    && Boolean(gate.submission?.id)
  );
}


export function normalizeVerificationGateResponse(payload = {}) {
  const gates = Array.isArray(payload.gates)
    ? payload.gates
    : [];

  return {
    startupProfileId: payload.startup_profile_id || null,
    schemeId: payload.scheme_id || null,
    schemeVersionId: payload.scheme_version_id || null,
    asOfDate: payload.as_of_date || null,
    gateCount: Number(payload.gate_count) || gates.length,
    unresolvedCount:
      Number(payload.unresolved_count)
      || gates.filter((gate) => !gate.resolved).length,
    gates,
  };
}

export function parseVerificationClaimValue(
  rawValue,
  expectedValue,
) {
  if (typeof expectedValue === "boolean") {
    if (rawValue === "true") return true;
    if (rawValue === "false") return false;
    throw new Error("Choose whether the claim is true or false.");
  }

  if (typeof expectedValue === "number") {
    const value = Number(rawValue);
    if (!Number.isFinite(value)) {
      throw new Error("Enter a valid numeric claim.");
    }
    return value;
  }

  const value = String(rawValue ?? "").trim();
  if (!value) {
    throw new Error("Enter the value you want reviewed.");
  }
  return value;
}
