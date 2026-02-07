"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/predictor.py 
Auteur: Stage R&D - IMT Nord Europe
Version: 1.1.0 - CORRECTION : Suppression lru_cache incompatible
═══════════════════════════════════════════════════════════════════════════════
Ce module contient la logique de prédiction du béton, avec validation des entrées,
feature engineering aligné avec le notebook, et vérification stricte de l'ordre des features.
Il est conçu pour être robuste, maintenable et facilement testable.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
# functools importé mais plus utilisé pour lru_cache ici (supprimé)

# Import config centralisée
from app.models.model_config import MODEL_FEATURES_ORDER

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    st = None  # Fallback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Résultat structuré d'une prédiction béton."""
    Resistance: float
    Diffusion_Cl: float
    Carbonatation: float
    Ratio_E_L: float
    Liant_Total: float
    Pct_Substitution: float
    
    def to_dict(self) -> Dict[str, float]:
        return self.__dict__


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ENTRÉES
# ═══════════════════════════════════════════════════════════════════════════════

def validate_composition(composition: Dict[str, float]) -> Tuple[bool, str]:
    """
    Valide une composition béton.
    """
    required_keys = [
        "Ciment", "Laitier", "CendresVolantes", "Eau",
        "Superplastifiant", "GravilonsGros", "SableFin", "Age"
    ]
    
    missing = [k for k in required_keys if k not in composition]
    if missing:
        return False, f"Clés manquantes: {missing}"
    
    for key, value in composition.items():
        if key in required_keys:
            try:
                val = float(value)
                if val < 0:
                    return False, f"Valeur négative pour {key}: {value}"
            except (TypeError, ValueError):
                return False, f"Valeur non numérique pour {key}: {value}"
    
    if composition["Age"] < 1:
        return False, "Age doit être ≥ 1 jour"
    
    liant_total = sum(composition.get(k, 0) for k in ["Ciment", "Laitier", "CendresVolantes"])
    if liant_total < 150:
        return False, f"Liant total trop faible: {liant_total:.1f} kg/m³"
    
    return True, "Composition valide"


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

def engineer_features(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering aligné avec le notebook.
    """
    df = df_input.copy()
    epsilon = 1e-5
    
    df['Liant_Total'] = df['Ciment'] + df['Laitier'] + df['CendresVolantes']
    df['Ratio_E_L'] = df['Eau'] / (df['Liant_Total'] + epsilon)
    df['Pct_Laitier'] = df['Laitier'] / (df['Liant_Total'] + epsilon)
    df['Log_Age'] = np.log(df['Age'] + 1)
    df['Sqrt_Age'] = np.sqrt(df['Age'])
    df['Ciment_x_LogAge'] = df['Ciment'] * df['Log_Age']
    df['Eau_x_SP'] = df['Eau'] * df['Superplastifiant']
    df['Liant_x_RatioEL'] = df['Liant_Total'] * df['Ratio_E_L']
    volume_total = df[['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'GravilonsGros', 'SableFin']].sum(axis=1)
    df['Ratio_Granulats'] = (df['GravilonsGros'] + df['SableFin']) / (volume_total + epsilon)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION ALIGNEMENT FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

def verify_features_alignment(
    feature_list: List[str],
    verbose: bool = True
) -> Tuple[bool, str]:
    """
    Vérifie alignement avec MODEL_FEATURES_ORDER.
    """
    if len(feature_list) != 15:
        msg = f"❌ Nombre incorrect: {len(feature_list)} != 15"
        if verbose: logger.error(msg)
        return False, msg
    
    if feature_list != MODEL_FEATURES_ORDER:
        msg = "❌ Ordre incorrect"
        if verbose:
            logger.error(msg)
            for i, (p, e) in enumerate(zip(feature_list, MODEL_FEATURES_ORDER)):
                status = "✅" if p == e else "❌"
                logger.error(f"  {i:2d}. {status} {p:20s} vs {e}")
        return False, msg
    
    if set(feature_list) != set(MODEL_FEATURES_ORDER):
        msg = "❌ Features manquantes/doublons"
        if verbose:
            missing = set(MODEL_FEATURES_ORDER) - set(feature_list)
            extra = set(feature_list) - set(MODEL_FEATURES_ORDER)
            logger.error(f"  Missing: {missing}")
            logger.error(f"  Extra: {extra}")
        return False, msg
    
    if verbose: logger.info("✅ Alignement parfait")
    return True, "✅ Alignement parfait"


# ═══════════════════════════════════════════════════════════════════════════════
# PRÉDICTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

# DECORATEUR @lru_cache SUPPRIMÉ CAR COMPATIBLE AVEC DICT ET OBJECTS SKLEARN (UNHASHABLE)
def predict_concrete_properties(
    composition: Dict[str, float],
    model: Optional[Any] = None,
    feature_list: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Prédit les propriétés du béton.
    
    Note: Le cache n'est pas utilisé ici car les arguments (dict, model obj) ne sont pas hachables.
    Le modèle est déjà mis en cache via @st.cache_resource dans le script principal.
    """
    try:
        is_valid, msg = validate_composition(composition)
        if not is_valid:
            raise ValueError(msg)
        
        if model is None:
            if HAS_STREAMLIT and 'model' in st.session_state:
                model = st.session_state.model
            else:
                raise RuntimeError("Modèle non chargé")
        
        if feature_list is None:
            if HAS_STREAMLIT and 'features' in st.session_state:
                feature_list = st.session_state.features
            else:
                feature_list = MODEL_FEATURES_ORDER
        
        is_aligned, msg = verify_features_alignment(feature_list)
        if not is_aligned:
            raise ValueError(msg)
        
        df_input = pd.DataFrame([composition])
        df_engineered = engineer_features(df_input)
        
        missing = [f for f in feature_list if f not in df_engineered.columns]
        if missing:
            raise ValueError(f"Features manquantes: {missing}")
        
        X_pred = df_engineered[feature_list]
        
        if list(X_pred.columns) != feature_list:
            raise ValueError("Ordre features modifié après sélection")
        
        raw_preds = model.predict(X_pred)[0]
        
        liant_total = float(df_engineered["Liant_Total"].values[0])
        ratio_el = float(df_engineered["Ratio_E_L"].values[0])
        pct_sub = (composition.get("Laitier", 0) + composition.get("CendresVolantes", 0)) / (liant_total + 1e-5)
        
        results = {
            "Resistance": round(float(raw_preds[0]), 1),
            "Diffusion_Cl": round(float(raw_preds[1]), 2),
            "Carbonatation": round(float(raw_preds[2]), 1),
            "Ratio_E_L": round(ratio_el, 3),
            "Liant_Total": round(liant_total, 1),
            "Pct_Substitution": round(pct_sub, 3)
        }
        
        return results
    
    except Exception as e:
        logger.error(f"Prédiction échouée: {e}", exc_info=True)
        raise RuntimeError(f"Erreur prédiction: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# PRÉDICTION BATCH
# ═══════════════════════════════════════════════════════════════════════════════

def predict_batch(
    compositions: List[Dict[str, float]],
    model: Any = None,
    feature_list: Optional[List[str]] = None
) -> List[Dict[str, float]]:
    """
    Prédiction batch optimisée (vectorisée).
    
    Args:
        compositions: Liste de compositions
        model: Modèle ML
        feature_list: Liste features
        
    Returns:
        Liste de résultats
    """
    import streamlit as st
    
    try:
        # Récupération modèle
        if model is None:
            if 'model' not in st.session_state:
                raise RuntimeError("❌ Modèle non chargé")
            model = st.session_state.model
        
        # Récupération features
        if feature_list is None:
            if 'features' in st.session_state:
                feature_list = st.session_state.features
            else:
                feature_list = MODEL_FEATURES_ORDER.copy()
        
        # Vérification alignement
        is_aligned, msg = verify_features_alignment(feature_list, verbose=False)
        if not is_aligned:
            raise ValueError(f"Alignement features incorrect: {msg}")
        
        # Validation batch
        for i, comp in enumerate(compositions):
            is_valid, message = validate_composition(comp)
            if not is_valid:
                raise ValueError(f"Composition {i+1} invalide: {message}")
        
        # Conversion DataFrame batch
        df_batch = pd.DataFrame(compositions)
        
        # Feature engineering batch (vectorisé)
        df_engineered = engineer_features(df_batch)
        
        # Sélection features
        X_batch = df_engineered[feature_list]
        
        # Prédiction batch (1 seul appel modèle)
        raw_preds = model.predict(X_batch)
        
        # Post-traitement
        results = []
        for i in range(len(compositions)):
            liant_total = float(df_engineered.iloc[i]["Liant_Total"])
            ratio_el = float(df_engineered.iloc[i]["Ratio_E_L"])
            
            pct_sub = float(
                (compositions[i].get("Laitier", 0) + 
                 compositions[i].get("CendresVolantes", 0)) / 
                (liant_total + 1e-5)
            )
            
            result = {
                "Resistance": round(float(raw_preds[i][0]), 1),
                "Diffusion_Cl": round(float(raw_preds[i][1]), 2),
                "Carbonatation": round(float(raw_preds[i][2]), 1),
                "Ratio_E_L": round(ratio_el, 3),
                "Liant_Total": round(liant_total, 1),
                "Pct_Substitution": round(pct_sub, 3)
            }
            results.append(result)
        
        logger.info(f"✅ Prédiction batch: {len(results)} formulations")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erreur prédiction batch: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_features() -> List[str]:
    """Retourne l'ordre des features du modèle."""
    return MODEL_FEATURES_ORDER.copy()


def simulate_prediction(composition: Dict[str, float]) -> Dict[str, float]:
    """
    Simulation de prédiction basée sur lois physiques.
    Utilisée pour tests sans modèle ML.
    """
    ciment = composition.get("Ciment", 350)
    eau = composition.get("Eau", 175)
    laitier = composition.get("Laitier", 0)
    cendres = composition.get("CendresVolantes", 0)
    age = composition.get("Age", 28)
    
    liant_total = ciment + laitier + cendres
    ratio_el = eau / (liant_total + 1e-5)
    
    # Loi d'Abrams : fc = A / (E/L)^B
    A, B = 100, 1.5
    resistance = A / (ratio_el**B + 0.5) * np.log(age + 1) / np.log(28 + 1)
    
    # Diffusion chlorures (anti-corrélée à résistance)
    diffusion_cl = max(0.5, 20 - resistance * 0.3)
    
    # Carbonatation (loi de Fick simplifiée)
    carbonatation = max(0.1, 10 * ratio_el * np.sqrt(age / 28))
    
    return {
        "Resistance": round(resistance, 1),
        "Diffusion_Cl": round(diffusion_cl, 2),
        "Carbonatation": round(carbonatation, 1),
        "Ratio_E_L": round(ratio_el, 3),
        "Liant_Total": round(liant_total, 1),
        "Pct_Substitution": round((laitier + cendres) / (liant_total + 1e-5), 3)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "predict_concrete_properties",
    "predict_batch",
    "validate_composition",
    "engineer_features",
    "get_default_features",
    "verify_features_alignment",
    "simulate_prediction",
    "PredictionResult",
    "MODEL_FEATURES_ORDER"
]