# ==========================================
# 1️⃣ Dependencies
# ==========================================
FROM node:20-alpine AS deps

WORKDIR /app

# Ensure openssl compatibility (required for some node libs)
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json ./

# Deterministic install
RUN npm ci --omit=dev


# ==========================================
# 2️⃣ Builder
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app
ENV NODE_ENV=production

RUN apk add --no-cache libc6-compat

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Ensure standalone output is enabled in next.config.js
RUN npm run build


# ==========================================
# 3️⃣ Runtime (Hardened)
# ==========================================
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Add minimal runtime deps
RUN apk add --no-cache libc6-compat curl

# Create non-root user
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

# Copy standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Fix ownership
RUN chown -R nextjs:nextjs /app

USER nextjs

EXPOSE 3000

# Healthcheck for ECS
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3000/healthz || exit 1

# Proper signal handling
CMD ["node", "server.js"]
