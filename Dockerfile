FROM python:3.12-slim

WORKDIR /app

# git is a runtime dependency, not just a build tool: repo_cloner.py shells
# out to it (via GitPython) to shallow-clone repos being analyzed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend

ENV CONTEXTCRAFT_DB_PATH=/data/contextcraft.db
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
