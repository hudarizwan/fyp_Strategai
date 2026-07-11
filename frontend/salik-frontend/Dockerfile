FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_BASE_URL=http://127.0.0.1:8001
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL     VITE_SUPABASE_URL=$VITE_SUPABASE_URL     VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3   CMD wget -qO- http://127.0.0.1/health >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
