# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Install serve for static file serving
RUN npm install -g serve

# Copy built assets
COPY --from=builder /app/dist ./dist
COPY entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 3001

# Start the app
CMD ["./entrypoint.sh"]
