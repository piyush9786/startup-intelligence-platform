# Public Entry and Authentication V1 — Phase 50

## Purpose

The Public Entry and Authentication milestone provides a responsive, accessible, and structured entry point for unauthenticated visitors and returning founders.

It establishes the product boundary between the public platform explanation and the protected founder application shell.

## Scope

- Responsive landing page (`LandingPage`) with hero workspace preview, how-it-works workflow, capability breakdown, responsible AI trust principles, and footer.
- Public header with smooth-scrolling section navigation, sign in action, and founder account creation trigger.
- Founder registration page (`RegistrationPage`) with API integration at `POST /api/v1/auth/register/`.
- Founder sign in page (`LoginPage`) with simpleJWT token authentication at `POST /api/v1/auth/token/`.
- Password recovery page (`PasswordRecoveryPage`) with username/email recovery guidance and platform administrator assistance details.
- Protected application shell (`App.jsx`) ensuring unauthenticated users see the public entry experience and authenticated founders access their private workspace.

## Authorization & Security Boundaries

1. **Public Registration**:
   - `POST /api/v1/auth/register/` is unauthenticated (`AllowAny`).
   - Ignores role parameters in payloads; unconditionally creates accounts with `User.Role.FOUNDER`.
   - Normalizes email addresses and validates password strength using Django auth password validators.

2. **Authentication**:
   - `POST /api/v1/auth/token/` yields JWT access and refresh tokens.
   - Session tokens are stored strictly in `sessionStorage` and cleared upon explicit sign-out or session expiry events (`SESSION_EXPIRED_EVENT`).

3. **Protected Shell**:
   - Unauthenticated state renders `<PublicEntry />`.
   - Successful authentication immediately opens the founder workspace.

## Verification & Testing

- 4 backend API tests in `apps/accounts/tests/test_founder_registration_api.py`.
- 144 frontend Vitest tests including public landing navigation, sign in, registration, error alerts, and password recovery.
- Full backend pytest suite passing (522 tests).
- Production bundle build (`npm run build`) passing.
- Ruff linting and Django system checks passing with zero migration drift.
