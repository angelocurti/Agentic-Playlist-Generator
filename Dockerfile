# ===========================================
# VIBE.AI - Multi-stage Dockerfile
# ===========================================

# --- Stage 1: Python Backend ---
FROM python:3.11-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY src/ ./src/

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run API
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]


# --- Stage 2: Node.js Frontend ---
FROM node:18-alpine as frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY app/ ./app/
COPY next.config.js tsconfig.json tailwind.config.js postcss.config.js ./

# Build Next.js
RUN npm run build


# --- Stage 3: Frontend Production ---
FROM node:18-alpine as frontend

WORKDIR /app

# Copy built files
COPY --from=frontend-builder /app/.next ./.next
COPY --from=frontend-builder /app/node_modules ./node_modules
COPY --from=frontend-builder /app/package.json ./

EXPOSE 3000

CMD ["npm", "start"]

