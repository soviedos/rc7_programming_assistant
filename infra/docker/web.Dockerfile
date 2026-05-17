FROM node:22-alpine

WORKDIR /app

COPY apps/web/package.json ./

RUN npm install

COPY apps/web ./

EXPOSE 3000

# Clear Turbopack's incremental cache on every container start to prevent
# stale compiled route handlers (e.g. catch-all proxy returning 404).
CMD ["sh", "-c", "rm -rf .next && npm run dev -- --hostname 0.0.0.0"]
