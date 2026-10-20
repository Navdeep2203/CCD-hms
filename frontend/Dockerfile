
# Pin the Node major/minor release line and Debian variant for a predictable build environment.
# Dependabot proposes image-tag updates through PRs so upgrades can be reviewed.
FROM node:24.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency manifests first so dependency installation can use Docker layer caching.
# npm ci installs the exact dependency tree recorded in package-lock.json.
COPY package-lock.json /app/
COPY package.json /app/

RUN npm ci

# Copy application inputs explicitly to keep the build context intentional.
# Add any new build inputs (for example, public/ or additional config files) here.
COPY src/ /app/src
COPY index.html /app/index.html
COPY vite.config.js /app/vite.config.js

# Vite embeds VITE_API_BASE into the generated client-side bundle at build time.
# ARG is sufficient; a runtime ENV cannot change a URL already compiled into the bundle.
ARG VITE_API_BASE

# Fail fast rather than accidentally producing a build with a missing API URL
# and relying on the application's localhost fallback.
RUN test -n "$VITE_API_BASE" || { echo "ERROR: VITE_API_BASE value missing" >&2; exit 1; }

RUN npm run build

# Use a versioned, unprivileged NGINX image for the runtime stage.
# Only the generated static site is copied in; Node.js and npm stay in the builder.
# Dependabot proposes image-tag updates through PRs for review.
FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24 AS production

# Copy only Vite's production output, keeping source files and dependencies out of runtime.
COPY --from=builder /app/dist/ /usr/share/nginx/html/

# Replace the default site config with our SPA routing, caching, and compression rules.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Document the port used by the unprivileged NGINX image; this does not publish it.
EXPOSE 8080

# The Alpine-based image provides wget, which can be used for a lightweight health check.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
