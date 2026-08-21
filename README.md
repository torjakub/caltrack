# calTrack

A self-hosted, open-source nutrition/calorie tracker — an alternative to Fitatu/MyFitnessPal that runs entirely on your own hardware.

## Why

- **Self-hosted first**: runs on a Raspberry Pi or any home server via Docker Compose. No cloud dependency required.
- **Privacy by default**: all data stays on your network unless you explicitly configure a remote LLM API.
- **Fully usable with zero LLM configured**: manual entry, barcode lookup, and search all work standalone. LLM only adds OCR-assist and meal/day analysis on top.
- **Offline-first mobile**: the mobile app keeps its own local database, so logging works with no connectivity at all — it syncs back to your server whenever it's reachable.

## Architecture

Three components:

- **`/server`** — FastAPI + SQLite backend. Single source of truth, runs on a Raspberry Pi (or any always-on home machine). See [`docs/architecture.md`](docs/architecture.md).
- **`/web`** — React (Vite) web app for use on your home network (e.g. from a laptop). Thin client, talks directly to the server.
- **`/mobile`** — React Native (Expo) app. Offline-first: keeps a local database on-device so you can log food anywhere, then syncs with the server when back on the network. Conflicts (rare, for solo use) are surfaced to you to resolve, git-style — never silently overwritten. See [`docs/sync-protocol.md`](docs/sync-protocol.md).

LLM features (OCR nutrition-label scanning, meal review, daily/weekly nutrient analysis) are entirely optional and pluggable — `none` (default), `anthropic`, `openai`, `cohere`, or `ollama` (point at a local model on your network). See [`docs/llm-providers.md`](docs/llm-providers.md).

## Getting started (self-hosting)

See [`docs/self-hosting.md`](docs/self-hosting.md) for full setup instructions.

```bash
cp .env.example .env
# edit .env with your secrets / API keys
docker compose up
```

`docker compose up` runs `/server` and `/web`. `/mobile` is a separate Expo app, not containerized — see [`mobile/README.md`](mobile/README.md) to build and run it, pointing it at your server's LAN address.

## Status

Core functionality is built and working end-to-end: barcode/search logging, recipes, offline-first mobile with sync and conflict resolution, and optional LLM features. Test coverage is still thin and the self-hosting docs haven't been validated against a real Raspberry Pi deployment yet — treat it as a personal project you can self-host today, not yet a polished 1.0.

## License

[AGPL-3.0](LICENSE) — chosen so that improvements to a self-hosted tool like this flow back to the community, even if someone runs a modified version as a hosted service.
