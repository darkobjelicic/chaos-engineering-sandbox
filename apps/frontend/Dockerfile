FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
