# Build from repository root:
#   docker build -f frontend/Dockerfile -t jobmate-frontend .
FROM node:20-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Copy .env (and .env.example fallback) from repository root so Vite reads VITE_* settings
COPY .env* ./

ARG VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime

WORKDIR /app

# Copy .env outside public webroot (/usr/share/nginx/html)
COPY .env* /app/
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh

EXPOSE 33340

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:33340/healthz || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
