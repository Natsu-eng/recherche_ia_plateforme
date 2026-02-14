# 🏗️ Plateforme R&D Béton IA - IMT Nord Europe

> **Système d'aide à la décision pour la formulation du béton utilisant l'Intelligence Artificielle**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-green.svg)](https://xgboost.readthedocs.io/)
[![License](https://img.shields.io/badge/License-IMT-orange.svg)](LICENSE)

---

## 📋 Table des Matières

- [Vue d'Ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Configuration](#️-configuration)
- [Déploiement](#-déploiement)
- [Structure du Projet](#-structure-du-projet)
- [Documentation Technique](#-documentation-technique)
- [Contribution](#-contribution)
- [Licence](#-licence)

---

## 🎯 Vue d'Ensemble

Cette plateforme permet de **prédire les propriétés du béton** et **d'optimiser les formulations** selon vos objectifs (coût, empreinte carbone, performance).

### Modèle IA

- **Algorithme** : XGBoost (MultiOutputRegressor)
- **Cibles** : 3 propriétés simultanées
  - Résistance en compression (MPa)
  - Coefficient de diffusion des chlorures (×10⁻¹² m²/s)
  - Profondeur de carbonatation (mm)
- **Performance** :
  - R² Résistance : **0.93+**
  - R² Diffusion Cl⁻ : **0.96+**
  - R² Carbonatation : **0.97+**

### Normes & Validation

- ✅ **EN 206** : Spécification, performance, production du béton
- ✅ **EN 197-1** : Ciments
- ✅ **EN 450-1** : Cendres volantes
- ✅ **Loi d'Abrams** : Validation physique E/C vs Résistance

---

## ✨ Fonctionnalités

### 1️⃣ **Formulateur** 📊
- Saisie intuitive via sliders
- Prédiction temps réel (3 cibles)
- Validation normative automatique
- Export CSV/PDF

### 2️⃣ **Laboratoire** 🧪
- Analyse de sensibilité paramétrique
- Calcul d'élasticités
- Visualisations interactives

### 3️⃣ **Comparateur** ⚖️
- Benchmark jusqu'à 10 formulations
- Coordonnées parallèles
- Tableaux comparatifs

### 4️⃣ **Optimiseur** 🎯
- Algorithme génétique
- Multi-objectifs : Coût / CO₂ / Résistance
- Contraintes personnalisables

### 5️⃣ **Analyse de Données** 📈
- Historique des prédictions
- Tendances et statistiques
- Détection d'outliers

### 6️⃣ **Configuration** ⚙️
- Diagnostics système
- Tests modèle ML
- Monitoring base de données

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   STREAMLIT APP                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Formulateur │  │ Optimiseur  │  │  Analytics  │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                 │                 │            │
├─────────┴─────────────────┴─────────────────┴───────────┤
│                    CORE LOGIC                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Predictor │  │Optimizer │  │Validator │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │              │                    │
├───────┴─────────────┴──────────────┴───────────────────┤
│                MODÈLE XGBOOST                            │
│  ┌──────────────────────────────────────────┐          │
│  │ MultiOutputRegressor (3 cibles)          │          │
│  │ • Résistance                             │          │
│  │ • Diffusion Cl⁻                          │          │
│  │ • Carbonatation                          │          │
│  └──────────────────────────────────────────┘          │
├─────────────────────────────────────────────────────────┤
│              BASE DE DONNÉES PostgreSQL                  │
│  ┌──────────────────────────────────────────┐          │
│  │ • predictions                            │          │
│  │ • formulations_favorites                 │          │
│  │ • sessions_utilisateurs                  │          │
│  └──────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prérequis

- **Python** 3.11+
- **PostgreSQL** 15+ (optionnel mais recommandé)
- **Git**

### Étape 1 : Cloner le Projet

```bash
git clone https://github.com/imt-nord-europe/concrete-ai-platform.git
cd concrete-ai-platform
```

### Étape 2 : Environnement Virtuel

```bash
# Créer l'environnement
python3 -m venv venv

# Activer
source venv/bin/activate  # Linux/Mac
# OU
venv\Scripts\activate  # Windows
```

### Étape 3 : Installer les Dépendances

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Étape 4 : Configurer `.env`

Créez un fichier `.env` à la racine :

```env
DATABASE_URL=postgresql://app_beton:Passer123@localhost:5432/concrete_ai_platform
```

### Étape 5 : Modèle ML

Assurez-vous que les fichiers du modèle sont présents dans `ml_models/production/` :
- `best_model.joblib`
- `features.joblib`
- `metadata.json`

---

## 🎮 Utilisation

### Méthode 1 : Streamlit Direct

```bash
streamlit run app.py --server.port=8501
```

Accès : **http://localhost:8501**

### Méthode 2 : Makefile

```bash
make run
```

### Méthode 3 : Docker Compose (Recommandé)

```bash
docker-compose up -d
```

Services démarrés :
- Application : **http://localhost:8501**
- PostgreSQL : **localhost:5432**

---

## ⚙️ Configuration

### Streamlit

Fichier : `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#1e3c72"  # Bleu IMT
backgroundColor = "#ffffff"
```

### Application

Fichier : `config/settings.py`

```python
APP_SETTINGS = {
    'app_name': 'Plateforme R&D Béton IA',
    'version': '1.0.0',
    # ...
}
```

### Base de Données

Fichier : `.env`

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

---

## 🐳 Déploiement

### Docker

#### Build

```bash
docker build -t concrete-ai-platform .
```

#### Run

```bash
docker run -p 8501:8501 \
  -v $(pwd)/ml_models:/app/ml_models \
  --env-file .env \
  concrete-ai-platform
```

### Docker Compose

```bash
# Démarrer
docker-compose up -d

# Voir logs
docker-compose logs -f

# Arrêter
docker-compose down
```

### Production

1. **Variables d'environnement** : Utiliser secrets management (Vault, AWS Secrets Manager)
2. **HTTPS** : Reverse proxy (Nginx, Traefik)
3. **Monitoring** : Prometheus + Grafana
4. **Backup DB** : Automatisé quotidien

---

## 📁 Structure du Projet

```
concrete-ai-platform/
├── app.py                      # Point d'entrée principal
├── requirements.txt            # Dépendances Python
├── Dockerfile                  # Image Docker
├── docker-compose.yml          # Orchestration
├── Makefile                    # Commandes utiles
├── .env                        # Variables d'environnement
│
├── .streamlit/
│   └── config.toml             # Configuration Streamlit
│
├── app/
│   ├── components/             # Composants UI réutilisables
│   │   ├── sidebar.py
│   │   ├── cards.py
│   │   ├── forms.py
│   │   └── charts.py
│   │
│   ├── core/                   # Logique métier
│   │   ├── predictor.py        # ⭐ Prédiction ML
│   │   ├── optimizer.py        # Algorithme génétique
│   │   ├── analyzer.py         # Analyses statistiques
│   │   └── validator.py        # Validation normes
│   │
│   ├── models/                 # Gestion modèles ML
│   │   ├── loader.py
│   │   └── model_config.py
│   │
│   ├── pages/                  # Pages Streamlit
│   │   ├── 1_📊_Formulateur.py
│   │   ├── 2_🧪_Laboratoire.py
│   │   ├── 3_⚖️_Comparateur.py
│   │   ├── 4_🎯_Optimiseur.py
│   │   ├── 5_📈_Analyse_de_Données.py
│   │   └── 6_⚙️_Configuration.py
│   │
│   └── styles/                 # Thème personnalisé
│       └── theme.py
│
├── config/
│   ├── constants.py            # Constantes métier
│   └── settings.py             # Configuration globale
│
├── database/
│   └── manager.py              # Gestionnaire PostgreSQL
│
├── ml_models/
│   └── production/             # ⭐ Modèles entraînés
│       ├── best_model.joblib
│       ├── features.joblib
│       └── metadata.json
│
├── logs/                       # Logs application
│
└── tests/                      # Tests unitaires
    ├── test_predictor.py
    ├── test_validator.py
    └── test_optimizer.py
```

---

## 📚 Documentation Technique

### Ordre des Features (CRITIQUE)

⚠️ **NE JAMAIS MODIFIER** sans réentraîner le modèle.

```python
MODEL_FEATURES_ORDER = [
    'Eau', 'GravilonsGros', 'Ratio_E_L', 'Sqrt_Age',
    'SableFin', 'Eau_x_SP', 'Log_Age', 'Pct_Laitier',
    'Liant_x_RatioEL', 'Laitier', 'Ciment',
    'Ratio_Granulats', 'Age', 'CendresVolantes',
    'Ciment_x_LogAge'
]
```

### Feature Engineering

Généré automatiquement par `predictor.engineer_features()` :

- `Ratio_E_L` : Eau / Liant Total
- `Pct_Laitier` : Laitier / Liant Total
- `Log_Age` : log(Age + 1)
- `Sqrt_Age` : √Age
- `Ciment_x_LogAge` : Ciment × Log_Age
- `Eau_x_SP` : Eau × Superplastifiant
- `Liant_x_RatioEL` : Liant Total × Ratio E/L
- `Ratio_Granulats` : (Gravillons + Sable) / Volume Total

### API Principale

```python
from app.core.predictor import predict_concrete_properties

composition = {
    'Ciment': 350.0,
    'Laitier': 60.0,
    'CendresVolantes': 0.0,
    'Eau': 175.0,
    'Superplastifiant': 4.0,
    'GravilonsGros': 1070.0,
    'SableFin': 710.0,
    'Age': 28.0
}

predictions = predict_concrete_properties(
    composition=composition,
    model=model,
    feature_list=features
)

# Résultat :
# {
#     'Resistance': 52.95,
#     'Diffusion_Cl': 2.02,
#     'Carbonatation': 21.13,
#     'Ratio_E_L': 0.427,
#     'Liant_Total': 410.0,
#     'Pct_Substitution': 0.146
# }
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
make test

# Avec couverture
make test-cov

# Test spécifique
pytest tests/test_predictor.py -v
```

---

## 🤝 Contribution

### Workflow

1. Fork le projet
2. Créer une branche (`git checkout -b feature/ma-feature`)
3. Commit (`git commit -m 'Ajout fonctionnalité'`)
4. Push (`git push origin feature/ma-feature`)
5. Ouvrir une Pull Request

### Standards

- **Code** : Black (line-length=100)
- **Linting** : Flake8
- **Tests** : Pytest (couverture > 80%)
- **Docstrings** : Google Style

---

## 📞 Support

- **Email** : support@imt-nord-europe.fr
- **Documentation** : [Wiki interne](https://wiki.imt-nord-europe.fr)
- **Issues** : [GitHub Issues](https://github.com/imt-nord-europe/concrete-ai-platform/issues)

---

## 📜 Licence

© 2026 **IMT Nord Europe** - Tous droits réservés.

Usage académique et de recherche uniquement.

---

## 🙏 Remerciements

- **IMT Nord Europe** - Infrastructure et support
- **Département Génie Civil** - Expertise métier
- **Streamlit** - Framework UI
- **XGBoost** - Modèle ML performant

---

**Développé avec ❤️ par l'équipe R&D - IMT Nord Europe**

*Version 1.0.0 - Février 2026*