"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/predictor.py
Version: 1.0.0 - ALIGNED WITH NOTEBOOK
Auteur: Stage R&D - IMT Nord Europe
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# ORDRE FEATURES CRITIQUE (ISSU DU NOTEBOOK SECTION 3.3)
# ═════════════════════════════════════════════════════════════════════════════

MODEL_FEATURES_ORDER = [
    'Ciment',
    'Eau',
    'Age',
    'GravilonsGros',
    'SableFin',
    'Laitier',
    'CendresVolantes',
    'Superplastifiant', 
    'Ratio_E_L',
    'Pct_Laitier',
    'Log_Age',
    'Sqrt_Age',
    'Ciment_x_LogAge',
    'Eau_x_SP',
    'Liant_x_RatioEL',
    'Ratio_Granulats'
]  # 16 features (8 originales + 8 engineered, sans Pct_CendresVolantes)

# Bornes physiques pour validation
BOUNDS = {
    'Ciment': (100, 550),
    'Laitier': (0, 350),
    'CendresVolantes': (0, 200),
    'Eau': (120, 250),
    'Superplastifiant': (0, 20),
    'GravilonsGros': (800, 1200),
    'SableFin': (600, 900),
    'Age': (1, 365)
}


# ═════════════════════════════════════════════════════════════════════════════
# FONCTION CRITIQUE : FEATURE ENGINEERING (EXACT NOTEBOOK)
# ═════════════════════════════════════════════════════════════════════════════

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering EXACT du notebook Section 2.3.
    
    CRITIQUE : Doit reproduire EXACTEMENT les transformations du notebook
    pour garantir compatibilité avec le modèle entraîné.
    
    Args:
        df: DataFrame avec colonnes originales
        
    Returns:
        DataFrame avec features engineered
    """
    df_new = df.copy()
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1. RATIOS FONDAMENTAUX
    # ─────────────────────────────────────────────────────────────────────────
    
    df_new['Liant_Total'] = (
        df_new['Ciment'] + 
        df_new['Laitier'] + 
        df_new['CendresVolantes']
    )
    
    # Protection division par zéro
    df_new['Ratio_E_L'] = df_new['Eau'] / (df_new['Liant_Total'] + 1e-5)
    df_new['Pct_Laitier'] = df_new['Laitier'] / (df_new['Liant_Total'] + 1e-5)
    df_new['Pct_CendresVolantes'] = df_new['CendresVolantes'] / (df_new['Liant_Total'] + 1e-5)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2. TRANSFORMATIONS CINÉTIQUES
    # ─────────────────────────────────────────────────────────────────────────
    
    df_new['Log_Age'] = np.log(df_new['Age'] + 1)
    df_new['Sqrt_Age'] = np.sqrt(df_new['Age'])
    
    # ─────────────────────────────────────────────────────────────────────────
    # 3. INTERACTIONS CRITIQUES
    # ─────────────────────────────────────────────────────────────────────────
    
    df_new['Ciment_x_LogAge'] = df_new['Ciment'] * df_new['Log_Age']
    df_new['Eau_x_SP'] = df_new['Eau'] * df_new['Superplastifiant']
    df_new['Liant_x_RatioEL'] = df_new['Liant_Total'] * df_new['Ratio_E_L']
    
    # ─────────────────────────────────────────────────────────────────────────
    # 4. COMPACITÉ GRANULAIRE
    # ─────────────────────────────────────────────────────────────────────────
    
    volume_total = df_new[[
        'Ciment', 'Laitier', 'CendresVolantes', 'Eau',
        'GravilonsGros', 'SableFin'
    ]].sum(axis=1)
    
    df_new['Ratio_Granulats'] = (
        (df_new['GravilonsGros'] + df_new['SableFin']) / 
        (volume_total + 1e-5)
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # 5. NETTOYAGE (CRITIQUE)
    # ─────────────────────────────────────────────────────────────────────────
    
    df_new.replace([np.inf, -np.inf], 0, inplace=True)
    df_new.fillna(0, inplace=True)
    
    return df_new


# ═════════════════════════════════════════════════════════════════════════════
# FONCTION : VALIDATION COMPOSITION
# ═════════════════════════════════════════════════════════════════════════════

def validate_composition(composition: Dict[str, float]) -> Dict[str, Any]:
    """
    Valide une composition béton selon bornes physiques.
    
    Args:
        composition: Dict avec composants (kg/m³)
        
    Returns:
        Dict avec 'valid': bool, 'errors': List[str], 'warnings': List[str]
    """
    errors = []
    warnings = []
    
    # Vérifier clés minimales
    required_keys = ['Ciment', 'Eau', 'Age']
    missing = [k for k in required_keys if k not in composition]
    
    if missing:
        errors.append(f"Clés manquantes: {missing}")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Vérifier bornes
    for param, (min_val, max_val) in BOUNDS.items():
        value = composition.get(param, 0)
        
        if value < min_val:
            errors.append(
                f"{param} trop faible: {value:.1f} < {min_val} kg/m³"
            )
        elif value > max_val:
            errors.append(
                f"{param} trop élevé: {value:.1f} > {max_val} kg/m³"
            )
    
    # Vérifications physiques
    ciment = composition.get('Ciment', 0)
    laitier = composition.get('Laitier', 0)
    cendres = composition.get('CendresVolantes', 0)
    eau = composition.get('Eau', 0)
    
    liant_total = ciment + laitier + cendres
    ratio_el = eau / (liant_total + 1e-5) if liant_total > 0 else 99
    
    # Ratio E/L critique
    if ratio_el > 0.70:
        errors.append(
            f"Ratio E/L excessif: {ratio_el:.3f} > 0.70 (béton non conforme)"
        )
    elif ratio_el > 0.60:
        warnings.append(
            f"Ratio E/L élevé: {ratio_el:.3f} > 0.60 (durabilité limitée)"
        )
    
    # Dosage ciment minimum
    if ciment < 200:
        errors.append(
            f"Dosage ciment insuffisant: {ciment:.0f} < 200 kg/m³"
        )
    
    # Taux substitution
    taux_sub = (laitier + cendres) / (liant_total + 1e-5)
    if taux_sub > 0.70:
        warnings.append(
            f"Taux substitution élevé: {taux_sub*100:.0f}% > 70% (prise lente)"
        )
    
    is_valid = len(errors) == 0
    
    return {
        'valid': is_valid,
        'errors': errors,
        'warnings': warnings,
        'ratio_el': ratio_el,
        'liant_total': liant_total,
        'taux_substitution': taux_sub
    }


# ═════════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE : PRÉDICTION
# ═════════════════════════════════════════════════════════════════════════════

def predict_concrete_properties(
    composition: Dict[str, float],
    model: Any,
    feature_list: Optional[List[str]] = None,
    validate: bool = True
) -> Dict[str, float]:
    """
    Prédit propriétés béton (3 cibles).
    
    Args:
        composition: Composition béton (kg/m³)
        model: Modèle ML (MultiOutputRegressor)
        feature_list: Liste features (utilise MODEL_FEATURES_ORDER si None)
        validate: Valider inputs
        
    Returns:
        Dict avec Resistance, Diffusion_Cl, Carbonatation, Ratio_E_L, Liant_Total
        
    Raises:
        ValueError: Si composition invalide
        
    Example:
```python
        composition = {
            'Ciment': 280, 'Laitier': 0, 'CendresVolantes': 0,
            'Eau': 180, 'Superplastifiant': 0,
            'GravillosGros': 1100, 'SableFin': 750, 'Age': 28
        }
        
        predictions = predict_concrete_properties(composition, model)
        # {'Resistance': 25.8, 'Diffusion_Cl': 7.76, 'Carbonatation': 16.7, ...}
```
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1. VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    
    if validate:
        validation = validate_composition(composition)
        
        if not validation['valid']:
            error_msg = "; ".join(validation['errors'])
            raise ValueError(f"Composition invalide: {error_msg}")
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"{warning}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2. COMPLÉTER COMPOSITION (valeurs par défaut)
    # ─────────────────────────────────────────────────────────────────────────
    
    defaults = {
        'Ciment': 280.0,
        'Laitier': 0.0,
        'CendresVolantes': 0.0,
        'Eau': 180.0,
        'Superplastifiant': 0.0,
        'GravilonsGros': 1100.0,
        'SableFin': 750.0,
        'Age': 28.0
    }
    
    full_composition = {**defaults, **composition}
    
    # ─────────────────────────────────────────────────────────────────────────
    # 3. FEATURE ENGINEERING
    # ─────────────────────────────────────────────────────────────────────────
    
    df_input = pd.DataFrame([full_composition])
    df_engineered = engineer_features(df_input)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 4. SÉLECTION FEATURES (ORDRE CRITIQUE)
    # ─────────────────────────────────────────────────────────────────────────
    
    if feature_list is None:
        feature_list = MODEL_FEATURES_ORDER
    
    # Vérifier disponibilité features
    missing_features = [f for f in feature_list if f not in df_engineered.columns]
    if missing_features:
        raise ValueError(
            f"Features manquantes après engineering: {missing_features}"
        )
    
    X_input = df_engineered[feature_list]
    
    # Vérifier NaN/Inf
    if X_input.isnull().any().any():
        logger.warning("⚠️ NaN détectés, remplacement par 0")
        X_input.fillna(0, inplace=True)
    
    if np.isinf(X_input.values).any():
        logger.warning("⚠️ Inf détectés, remplacement par 0")
        X_input.replace([np.inf, -np.inf], 0, inplace=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 5. PRÉDICTION (3 CIBLES)
    # ─────────────────────────────────────────────────────────────────────────
    
    try:
        predictions = model.predict(X_input)[0]
        
        # Validation bornes physiques
        resistance = float(np.clip(predictions[0], 0, 150))
        diffusion_cl = float(np.clip(predictions[1], 0, 30))
        carbonatation = float(np.clip(predictions[2], 0, 100))
        
        # Calculs supplémentaires
        liant_total = float(df_engineered['Liant_Total'].values[0])
        ratio_el = float(df_engineered['Ratio_E_L'].values[0])
        pct_substitution = (
            (full_composition['Laitier'] + full_composition['CendresVolantes']) / 
            (liant_total + 1e-5)
        )
        
        result = {
            'Resistance': round(resistance, 2),
            'Diffusion_Cl': round(diffusion_cl, 3),
            'Carbonatation': round(carbonatation, 2),
            'Ratio_E_L': round(ratio_el, 3),
            'Liant_Total': round(liant_total, 1),
            'Pct_Substitution': round(pct_substitution, 3)
        }
        
        logger.debug(
            f"Prédiction: R={result['Resistance']:.1f} MPa, "
            f"Diff={result['Diffusion_Cl']:.2f}, "
            f"Carb={result['Carbonatation']:.1f} mm"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur prédiction: {e}", exc_info=True)
        raise RuntimeError(f"Erreur lors de la prédiction: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═════════════════════════════════════════════════════════════════════════════

def get_default_features() -> List[str]:
    """Retourne liste features par défaut."""
    return MODEL_FEATURES_ORDER.copy()


def verify_features_alignment(model, expected_features: List[str]) -> bool:
    """
    Vérifie cohérence features modèle vs attendues.
    
    Args:
        model: Modèle ML
        expected_features: Liste features attendues
        
    Returns:
        True si cohérent
    """
    try:
        # Test avec données fictives
        test_data = pd.DataFrame([{f: 0.5 for f in expected_features}])
        _ = model.predict(test_data)
        logger.info("Alignement features vérifié")
        return True
    except Exception as e:
        logger.error(f"Erreur alignement features: {e}")
        return False


__all__ = [
    'predict_concrete_properties',
    'engineer_features',
    'validate_composition',
    'get_default_features',
    'verify_features_alignment',
    'MODEL_FEATURES_ORDER',
    'BOUNDS'
]