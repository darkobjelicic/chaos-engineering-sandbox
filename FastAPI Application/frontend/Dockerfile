FROM node:18-alpine
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* ./
# use legacy-peer-deps to avoid Vite / plugin peer dependency conflicts in CI build
RUN if [ -f yarn.lock ]; then yarn --frozen-lockfile; elif [ -f package-lock.json ]; then npm ci --legacy-peer-deps; else npm i --legacy-peer-deps; fi
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
