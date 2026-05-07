FROM node:20-alpine AS base

RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

# ── deps target ────────────────────────────────────────────────────────────────
FROM base AS deps
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

# ── development target ─────────────────────────────────────────────────────────
FROM deps AS development
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]

# ── builder target ─────────────────────────────────────────────────────────────
FROM deps AS builder
COPY . .
ENV NEXT_STANDALONE=1
RUN pnpm build

# ── production target ──────────────────────────────────────────────────────────
FROM base AS production
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
