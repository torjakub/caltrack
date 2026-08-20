#!/bin/sh
# Writes config.js from API_BASE_URL at container start, so the same built
# image works regardless of the Pi's LAN IP (nginx's stock entrypoint runs
# every /docker-entrypoint.d/*.sh script before starting nginx).
set -e

cat > /usr/share/nginx/html/config.js <<EOF
window.__CALTRACK_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL:-}",
};
EOF
