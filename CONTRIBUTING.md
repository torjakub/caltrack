# Contributing

calTrack started as a personal self-hosted project and is open-sourced in case it's useful to others. Contributions are welcome, but it's still early — expect rough edges.

## Project layout

- `/server` — FastAPI + SQLite, the single source of truth. See `server/README.md`.
- `/web` — React (Vite) thin client. See `web/README.md`.
- `/mobile` — React Native (Expo), offline-first with sync. See `mobile/README.md`.
- `/docs` — architecture, self-hosting, sync protocol, and LLM provider docs.

Read `docs/architecture.md` and `docs/sync-protocol.md` before touching sync-related code — the conflict-resolution design is deliberate (whole-record, not field-level; see the doc for why).

## Before opening a PR

- Run the server test suite: `cd server && .venv/bin/pytest tests/`
- Typecheck the client you touched: `npx tsc -b --noEmit` (web) or `npx tsc --noEmit` (mobile)
- Keep changes scoped — this codebase favors small, focused PRs over large refactors.

## Reporting bugs

Open an issue with what you expected vs. what happened, and whether it's `/server`, `/web`, or `/mobile`. For sync-related bugs, include what device(s) were involved and roughly when each side last synced — timing usually matters.

## License

By contributing, you agree your contributions are licensed under this project's [AGPL-3.0](LICENSE).
