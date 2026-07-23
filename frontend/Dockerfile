FROM node:22-alpine AS deps

WORKDIR /app

COPY package.json pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN corepack enable \
    && pnpm install

FROM node:22-alpine AS runtime

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/frontend/node_modules ./frontend/node_modules
COPY package.json pnpm-workspace.yaml ./
COPY frontend ./frontend

WORKDIR /app/frontend

EXPOSE 3000

CMD ["pnpm", "dev"]

