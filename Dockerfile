FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json /frontend/
RUN npm install

COPY frontend /frontend
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN cd /app/backend && uv sync --all-groups

COPY backend /app/backend
COPY scripts /app/scripts
COPY --from=frontend-builder /frontend/out /app/backend/app/static

WORKDIR /app/backend

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
