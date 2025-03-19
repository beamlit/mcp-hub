FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND noninteractive

# Update and install packages with proper key setup
RUN apt-get update && apt-get install -y git

COPY index.ts /project/index.ts
COPY tsconfig.json /project/tsconfig.json
COPY package.json /project/package.json

WORKDIR /project

RUN npm install && npm run build

RUN npm install -g pnpm \
    && pnpm install https://github.com/beamlit/supergateway

ENTRYPOINT ["npx","-y","@blaxel/supergateway","--port","80","--stdio"]