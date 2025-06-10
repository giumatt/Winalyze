# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Enable corepack and install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy only lockfile and manifest for caching
COPY frontend/pnpm-lock.yaml frontend/package.json ./

# Install dependencies
RUN pnpm install

# Copy the rest of the frontend files
COPY frontend/ .

# Build the frontend
RUN pnpm run build

# Serve stage
FROM nginx:alpine

# Copy built frontend to Nginx HTML folder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80