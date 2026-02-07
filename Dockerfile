FROM python:3.11-slim

WORKDIR /app

# Installer dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de configuration et de dépendances
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copier le code applicatif
COPY . .

ENV STREAMLIT_SERVER_PORT=8501 \
    PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501"]


