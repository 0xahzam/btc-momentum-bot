FROM oven/bun:latest
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install
COPY src/ ./src/
COPY tsconfig.json ./
CMD ["bun", "run", "start"]