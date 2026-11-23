FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
 && pip install --no-cache-dir -r requirements.txt \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*
COPY . .
ENV HOST=0.0.0.0 PORT=8770 DATA_DIR=/data SERVER_MODE=1 NO_SANDBOX=1
VOLUME /data
EXPOSE 8770
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8770/ping',timeout=3).read()==b'bilan-ok' else 1)"
CMD ["python3", "serveur.py", "--no-browser"]
