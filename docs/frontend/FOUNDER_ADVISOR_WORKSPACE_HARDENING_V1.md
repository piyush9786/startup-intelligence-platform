# Founder Advisor Workspace Hardening v1

## Scope

Phase 4G.2 adds browser-like interaction coverage and production-oriented
frontend safeguards to the founder advisor workspace.

## Interaction coverage

Vitest runs with `jsdom`, React Testing Library, and `user-event`. Tests
cover:

- successful founder sign-in;
- rejected credentials and accessible error output;
- startup-profile loading;
- explicit empty current-briefing state;
- current briefing rendering;
- briefing-history selection;
- successful briefing generation and history refresh;
- generation failure followed by a successful retry;
- session-expiry sign-out;
- environment-derived admin and API documentation links.

Existing advisor utility tests also run under Vitest.

## Session expiry

The API layer emits a browser event whenever token refresh fails or an
authenticated request has no usable refresh token. The application listens
for that event and immediately returns to the sign-in screen after clearing
session storage.

## Environment-safe links

The frontend uses:

```text
VITE_API_BASE_URL
VITE_PLATFORM_BASE_URL
```

`VITE_PLATFORM_BASE_URL` is the origin used for Django admin and API
documentation links. No production link is hard-coded to localhost.

External links opened in a new tab include:

```text
rel="noopener noreferrer"
```

## Reproducible installation and CI

`package-lock.json` is committed. The frontend Docker image and GitHub
Actions use `npm ci`. CI runs both:

```text
npm test
npm run build
```

## Local origins

The example Django CORS configuration allows both common local frontend
origins:

```text
http://localhost:5173
http://127.0.0.1:5173
```
