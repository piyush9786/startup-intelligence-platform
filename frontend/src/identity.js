export function normalizeCurrentUser(payload = {}) {
  return {
    id: payload.id || null,
    username: payload.username || "",
    email: payload.email || "",
    role: payload.role || "",
    roleLabel: payload.role_label || "",
    emailVerified: Boolean(payload.email_verified),
    isStaff: Boolean(payload.is_staff),
    isSuperuser: Boolean(payload.is_superuser),
    canReviewEligibility: Boolean(
      payload.can_review_eligibility,
    ),
  };
}


export function canAccessReviewerWorkspace(user = {}) {
  return Boolean(user?.canReviewEligibility);
}
