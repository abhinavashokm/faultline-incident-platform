# ── Dev stage ─────────────────────────────────────────────────────────────────
FROM node:20-slim AS dev

WORKDIR /app

# Pre-create runtime dirs owned by node so volumes inherit the right owner
RUN mkdir -p /app/.next /app/node_modules && chown -R node:node /app

USER node

# Copy package manifests and install dependencies as node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

# Source is bind-mounted from host at runtime for HMR.
# node_modules are kept in a named volume so host bind-mount does not shadow them.

EXPOSE 3000

CMD ["npm", "run", "dev"]