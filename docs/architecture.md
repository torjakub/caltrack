# Architecture

*Status: implemented and working end-to-end (server, web, mobile, sync, and optional LLM features). Test coverage and a real Raspberry Pi deployment are still outstanding — see the root README's Status section.*

calTrack is three independently deployed components sharing one server-side source of truth:

- **`/server`** — FastAPI + SQLite. Runs on a Raspberry Pi (or any always-on home machine). Owns the canonical database, exposes the REST API, and is the endpoint the mobile app syncs against.
- **`/web`** — React (Vite) SPA. A thin client for use on the home network (e.g. laptop browser). Talks directly to the server API; holds no local database and needs no offline logic.
- **`/mobile`** — React Native (Expo) app. Offline-first: keeps its own local SQLite database as the on-device source of truth, so logging works with zero connectivity. Reconciles with the server via the sync protocol (see [`sync-protocol.md`](sync-protocol.md)) whenever it can reach the server.

## Data flow

```
   [phone, anywhere]              [laptop, home LAN]
   /mobile (local SQLite) -\      /web (no local state)
                             \    /
                          [server: FastAPI + SQLite]  --  Open Food Facts / USDA (food lookup, cached locally)
                             |
                        [LLM provider: none | anthropic | openai | cohere | ollama]
                             |
                     ollama -> separate LAN host (e.g. Mac mini), not the Pi
```

## Why SQLite

Single file, zero-admin, trivial backup (`sqlite3 .backup`), and more than sufficient for single/household-scale write volume. The server is the only writer of record; the mobile app's local SQLite is a separate, independent database reconciled via sync, not a replica.

## LLM adapter

LLM features are entirely optional and decoupled behind a single interface (`server/app/llm/base.py`) so the app is 100% usable with `LLM_PROVIDER=none`. See [`llm-providers.md`](llm-providers.md).
