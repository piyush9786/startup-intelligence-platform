export const RESEARCH_HANDOFF_STORAGE_KEY =
  "startup-intelligence.research-handoff.v1";

const MAX_HANDOFF_AGE_MS = 10 * 60 * 1000;

export function saveResearchHandoff({
  question,
  startupProfileId,
  autoSubmit = true,
}) {
  const normalizedQuestion = String(
    question || "",
  ).trim();

  if (
    normalizedQuestion.length < 5
    || !startupProfileId
  ) {
    return false;
  }

  const payload = {
    question: normalizedQuestion,
    startupProfileId: String(
      startupProfileId,
    ),
    autoSubmit: Boolean(autoSubmit),
    createdAt: Date.now(),
  };

  window.sessionStorage.setItem(
    RESEARCH_HANDOFF_STORAGE_KEY,
    JSON.stringify(payload),
  );

  return true;
}


export function takeResearchHandoff({
  startupProfileId,
}) {
  const raw = window.sessionStorage.getItem(
    RESEARCH_HANDOFF_STORAGE_KEY,
  );

  if (!raw) {
    return null;
  }

  let payload;

  try {
    payload = JSON.parse(raw);
  } catch {
    window.sessionStorage.removeItem(
      RESEARCH_HANDOFF_STORAGE_KEY,
    );
    return null;
  }

  const question = String(
    payload?.question || "",
  ).trim();

  const storedProfileId = String(
    payload?.startupProfileId || "",
  );

  const currentProfileId = String(
    startupProfileId || "",
  );

  const createdAt = Number(
    payload?.createdAt || 0,
  );

  const expired = (
    !Number.isFinite(createdAt)
    || createdAt <= 0
    || Date.now() - createdAt > MAX_HANDOFF_AGE_MS
  );

  const invalid = (
    question.length < 5
    || !storedProfileId
    || storedProfileId !== currentProfileId
    || expired
  );

  if (invalid) {
    window.sessionStorage.removeItem(
      RESEARCH_HANDOFF_STORAGE_KEY,
    );
    return null;
  }

  window.sessionStorage.removeItem(
    RESEARCH_HANDOFF_STORAGE_KEY,
  );

  return {
    question,
    autoSubmit: (
      payload.autoSubmit !== false
    ),
  };
}
