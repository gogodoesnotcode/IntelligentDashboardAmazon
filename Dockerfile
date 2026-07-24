# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY agent ./agent
COPY --from=frontend-build /frontend/dist ./frontend/dist
ENV ENV=prod
# Container layout differs from the local repo layout (backend/app/core/config.py's
# relative defaults assume the local repo tree) — point both explicitly here.
ENV ANALYZED_DATA_DIR=/app/agent/data/analyzed
ENV FRONTEND_DIST_DIR=/app/frontend/dist
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
