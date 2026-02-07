Plateforme R&D Béton IA – IMT Nord Europe
=========================================

### 🎯 Objectif

Cette plateforme Streamlit multi‑pages permet de **formuler, comparer, optimiser et analyser** des bétons à l’aide d’un moteur d’IA (XGBoost / RandomForest) et de lois physiques métiers (ratio E/L, liant total, substitutions cimentaires…).

L’interface est pensée comme un **laboratoire numérique** : jauges, radars, analyses de sensibilité et exports prêts pour les rapports.

---

### 🧱 Structure du projet

- `app/main.py` : point d’entrée Streamlit (page d’accueil / dashboard).
- `app/pages/2_🧪_Formulateur.py` : formulateur IA (jauges, sensibilité, exports CSV/PDF).
- `app/pages/3__Comparateur.py` : comparateur multicritère de formulations.
- `app/pages/4__Laboratoire.py` : laboratoire virtuel (analyses de sensibilité avancées).
- `app/pages/5__Optimiseur.py` : interface de l’optimiseur (coût / CO₂).
- `app/pages/6__Analyse_Donnees.py` : analyse de données expérimentales (CSV/Excel).
- `app/pages/7__Configuration.py` : visualisation et diagnostic de la configuration.
- `app/core/predictor.py` : feature engineering + prédiction des 3 cibles :
  - `Resistance` (MPa),
  - `Diffusion_Cl` (×10⁻¹² m²/s),
  - `Carbonatation` (mm).
- `app/core/optimizer.py` : algorithme génétique simple pour optimiser les mélanges.
- `app/components/charts.py` : jauges, radars et courbes de sensibilité Plotly.
- `config/settings.py` : configuration centrale (chemins, cibles, coûts, CO₂, UI, optimiseur).
- `config/constants.py` : bornes matériaux (`BOUNDS`), prix, émissions CO₂, libellés.
- `ml_models/production/` : dossier attendu pour `best_model.pkl`, `features.pkl`, `metadata.json`.

---

### 🚀 Démarrage en local

1. **Créer et activer un environnement virtuel** (facultatif mais recommandé) :

```bash
python -m venv env
env\Scripts\activate  # Windows
```

2. **Installer les dépendances** :

```bash
pip install -r requirements.txt
```

3. **Placer les modèles de production** :

Mettre au minimum :

- `ml_models/production/best_model.pkl`
- `ml_models/production/features.pkl`
- `ml_models/production/metadata.json` (optionnel mais recommandé)

4. **Lancer l’application** :

```bash
streamlit run app/main.py
```

---

### ⚙️ Variables d’environnement utiles

Il n’y a pas (pour l’instant) de fichier `.env` versionné, mais les variables suivantes peuvent être définies (localement ou via Docker / Vercel) :

- `STREAMLIT_SERVER_PORT` : port HTTP de Streamlit (par défaut `8501`).
- `APP_LOG_LEVEL` : niveau de log global (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `PROJECT_ROOT`, `MODELS_DIR`, `DATA_DIR`, `LOGS_DIR` : chemins spécifiques si besoin de surcharger les valeurs par défaut de `config/settings.py`.

---

### 🐳 Déploiement Docker

Un `Dockerfile` et un `docker-compose.yml` sont fournis.

- **Build de l’image** :

```bash
docker build -t concrete-ai-platform .
```

- **Lancement via docker-compose** :

```bash
docker-compose up --build
```

Par défaut, l’application sera disponible sur `http://localhost:8501`.

Les dossiers suivants sont montés comme volumes (persistants) :

- `./ml_models` → `/app/ml_models`
- `./database` → `/app/database`
- `./logs` → `/app/logs`

---

### 🧪 Cohérence avec le dataset

Les noms de colonnes utilisés dans tout le code sont alignés avec le dataset :

- Entrées (kg/m³) :
  - `Ciment`, `Laitier`, `CendresVolantes`, `Eau`, `Superplastifiant`,
    `GravilonsGros`, `SableFin`, `Age`
- Cibles de prédiction (`MODEL_SETTINGS["targets"]`) :
  - `Resistance`, `Diffusion_Cl`, `Carbonatation`

Les mêmes noms sont utilisés dans :

- `config/constants.py` (`BOUNDS`, coûts, CO₂),
- `config/settings.py` (`MODEL_SETTINGS`, `OPTIMIZER_SETTINGS`),
- `app/core/predictor.py` (feature engineering + inférence),
- `app/core/optimizer.py` (optimisation),
- toutes les pages Streamlit (Formulateur, Comparateur, Optimiseur, Laboratoire).

---

### 🧭 Navigation fonctionnelle

Une fois l’app lancée, la navigation se fait via le **menu latéral Streamlit** :

- **Accueil (`main.py`)** : vue d’ensemble, stats et description des modules.
- **🧪 Formulateur** : saisie de formulation, prédictions, jauges, sensibilité, exports.
- **📊 Comparateur** : panel de plusieurs formulations et radar multicritère.
- **🔬 Laboratoire** : sandbox d’analyse de sensibilité (paramètre vs résistance & E/L).
- **🎯 Optimiseur** : optimisation coût / CO₂ sous contrainte de résistance.
- **📈 Analyse des données** : import CSV/Excel et exploration rapide.
- **⚙️ Configuration** : inspection de la configuration et test de chargement du modèle.


