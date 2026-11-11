#!/bin/sh
set -eu

PROXY_INC="/etc/nginx/conf.d/api-proxy.inc"
: > "$PROXY_INC"

if [ -n "${API_PROXY_URL:-}" ]; then
  CLEAN_URL="${API_PROXY_URL%/}"
  cat > "$PROXY_INC" <<EOF
location /api/ {
    proxy_pass ${CLEAN_URL};
    proxy_http_version 1.1;
    proxy_set_header Host \$http_host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_connect_timeout 15s;
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
}
EOF
fi

exec nginx -g "daemon off;"
