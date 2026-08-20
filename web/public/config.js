// Overwritten at container start (see Dockerfile entrypoint) so the same
// built image works regardless of the Pi's LAN IP. Falls back to same-origin
// when self-hosted behind a reverse proxy on one host.
window.__CALTRACK_CONFIG__ = {
  API_BASE_URL: "",
};
