FROM python:3-slim AS backend-build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/
COPY backend /app/backend

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

FROM node:26-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json /app/
RUN npm install
COPY frontend /app
RUN npm run build

FROM python:3-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TEMPVERITY_DB_PATH=/data/tempverity.sqlite3 \
    TEMPVERITY_DATA_DIR=/data

WORKDIR /app

COPY --from=backend-build /usr/local /usr/local
COPY --from=backend-build /app/backend /app/backend
COPY --from=frontend-build /app/dist /app/frontend/dist

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
