# Mini App Auth Review Context

This is a sanitized evidence set for advisory review only.

Reproduction: Telegram Mini App opens; bootstrap may remain waiting for identity/authentication. Review the frontend bootstrap and backend Telegram auth contract together. Check the actual endpoint path, initData timing, token storage/restoration, 401 behavior, and role propagation. No production changes are authorized by this handoff.

Files are excerpts or sanitized copies. Do not infer unavailable implementation. Do not request or expose secrets.
