# Repository Working Notes

## Scope
- This repository contains a Django backend in `backend/` and a Vite/React frontend in `frontend/`.
- Prefer end-to-end fixes that keep backend contracts and frontend consumers aligned.

## Backend
- Use the namespaced API routes under `/api/v1/`; avoid duplicating routes in `backend/config/urls.py`.
- Keep auth, invitation, task, and notification responses on the shared success/error envelope already used by the API.
- Do not log secrets, tokens, raw passwords, or provider credentials.
- Add regression tests for any auth, permission, or deployment bootstrap change.

## Frontend
- Use the centralized API client in `frontend/src/services/api.js`.
- Keep auth persistence and redirect behavior aligned with `frontend/src/utils/authSession.*` and `frontend/src/utils/authRouting.*`.
- Prefer fixing data flow or API parsing issues at the shared service or slice layer instead of patching individual pages.

## Verification
- For backend changes, run focused Django tests first, then broaden if needed.
- For frontend changes, run the relevant lint or test command before finishing.
