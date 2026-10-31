# Build context: frontend-web/
# docker build -f frontend-web/Dockerfile frontend-web/

# ── Dev stage ─────────────────────────────────────────────────────────────────
FROM node:20-slim AS dev

WORKDIR /app

# Copy package manifests and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Source is bind-mounted from host at runtime for HMR.
# node_modules are kept in a named volume so host bind-mount does not shadow them.

EXPOSE 3000

# Run as the built-in 'node' user (uid 1000)
USER node

CMD ["npm", "run", "dev"]

# ── Prod stage ────────────────────────────────────────────────────────────────
FROM node:20-slim AS prod

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY . .
RUN npm run build

# Create non-root user
RUN addgroup --system nextjs && adduser --system --ingroup nextjs nextjs
RUN chown -R nextjs:nextjs /app

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production

CMD ["npm", "run", "start"]
