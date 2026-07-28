import {
  authenticatedApiClient as authenticatedApiClient,
  submitStartupAssessmentDraft,
} from "./api";


function scopeParams(startupProfileId) {
  return startupProfileId
    ? {
        startup_profile_id: startupProfileId,
      }
    : {};
}


function scopedBody({
  draftId,
  startupProfileId,
  ...body
}) {
  return {
    draft_id: draftId,
    ...body,
    ...(startupProfileId
      ? {
          startup_profile_id: startupProfileId,
        }
      : {}),
  };
}


export async function getConciergeCurrent({
  startupProfileId,
} = {}) {
  const response = await authenticatedApiClient.get(
    "/assistant/concierge/current/",
    {
      params: scopeParams(startupProfileId),
    },
  );

  return response.data;
}


export async function updateConciergeDraft({
  draftId,
  startupProfileId,
  updates,
}) {
  const response = await authenticatedApiClient.post(
    "/assistant/concierge/current/updates/",
    scopedBody({
      draftId,
      startupProfileId,
      updates,
    }),
  );

  return response.data;
}


export async function transitionConcierge({
  confirmed = false,
  draftId,
  expectedState,
  startupProfileId,
}) {
  const response = await authenticatedApiClient.post(
    "/assistant/concierge/current/transitions/",
    scopedBody({
      draftId,
      startupProfileId,
      expected_state: expectedState,
      ...(confirmed ? { confirmed: true } : {}),
    }),
  );

  return response.data;
}


export async function submitConciergeAssessment({
  draftId,
}) {
  return submitStartupAssessmentDraft(draftId);
}
