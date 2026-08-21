# Self-hosting

*Status: the Dockerfiles/compose config follow standard patterns and the app itself is verified working, but this guide hasn't yet been walked through end-to-end against a real Raspberry Pi (developed and tested on a Mac without Docker installed). If something here doesn't match reality, please open an issue.*

## Requirements

- A Raspberry Pi (or any always-on Linux machine on your home network) with Docker and Docker Compose installed.
- Optionally, a second machine on the same network running [Ollama](https://ollama.com) if you want local-LLM features without calling a cloud API (see [`llm-providers.md`](llm-providers.md)).

## Setup

```bash
git clone <your fork/clone of this repo>
cd calTrack
cp .env.example .env
```

Edit `.env`:
- Set `JWT_SECRET` to a long random string.
- Optionally set `USDA_FDC_API_KEY` (free, from https://fdc.nal.usda.gov/api-key-signup.html) — Open Food Facts barcode lookup works without any key.
- Leave `LLM_PROVIDER=none` unless you want LLM features (see [`llm-providers.md`](llm-providers.md)).
- Set `API_BASE_URL` and `CORS_ALLOWED_ORIGINS` to match how you'll reach the Pi on your LAN (e.g. `http://caltrack.local:8000`).

Then:

```bash
docker compose up -d
```

- API: `http://<pi-ip>:8000`
- Web app: `http://<pi-ip>:5173`

On first run, open the web app and use "First-time setup" to create the initial account (this calls `POST /api/v1/auth/setup`, which only works while the database has zero users — so only the first person to open the app can create an account this way).

## Backup and restore

The entire database is one file at `./data/caltrack.db` (bind-mounted from the `server` container). Back it up with:

```bash
mkdir -p ./backups
sqlite3 ./data/caltrack.db ".backup './backups/caltrack-$(date +%F).db'"
```

Do this instead of copying the file directly while the server is running, to avoid grabbing it mid-write.

To restore, stop the stack, replace the file, then start it back up:

```bash
docker compose down
cp ./backups/caltrack-2026-08-21.db ./data/caltrack.db
docker compose up -d
```

## Mobile app

The mobile app is a separate Expo build, not part of `docker compose`. Point it at your server's LAN address on first login. See `/mobile/README.md` (added in milestone M3) for build/install instructions.
