FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Python Backend ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into backend/static
COPY --from=frontend-build /app/frontend/dist ./backend/static

# Expose port 5000 (matches HF Space app_port)
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST=/app/backend/static
ENV FLASK_HOST=0.0.0.0
ENV HOST=0.0.0.0
ENV PORT=5000

# Start the app
CMD ["python", "backend/app.py"]
