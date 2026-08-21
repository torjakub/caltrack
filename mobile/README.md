# calTrack mobile

React Native (Expo) app for calTrack — **offline-first**: keeps its own local SQLite database as the source of truth on-device, so logging food works with zero connectivity. Syncs with `/server` once the sync engine lands (see `docs/sync-protocol.md` at the repo root); for now, everything logged here stays local to the device.

## Dev

Requires Expo Go on your phone (same Wi-Fi network as this machine), matching the SDK version in `package.json` — check Expo Go's own "supported SDK" info (usually under Settings/About in the app) if you hit a version-incompatibility error.

```bash
npm install
npx expo start
```

Scan the QR code, or manually enter `exp://<this-machine's-LAN-IP>:8081` in Expo Go. On first launch, enter your calTrack server's LAN address (e.g. `http://192.168.1.50:8000`).

## Local database

Schema lives in `src/db/schema.ts` (Drizzle ORM + expo-sqlite). After changing it:

```bash
npm run db:generate
```

This regenerates `src/db/migrations/`, which the app applies automatically on startup via `useMigrations` in `src/app/_layout.tsx`.

## What works today (no sync yet)

- Login / first-time setup against your server
- One-time bootstrap pull of profile + targets after login
- Food search (local cache, plus a live server fallback that caches results) and barcode lookup
- Custom foods and meal logging — written straight to the local database, works fully offline
- Dashboard showing today's totals vs. targets

Recipes, profile editing, and syncing logged entries back to the server all land with the sync engine (M4).
