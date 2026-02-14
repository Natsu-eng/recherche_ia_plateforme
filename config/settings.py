"""
═══════════════════════════════════════════════════════════════════════════════
FICHIER: config/settings.py
Description: Configuration globale de l'application
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CHEMINS PROJET
# ═══════════════════════════════════════════════════════════════════════════════

# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent

# Dossiers principaux
APP_DIR = PROJECT_ROOT / "app"
MODELS_DIR = PROJECT_ROOT / "ml_models" / "production"
DATA_DIR = PROJECT_ROOT / "database"
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGS_DIR = PROJECT_ROOT / "logs"

# Créer les dossiers s'ils n'existent pas
for directory in [MODELS_DIR, DATA_DIR, ASSETS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

APP_SETTINGS = {
    # Informations générales
    "app_name": "Plateforme R&D Béton IA",
    "app_icon": "🏗️",
    "version": "1.0.0",
    "release_date": "2026-01-01",
    
    # Institution
    "institution": "IMT Nord Europe",
    "campus": "Douai, France",
    "department": "Génie Civil & Intelligence Artificielle",
    
    # Contact
    "email": "mailto:support@imt-nord-europe.fr",
    "phone": "+33 (0)3 27 71 22 22",
    "website": "https://imt-nord-europe.fr",
    
    # Fonctionnalités
    "enable_predictions": True,
    "enable_comparisons": True,
    "enable_optimization": True,
    "enable_laboratory": True,
    "enable_analytics": True,
    "enable_exports": True,
    
    # Limites
    "max_predictions_per_session": 100,
    "max_formulations_comparison": 10,
    "max_batch_size": 50,
    "max_file_upload_mb": 10,
    
    # Performance
    "cache_ttl_seconds": 3600,  # 1 heure
    "enable_gpu": False,
    "num_workers": 4,
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION MODÈLES ML
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_SETTINGS = {
    # Chemins modèles
    "model_path": MODELS_DIR / "best_model.pkl",
    "scaler_path": MODELS_DIR / "scaler.pkl",
    "features_path": MODELS_DIR / "features.pkl",
    "metadata_path": MODELS_DIR / "metadata.json",
    
    # Cibles prédiction
    "targets": [
        "Resistance",      # Résistance compression (MPa)
        "Diffusion_Cl",    # Coeff. diffusion chlorures (×10⁻¹² m²/s)
        "Carbonatation"    # Profondeur carbonatation (mm)
    ],
    
    # Unités
    "units": {
        "Resistance": "MPa",
        "Diffusion_Cl": "×10⁻¹² m²/s",
        "Carbonatation": "mm"
    },
    
    # Noms affichage
    "target_names": {
        "Resistance": "Résistance en Compression",
        "Diffusion_Cl": "Diffusion des Chlorures",
        "Carbonatation": "Profondeur de Carbonatation"
    },
    
    # Seuils qualité
    "quality_thresholds": {
        "Resistance": {
            "faible": 25,      # < 25 MPa
            "standard": 35,    # 25-35 MPa
            "haute": 50,       # 35-50 MPa
            "tres_haute": 50   # > 50 MPa
        },
        "Diffusion_Cl": {
            "excellent": 5,    # < 5
            "bon": 8,          # 5-8
            "moyen": 12,       # 8-12
            "faible": 12       # > 12
        },
        "Carbonatation": {
            "excellent": 10,   # < 10 mm
            "bon": 15,         # 10-15 mm
            "moyen": 20,       # 15-20 mm
            "faible": 20       # > 20 mm
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

DATABASE_SETTINGS = {
    "database_path": None,
    "echo": False,  # Afficher les requêtes SQL (debug)
    "pool_size": 10,
    "max_overflow": 20,
    
    # Tables
    "tables": {
        "predictions": "predictions",
        "formulations": "formulations",
        "comparisons": "comparisons",
        "optimizations": "optimizations",
        "users": "users"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════════
import os
from dotenv import load_dotenv

load_dotenv()  # Charge le .env

POSTGRES_SETTINGS = {
    "database_url": os.getenv('DATABASE_URL', 'postgresql://app_beton:Passer123@localhost:5432/concrete_ai_platform'),
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "echo": False
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

UI_SETTINGS = {
    # Thème couleurs (palette IMT Nord Europe)
    "colors": {
        "primary": "#1e3c72",      # Bleu IMT
        "secondary": "#2a5298",    # Bleu clair
        "accent": "#3d5a99",       # Bleu accent
        "success": "#2ca02c",      # Vert
        "warning": "#ff7f0e",      # Orange
        "danger": "#d62728",       # Rouge
        "info": "#17becf",         # Cyan
        "light": "#f0f2f6",        # Gris clair
        "dark": "#262730"          # Gris foncé
    },
    
    # Polices
    "fonts": {
        "main": "Inter, sans-serif",
        "heading": "Poppins, sans-serif",
        "mono": "JetBrains Mono, monospace"
    },
    
    # Tailles
    "font_sizes": {
        "small": "0.875rem",
        "normal": "1rem",
        "large": "1.125rem",
        "xlarge": "1.25rem",
        "heading": "1.5rem"
    },
    
    # Espacements
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem"
    },
    
    # Bordures
    "border_radius": {
        "small": "5px",
        "medium": "10px",
        "large": "15px"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

EXPORT_SETTINGS = {
    "formats": ["CSV", "Excel", "JSON", "PDF"],
    "default_format": "CSV",
    
    # Colonnes export CSV
    "csv_columns": [
        "timestamp",
        "Ciment", "Laitier", "CendresVolantes", "Eau",
        "Superplastifiant", "GravilonsGros", "SableFin", "Age",
        "Resistance", "Diffusion_Cl", "Carbonatation",
        "Ratio_E_L", "Liant_Total"
    ],
    
    # Options PDF
    "pdf_options": {
        "page_size": "A4",
        "orientation": "portrait",
        "include_logo": True,
        "include_charts": True
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

LOGGING_SETTINGS = {
    "log_file": LOGS_DIR / "app.log",
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
    
    # Logs par module
    "loggers": {
        "predictor": "INFO",
        "optimizer": "INFO",
        "database": "WARNING",
        "api": "INFO"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION OPTIMISEUR
# ═══════════════════════════════════════════════════════════════════════════════

OPTIMIZER_SETTINGS = {
    # Algorithme
    "algorithm": "genetic",  # genetic, particle_swarm, bayesian
    
    # Paramètres algorithme génétique
    "genetic_algorithm": {
        "population_size": 100,
        "num_generations": 50,
        "mutation_rate": 0.1,
        "crossover_rate": 0.8,
        "elite_size": 10,
        "tournament_size": 5
    },
    
    # Objectifs disponibles
    "objectives": [
        "maximize_resistance",
        "minimize_cost",
        "minimize_co2",
        "minimize_diffusion_cl",
        "minimize_carbonatation"
    ],
    
    # Coûts matériaux (€/kg)
    "material_costs": {
        "Ciment": 0.12,
        "Laitier": 0.04,
        "CendresVolantes": 0.03,
        "Eau": 0.0001,
        "Superplastifiant": 2.5,
        "GravilonsGros": 0.015,
        "SableFin": 0.015
    },
    
    # Émissions CO₂ (kg CO₂/kg matériau)
    "co2_emissions": {
        "Ciment": 0.9,           # 900 kg CO₂/tonne
        "Laitier": 0.05,         # 50 kg CO₂/tonne
        "CendresVolantes": 0.02, # 20 kg CO₂/tonne
        "Eau": 0.0001,
        "Superplastifiant": 0.5,
        "GravilonsGros": 0.005,
        "SableFin": 0.005
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SÉCURITÉ
# ═══════════════════════════════════════════════════════════════════════════════

SECURITY_SETTINGS = {
    "enable_authentication": False,  # À activer en production
    "session_timeout_minutes": 60,
    "max_login_attempts": 5,
    "password_min_length": 8,
    
    # API keys (à stocker dans variables d'environnement)
    "api_key_enabled": False,
    "api_key_header": "X-API-Key"
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION CACHE
# ═══════════════════════════════════════════════════════════════════════════════

CACHE_SETTINGS = {
    "enable_cache": True,
    "cache_type": "memory",  # memory, redis, file
    "ttl_seconds": 3600,
    
    # Cache par type
    "cache_ttls": {
        "model_predictions": 3600,
        "formulation_history": 7200,
        "statistics": 1800
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_settings():
    """
    Valide la configuration au démarrage de l'application.
    
    Lève une exception si la configuration est invalide.
    """
    # Vérifier chemins critiques
    if not MODEL_SETTINGS["model_path"].exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {MODEL_SETTINGS['model_path']}\n"
            "Veuillez entraîner et exporter le modèle d'abord."
        )
    
    # Vérifier cohérence
    if APP_SETTINGS["max_batch_size"] > APP_SETTINGS["max_predictions_per_session"]:
        raise ValueError(
            "max_batch_size ne peut pas excéder max_predictions_per_session"
        )
    
    print("Configuration validée avec succès")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "APP_SETTINGS",
    "MODEL_SETTINGS",
    "DATABASE_SETTINGS",
    "POSTGRES_SETTINGS",
    "UI_SETTINGS",
    "EXPORT_SETTINGS",
    "LOGGING_SETTINGS",
    "OPTIMIZER_SETTINGS",
    "SECURITY_SETTINGS",
    "CACHE_SETTINGS",
    "validate_settings"
]