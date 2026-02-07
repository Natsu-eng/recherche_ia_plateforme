"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/models/model_config.py
Version: 1.0.0 - Synchronisé avec l'ordre réel du modèle (Eau en premier)
═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
from typing import List
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# ORDRE RÉEL DU MODÈLE (SOURCE DE VÉRITÉ ABSOLUE)
# Synchronisé avec feature_names_in_ du Booster XGBoost
# ═══════════════════════════════════════════════════════════════════════════════
MODEL_FEATURES_ORDER = [
    'Eau',                # 0
    'GravilonsGros',      # 1
    'Ratio_E_L',          # 2
    'Sqrt_Age',           # 3
    'SableFin',           # 4
    'Eau_x_SP',           # 5
    'Log_Age',            # 6
    'Pct_Laitier',        # 7
    'Liant_x_RatioEL',    # 8
    'Laitier',            # 9
    'Ciment',             # 10
    'Ratio_Granulats',    # 11
    'Age',                # 12
    'CendresVolantes',    # 13
    'Ciment_x_LogAge'     # 14
]

assert len(MODEL_FEATURES_ORDER) == 15, "Erreur : 15 features attendues"


# Ordre canonique (référence alphabétique - NE PAS UTILISER pour prédiction)
CANONICAL_FEATURES_ORDER = [
    'Age', 'CendresVolantes', 'Ciment', 'Ciment_x_LogAge', 'Eau', 'Eau_x_SP',
    'GravilonsGros', 'Laitier', 'Liant_x_RatioEL', 'Log_Age', 'Pct_Laitier',
    'Ratio_E_L', 'Ratio_Granulats', 'SableFin', 'Sqrt_Age'
]


# Alias pour tolérance aux typos
FEATURE_ALIASES = {
    'GravillosGros': 'GravilonsGros',
    'Gravilons_Gros': 'GravilonsGros',
    'Sable_Fin': 'SableFin',
    'Cendres_Volantes': 'CendresVolantes',
    'LogAge': 'Log_Age',
    'SqrtAge': 'Sqrt_Age'
}


def normalize_feature_name(feature: str) -> str:
    normalized = feature.strip().replace(' ', '_').replace('-', '_')
    return FEATURE_ALIASES.get(normalized, normalized)


# Chemins
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_MODELS_DIR = PROJECT_ROOT / "ml_models" / "production"

MODEL_FILENAME = "best_model.joblib"          
FEATURES_FILENAME = "features.joblib"
METADATA_FILENAME = "metadata.json"


class ModelApproach(Enum):
    BASELINE = "1_Baseline"
    SELECT_FEATURES = "2_SelectFeatures"
    SELECT_OPTIMHP = "3_Select+OptimHP"


DEFAULT_METADATA = {
    'model_name': 'XGBoost',
    'approach': ModelApproach.SELECT_OPTIMHP.value,
    'targets': ['Resistance', 'Diffusion_Cl', 'Carbonatation'],
    'date_trained': '2026-02-07',
    'performance': {'Resistance': 0.93, 'Diffusion_Cl': 0.96, 'Carbonatation': 0.97},
    'features_count': 15
}


def get_feature_order(order_type: str = 'model') -> List[str]:
    if order_type == 'model':
        return MODEL_FEATURES_ORDER.copy()
    elif order_type == 'canonical':
        return CANONICAL_FEATURES_ORDER.copy()
    raise ValueError(f"order_type invalide : {order_type}")


# Tests unitaires (exécution directe)
if __name__ == "__main__":
    print("TEST CONFIG MODEL")
    print("Ordre modèle :", MODEL_FEATURES_ORDER[:5], "...")
    print("Tout semble OK")