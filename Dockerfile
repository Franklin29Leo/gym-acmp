# ---------- 1) compila el frontend ----------
FROM node:22-alpine AS front
WORKDIR /front
COPY front/package.json front/package-lock.json ./
RUN npm ci
COPY front/ ./
RUN npm run build

# ---------- 2) API FastAPI + frontend compilado ----------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=America/Lima
WORKDIR /srv/back
COPY back/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY back/app ./app
COPY back/crear_bd.py .
# main.py busca el frontend en ../front/dist
COPY --from=front /front/dist /srv/front/dist
RUN useradd --system --no-create-home gym && chown -R gym /srv
USER gym
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
