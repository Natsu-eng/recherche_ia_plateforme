# ═══════════════════════════════════════════════════════════════════════════════
# DOCKERFILE - Plateforme R&D Béton IA (VERSION OPTIMISÉE)
# Base: Python 3.11 Slim
# Auteur: Stage R&D - IMT Nord Europe
# Version: 2.0.0
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# ─── MÉTADONNÉES ───
LABEL maintainer="support@imt-nord-europe.fr" \
      version="2.0.0" \
      description="Plateforme R&D Béton avec IA - IMT Nord Europe"

# ─── VARIABLES D'ENVIRONNEMENT ───
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ─── INSTALLATION DÉPENDANCES SYSTÈME ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ─── RÉPERTOIRE DE TRAVAIL ───
WORKDIR /app

# ─── COPIE REQUIREMENTS & INSTALLATION ───
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ─── COPIE CODE SOURCE (SÉLECTIF) ───
COPY app/ ./app/
COPY config/ ./config/
COPY database/ ./database/
COPY pages/ ./pages/
COPY assets/ ./assets/
COPY app.py .

# ─── CRÉATION DOSSIERS NÉCESSAIRES ───
RUN mkdir -p logs ml_models/production .streamlit

# ─── CONFIGURATION STREAMLIT ───
RUN echo '[server]\n\
headless = true\n\
port = 8501\n\
address = "0.0.0.0"\n\
enableCORS = false\n\
enableXsrfProtection = true\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
\n\
[theme]\n\
base = "light"\n\
primaryColor = "#1e3c72"\n\
backgroundColor = "#ffffff"\n\
secondaryBackgroundColor = "#f0f2f6"\n\
textColor = "#262730"\n\
' > .streamlit/config.toml

# ─── PERMISSIONS ───
RUN chmod -R 755 /app

# ─── UTILISATEUR NON-ROOT (sécurité) ───
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# ─── EXPOSITION PORT ───
EXPOSE 8501

# ─── HEALTHCHECK ───
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ─── COMMANDE DE DÉMARRAGE ───
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.fileWatcherType=none"]