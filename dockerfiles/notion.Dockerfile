# Generated by https://smithery.ai. See: https://smithery.ai/docs/config#dockerfile
# Use the official Node.js image as the base image
FROM node:22-alpine AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY notion/package.json notion/package-lock.json ./

# Install the dependencies
RUN npm install --ignore-scripts

# Copy the rest of the application source code
COPY notion ./

# Build the application
RUN npm run build

# Use a separate runtime environment
FROM node:22-alpine

# Set the working directory
WORKDIR /app

# Copy built files from the builder stage
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json /app/package-lock.json ./

# Expose the port the app runs on
# (This line is optional and depends on whether you want to specify a port to be exposed)

RUN apk add git \
    && npm install -g pnpm \
    && pnpm install https://github.com/beamlit/supergateway

# Command to run the application
ENTRYPOINT ["npx","-y","@blaxel/supergateway","--port","80","--stdio"]