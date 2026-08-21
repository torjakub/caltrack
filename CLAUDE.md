# calTrack — notes for AI agents

Self-hosted, open-source nutrition/calorie tracker (MyFitnessPal/Fitatu alternative) designed to run on a Raspberry Pi via Docker Compose. Personal project, open-sourced for others to self-host. See `README.md` for the user-facing pitch; this file is oriented at an agent picking up work in this repo.

## Architecture — three independent components, one source of truth

- **`/server`** — FastAPI + SQLite. Runs on the Pi. Owns the canonical database and REST API. The only thing `/mobile` syncs against.
- **`/web`** — React (Vite). Thin client for home-LAN use (laptop browser). Talks directly to the server API. **No local database, no offline logic** — don't add any.
- **`/mobile`** — React Native (Expo Router). **Offline-first**: keeps its own local SQLite (Drizzle ORM) as the on-device source of truth. Logging must work with zero connectivity. Reconciles with the server via the sync engine whenever reachable.

Read `docs/architecture.md` and especially `docs/sync-protocol.md` before touching anything sync-related — the conflict model is a deliberate, non-obvious design choice (see below).

## The sync protocol (read this before editing `sync_engine.py` or `mobile/src/lib/sync.ts`)

Git-like, whole-record, user-resolved conflicts — explicitly **not** a CRDT or auto-merge system, because this is solo/household scale (2-3 devices) and field-level merging isn't worth the complexity.

- Every syncable row has a client-generated UUID `id`, `updated_at`, and a soft-delete `deleted_at`.
- Each device tracks one `since` checkpoint. Per record: `no existing row` or `since is None` or `existing.updated_at <= since` → apply. Otherwise → conflict, return both versions, don't apply either.
- Conflicts surface in the mobile Conflicts screen as "keep mine" / "keep theirs" (whole record, not field-by-field).
- Push order matters (FK dependencies): `user_profile/user_targets → foods → food_nutrients/food_micronutrients → recipes → log_entries`.
- **Custom foods are the only foods a device ever pushes**, and only ones it created (`is_custom=true AND created_by_user_id=<this user>`). Cached external (OFF/USDA) foods are read-only mirrors of what the server already has — never re-pushed.
- A resolution (`/sync/resolve`) is itself a new write and gets a **fresh server-assigned `updated_at`**, not whatever the client last saw — see `server/app/routers/sync.py`.

## Non-obvious gotchas hit during development (don't reintroduce these)

- **SQLite drops tzinfo.** `DateTime(timezone=True)` columns come back naive on SQLite. `sync_engine.py` normalizes everything to naive-UTC internally (`_to_naive_utc`) and re-attaches the offset only when serializing to JSON (`_to_iso`). If you add new datetime handling anywhere touching the DB, follow this pattern or comparisons will silently misbehave (or crash on naive/aware comparison).
- **Day boundaries follow the user's profile timezone, not device/server clock.** `log_date` is resolved server-side (and equivalently client-side in mobile) using `user_profiles.timezone`, precisely so a dashboard's "today" and the server's log-bucketing never disagree. If you add a new "what day is it" computation anywhere, resolve it the same way (see `server/app/routers/logs.py:_resolve_log_date`, `web/src/pages/DashboardPage.tsx:todayInTimezone`, `mobile/src/lib/dates.ts`).
- **Expo Router auth guards need explicit `<Redirect>`.** Conditionally omitting `<Stack.Screen>` entries in the root layout does *not* reliably block navigation to an already-resolved route — it looks like it works until it doesn't. Guard each protected group/screen itself (see `mobile/src/app/(tabs)/_layout.tsx` and `login.tsx`).
- **Mobile local food search must be scoped to the current user.** A custom food's local cache row can outlive the account that created it (e.g. account switch on the same device). Unscoped search can surface another account's custom food, which then gets logged and can never sync (server correctly refuses to accept data claiming another user's ownership). See `ownedOrShared()` in `mobile/src/db/repo/foods.ts`.
- **FastAPI validation-error `detail` is sometimes an array**, not a string (422 responses use Pydantic's `[{loc, msg, type}, ...]` shape). Both web and mobile API clients have a `formatErrorDetail`-style helper for this — don't naively do `setError(err.message)` from a raw fetch without going through the shared client.
- **LLM features on mobile only see server-side data.** A freshly logged entry may still be local-only under the offline-first model. `mealReview`/`analysisDaily` on mobile call `runSync()` first — don't remove that or "just logged this" will silently show empty nutrition data.
- **passlib + bcrypt 5.x are incompatible** (a passlib internal self-test breaks). Pinned to `bcrypt==4.0.1` in `server/requirements.txt` — don't bump bcrypt without checking this.

## Where things live

- Server: `app/models` (SQLAlchemy), `app/schemas` (Pydantic), `app/routers`, `app/services` (`sync_engine.py`, `nutrition_calc.py`, `food_lookup.py`, `recipe_calc.py`, `auth_service.py`), `app/llm` (provider adapters), `alembic/versions` (migrations, including seed-data migrations for `nutrient_reference` and `rda_targets`).
- Web: `src/api` (typed HTTP client per resource), `src/pages`.
- Mobile: `src/db/schema.ts` (Drizzle schema), `src/db/repo` (local-DB operations, including `sync.ts`'s dirty-scan/apply logic), `src/lib/sync.ts` (top-level sync orchestrator + conflict resolution), `src/app` (Expo Router file-based routes; `(tabs)` group is the authenticated area).

## LLM adapter

Pluggable, fully optional (`LLM_PROVIDER=none` default, app is 100% usable without it). Providers: `none`, `anthropic`, `openai`, `ollama` (point at a LAN machine, e.g. a Mac mini — **not** the Pi, too weak), `cohere` (added because that's the API key available to test with during development; fully implemented and live-verified, unlike anthropic/openai/ollama which are implemented but not live-tested). All providers implement `LLMProvider` in `server/app/llm/base.py`; all failures raise `LLMUnavailableError` → uniform 503 `{error: "llm_unavailable", message}` both clients check for. The LLM **never does arithmetic** — `nutrition_calc.py` computes nutrient gaps in plain Python; the model only narrates a pre-computed report.

## Running things

```bash
# server
cd server && .venv/bin/pip install -r requirements-dev.txt
DATABASE_URL="sqlite:///./caltrack_dev.db" .venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./caltrack_dev.db" JWT_SECRET=dev-secret .venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest tests/                       # 29 tests, sync_engine + nutrition_calc + food_lookup

# web
cd web && npm run dev                          # points at localhost:8000 by default
npx tsc -b --noEmit                            # typecheck

# mobile (needs Expo Go on a phone on the same LAN, matching its supported SDK — check Expo Go's own "About" screen if you hit a version-mismatch error)
cd mobile && npx expo start
npx tsc --noEmit                               # typecheck
```

## What's genuinely untested/unverified

- `docker compose up` has never actually been run (developed on a Mac with no Docker installed) — the Dockerfiles follow standard patterns but haven't been walked through end-to-end.
- No test coverage for FastAPI routers or the web/mobile clients themselves (only the server's `services/` layer has automated tests).
- The self-hosting guide (`docs/self-hosting.md`) hasn't been validated against a real Raspberry Pi.
- OCR nutrition-label scanning is implemented and code-reviewed but was never exercised with a real photo in testing (meal-review and period-analysis were, live, with a real Cohere key, and they share the same request/parsing code path).

## License

AGPL-3.0 — deliberate choice so a hosted-SaaS fork has to contribute back. Don't suggest MIT without flagging that this was an explicit decision.
