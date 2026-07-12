FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC vars must be available at build time.
# Preferred: set NEXT_PUBLIC_API_GATEWAY to a single LB/gateway URL.
# Legacy: per-service URLs still supported for backward compatibility.
ARG NEXT_PUBLIC_API_GATEWAY
ARG NEXT_PUBLIC_API_EXECUTE
ARG NEXT_PUBLIC_API_CALLBACK
ARG NEXT_PUBLIC_API_CANALES
ARG NEXT_PUBLIC_API_TASKS
ENV NEXT_PUBLIC_API_GATEWAY=$NEXT_PUBLIC_API_GATEWAY
ENV NEXT_PUBLIC_API_EXECUTE=$NEXT_PUBLIC_API_EXECUTE
ENV NEXT_PUBLIC_API_CALLBACK=$NEXT_PUBLIC_API_CALLBACK
ENV NEXT_PUBLIC_API_CANALES=$NEXT_PUBLIC_API_CANALES
ENV NEXT_PUBLIC_API_TASKS=$NEXT_PUBLIC_API_TASKS
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
RUN mkdir -p ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./app/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./app/public
USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "app/server.js"]
