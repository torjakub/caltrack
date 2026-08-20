# calTrack web

React (Vite) thin client for calTrack — used on the home network (e.g. laptop browser). Talks directly to the `/server` API; no offline logic (that's `/mobile`'s job).

## Dev

```bash
npm install
npm run dev
```

By default it targets `http://localhost:8000`. Override with `VITE_API_BASE_URL` in a local `.env` file, or via `public/config.js` at runtime (see the Dockerfile — this is how the built image is pointed at the Pi's LAN address without a rebuild).

## Build

```bash
npm run build
```
