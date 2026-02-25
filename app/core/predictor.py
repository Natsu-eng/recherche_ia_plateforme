"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/predictor.py
Version: 1.1.0 - Corrigé & Production Ready
Auteur: Stage R&D - IMT Nord Europe
═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE :
  - RAW_FEATURES (8)  → colonnes saisies par l'utilisateur / formulaires
  - MODEL_FEATURES_ORDER (16) → colonnes après engineer_features()
  - Le flux est toujours : raw → engineer_features() → [16 cols] → model.predict()
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

# ✅ [1] Séparation explicite raw features vs engineered features

# Colonnes saisies par l'utilisateur (formulaires Streamlit / BDD)
RAW_FEATURES: List[str] = [
    'Ciment',
    'Eau',
    'Age',
    'GravilonsGros',
    'SableFin',
    'Laitier',
    'CendresVolantes',
    'Superplastifiant',
]  # 8 colonnes

# Colonnes passées au modèle (après engineer_features)
# CRITIQUE : ordre exact issu du notebook Section 3.3
# Ne pas modifier sans ré-entraîner le modèle
MODEL_FEATURES_ORDER: List[str] = [
    'Eau',
    'GravilonsGros',
    'Ratio_E_L',
    'Sqrt_Age',
    'SableFin',
    'Eau_x_SP',
    'Log_Age',
    'Pct_Laitier',
    'Liant_x_RatioEL',
    'Laitier',
    'Ciment',
    'Ratio_Granulats',
    'Age',
    'CendresVolantes',
    'Ciment_x_LogAge',
] 

# ═══════════════════════════════════════════════════════════════════════════════
# BORNES PHYSIQUES
# ═══════════════════════════════════════════════════════════════════════════════

# Erreur bloquante si dépassement
BOUNDS_ERROR: Dict[str, tuple] = {
    'Ciment':          (80,  600),   # CEM III/B peut avoir Ciment ≈ 80 kg
    'Laitier':         (0,   400),
    'CendresVolantes': (0,   200),
    'Eau':             (100, 260),
    'Superplastifiant':(0,   25),
    'GravilonsGros':   (700, 1300),
    'Age':             (1,   365),
}

# Warning non bloquant si dépassement
BOUNDS_WARNING: Dict[str, tuple] = {
    'SableFin': (400, 950),   # [2] warning, pas erreur (BAP possible)
}

# [2] Seuil sur LIANT TOTAL (pas Ciment seul)
LIANT_TOTAL_MIN: float = 200.0     # kg/m³

# Seuils E/L EN 206
EL_ERROR_THRESHOLD:   float = 0.75
EL_WARNING_THRESHOLD: float = 0.60

# Seuil substitution
SUBSTITUTION_WARNING: float = 0.70


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING — REPRODUCTION EXACTE NOTEBOOK
# ═══════════════════════════════════════════════════════════════════════════════

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering EXACT du notebook Section 2.3.

    CRITIQUE : cette fonction doit reproduire bit-à-bit les transformations
    appliquées lors de l'entraînement. Toute divergence entraîne une
    distribution-shift silencieuse → prédictions biaisées.

    Transformations appliquées (dans l'ordre notebook) :
      1. Ratios fondamentaux  : Ratio_E_L, Pct_Laitier, Pct_CendresVolantes
      2. Cinétique d'hydratation : Log_Age, Sqrt_Age
      3. Interactions            : Ciment_x_LogAge, Eau_x_SP, Liant_x_RatioEL
      4. Compacité granulaire    : Ratio_Granulats
      5. Nettoyage NaN/Inf       : replace puis fillna

    Note : Pct_CendresVolantes est calculé (utile en analyse) mais exclu
    de MODEL_FEATURES_ORDER — cohérent avec la sélection du notebook.

    Args:
        df: DataFrame avec les colonnes RAW_FEATURES

    Returns:
        DataFrame enrichi avec 16+ colonnes (toutes celles de MODEL_FEATURES_ORDER)
    """
    df_new = df.copy()

    # ── 1. RATIOS FONDAMENTAUX ────────────────────────────────────────────────

    df_new['Liant_Total'] = (
        df_new['Ciment']
        + df_new['Laitier']
        + df_new['CendresVolantes']
    )

    # Protection division par zéro (+ 1e-5 cohérent avec le notebook)
    df_new['Ratio_E_L'] = df_new['Eau'] / (df_new['Liant_Total'] + 1e-5)
    df_new['Pct_Laitier'] = df_new['Laitier'] / (df_new['Liant_Total'] + 1e-5)

    # Calculé mais non inclus dans MODEL_FEATURES_ORDER (comme dans le notebook)
    df_new['Pct_CendresVolantes'] = (
        df_new['CendresVolantes'] / (df_new['Liant_Total'] + 1e-5)
    )

    # ── 2. CINÉTIQUE D'HYDRATATION ────────────────────────────────────────────
    # ln(age+1) modélise la progression logarithmique de la résistance
    # sqrt(age) capture la phase d'hydratation initiale plus rapide

    df_new['Log_Age'] = np.log(df_new['Age'] + 1)
    df_new['Sqrt_Age'] = np.sqrt(df_new['Age'])

    # ── 3. INTERACTIONS CRITIQUES ─────────────────────────────────────────────
    # Ciment × Log_Age : montée en résistance (clinker + durée)
    # Eau × SP        : plasticité (dilution adjuvant)
    # Liant × E/L     : densité pâte cimentaire

    df_new['Ciment_x_LogAge']  = df_new['Ciment'] * df_new['Log_Age']
    df_new['Eau_x_SP']         = df_new['Eau'] * df_new['Superplastifiant']
    df_new['Liant_x_RatioEL']  = df_new['Liant_Total'] * df_new['Ratio_E_L']

    # ── 4. COMPACITÉ GRANULAIRE ───────────────────────────────────────────────
    # Proportion granulats dans le volume total (squelette granulaire)

    volume_total = df_new[[
        'Ciment', 'Laitier', 'CendresVolantes',
        'Eau', 'GravilonsGros', 'SableFin',
    ]].sum(axis=1)

    df_new['Ratio_Granulats'] = (
        (df_new['GravilonsGros'] + df_new['SableFin'])
        / (volume_total + 1e-5)
    )

    # ── 5. NETTOYAGE ──────────────────────────────────────────────────────────
    # ORDRE CRITIQUE : replace(Inf) AVANT fillna(NaN)
    # (un Inf → NaN après replace, puis NaN → 0 après fillna)

    df_new.replace([np.inf, -np.inf], 0, inplace=True)
    df_new.fillna(0, inplace=True)

    return df_new


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION COMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_composition(composition: Dict[str, float]) -> Dict[str, Any]:
    """
    Valide une composition béton selon bornes physiques et règles EN 206.

    Niveaux :
      - errors   : composition rejetée (predict lèvera ValueError)
      - warnings : composition acceptée avec alertes utilisateur

    Règles :
      - Clés obligatoires : Ciment, Eau, Age
      - Bornes par constituant (BOUNDS_ERROR / BOUNDS_WARNING)
      - Liant total ≥ 200 kg/m³ (pas Ciment seul → CEM III/B compatible)  ✅
      - Ratio E/L ≤ 0.75 (erreur) / ≤ 0.60 (warning)
      - Taux substitution ≤ 70 % (warning)
      - SableFin hors [400, 950] : warning (pas erreur) ✅

    Args:
        composition: Dict des dosages en kg/m³

    Returns:
        Dict {
            'valid': bool,
            'errors': List[str],
            'warnings': List[str],
            'ratio_el': float,
            'liant_total': float,
            'taux_substitution': float,
        }
    """
    errors: List[str]   = []
    warnings: List[str] = []

    # ── Clés obligatoires ─────────────────────────────────────────────────────
    required_keys = ['Ciment', 'Eau', 'Age']
    missing = [k for k in required_keys if k not in composition]
    if missing:
        errors.append(f"Clés obligatoires manquantes : {missing}")
        return {
            'valid': False, 'errors': errors, 'warnings': warnings,
            'ratio_el': 0.0, 'liant_total': 0.0, 'taux_substitution': 0.0,
        }

    # ── Bornes erreur bloquante ────────────────────────────────────────────────
    for param, (min_val, max_val) in BOUNDS_ERROR.items():
        value = float(composition.get(param, 0))
        if value < min_val:
            errors.append(
                f"{param} trop faible : {value:.1f} < {min_val} kg/m³"
            )
        elif value > max_val:
            errors.append(
                f"{param} trop élevé : {value:.1f} > {max_val} kg/m³"
            )

    # [2] Bornes warning non bloquant (ex: SableFin)
    for param, (min_val, max_val) in BOUNDS_WARNING.items():
        value = float(composition.get(param, 0))
        if value < min_val:
            warnings.append(
                f"{param} faible : {value:.1f} < {min_val} kg/m³ "
                f"(vérifier si béton autoplaçant)"
            )
        elif value > max_val:
            warnings.append(
                f"{param} élevé : {value:.1f} > {max_val} kg/m³"
            )

    # ── Calculs intermédiaires ────────────────────────────────────────────────
    ciment         = float(composition.get('Ciment', 0))
    laitier        = float(composition.get('Laitier', 0))
    cendres        = float(composition.get('CendresVolantes', 0))
    eau            = float(composition.get('Eau', 0))
    liant_total    = ciment + laitier + cendres
    ratio_el       = eau / (liant_total + 1e-5)
    taux_sub       = (laitier + cendres) / (liant_total + 1e-5)

    # [2] Seuil sur liant total, pas sur ciment seul
    if liant_total < LIANT_TOTAL_MIN:
        errors.append(
            f"Liant total insuffisant : {liant_total:.0f} < {LIANT_TOTAL_MIN:.0f} kg/m³ "
            f"(Ciment + Laitier + Cendres)"
        )

    # ── Ratio E/L ─────────────────────────────────────────────────────────────
    if ratio_el > EL_ERROR_THRESHOLD:
        errors.append(
            f"Ratio E/L excessif : {ratio_el:.3f} > {EL_ERROR_THRESHOLD} "
            f"(béton non conforme EN 206)"
        )
    elif ratio_el > EL_WARNING_THRESHOLD:
        warnings.append(
            f"Ratio E/L élevé : {ratio_el:.3f} > {EL_WARNING_THRESHOLD} "
            f"(durabilité limitée)"
        )

    # ── Taux de substitution ─────────────────────────────────────────────────
    if taux_sub > SUBSTITUTION_WARNING:
        warnings.append(
            f"Taux de substitution élevé : {taux_sub * 100:.0f} % > "
            f"{SUBSTITUTION_WARNING * 100:.0f} % (prise lente, résistance initiale réduite)"
        )

    return {
        'valid':             len(errors) == 0,
        'errors':            errors,
        'warnings':          warnings,
        'ratio_el':          round(ratio_el, 4),
        'liant_total':       round(liant_total, 1),
        'taux_substitution': round(taux_sub, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRÉDICTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

def predict_concrete_properties(
    composition: Dict[str, float],
    model: Any,
    feature_list: Optional[List[str]] = None,
    validate: bool = True,
) -> Dict[str, float]:
    """
    Prédit les 3 propriétés cibles d'un béton.

    Pipeline interne :
      composition (dict)
        → validate_composition()                      [optionnel]
        → complétion avec valeurs par défaut
        → engineer_features()                         [toujours appliqué]
        → sélection MODEL_FEATURES_ORDER (16 cols)
        → model.predict()
        → clip + round

    Note sur `feature_list` :
      Ce paramètre est conservé pour compatibilité ascendante avec les pages
      Streamlit qui passent st.session_state["features"]. Il est utilisé
      uniquement pour un log de vérification. Le modèle reçoit toujours les
      16 colonnes de MODEL_FEATURES_ORDER après feature engineering.

    Args:
        composition:  Dict des dosages en kg/m³. Clés reconnues :
                        Ciment, Laitier, CendresVolantes, Eau,
                        Superplastifiant, GravilonsGros, SableFin, Age
        model:        Modèle ML (MultiOutputRegressor wrappant XGBoost)
                        model.predict(X) → array shape (n, 3)
                        colonnes : [Resistance, Diffusion_Cl, Carbonatation]
        feature_list: Ignoré pour la prédiction (voir note ci-dessus).
                        Si fourni, un log de vérification est émis.
        validate:     Si True, lève ValueError sur composition invalide.

    Returns:
        Dict {
            'Resistance':       float  (MPa, clippé [0, 200])
            'Diffusion_Cl':     float  (×10⁻¹², clippé [0, 30])
            'Carbonatation':    float  (mm, clippé [0, 100])
            'Ratio_E_L':        float  (calculé depuis engineer_features)
            'Liant_Total':      float  (kg/m³)
            'Pct_Substitution': float  ([0, 1])
        }

    Raises:
        ValueError:    Si composition invalide (validate=True)
        RuntimeError:  Si model.predict() échoue
    """

    # ── 1. VALIDATION ─────────────────────────────────────────────────────────

    if validate:
        report = validate_composition(composition)
        if not report['valid']:
            error_msg = " | ".join(report['errors'])
            raise ValueError(f"Composition invalide : {error_msg}")
        for warning in report['warnings']:
            logger.warning("[predictor] %s", warning)

    # ── 2. COMPLÉTION VALEURS PAR DÉFAUT ──────────────────────────────────────
    # Les defaults correspondent à un béton C25/30 ordinaire.
    # Toutes les clés RAW_FEATURES doivent être présentes avant engineering.

    _defaults: Dict[str, float] = {
        'Ciment':           280.0,
        'Laitier':            0.0,
        'CendresVolantes':    0.0,
        'Eau':              180.0,
        'Superplastifiant':   0.0,
        'GravilonsGros':   1100.0,
        'SableFin':         750.0,
        'Age':               28.0,
    }
    full_composition = {**_defaults, **composition}

    # ── 3. LOG VÉRIFICATION feature_list ──────────────────────────────────────
    # [1] feature_list n'est plus utilisé pour la sélection finale.
    # Si fourni, on vérifie que les raw features sont couvertes.
    if feature_list is not None:
        raw_missing = [f for f in RAW_FEATURES if f not in feature_list]
        if raw_missing:
            logger.warning(
                "[predictor] feature_list fourni ne contient pas : %s — "
                "MODEL_FEATURES_ORDER sera utilisé.", raw_missing
            )

    # ── 4. FEATURE ENGINEERING ────────────────────────────────────────────────

    df_input      = pd.DataFrame([full_composition])
    df_engineered = engineer_features(df_input)

    # ── 5. SÉLECTION 15 COLONNES (ORDRE CRITIQUE) ─────────────────────────────

    missing_engineered = [
        f for f in MODEL_FEATURES_ORDER if f not in df_engineered.columns
    ]
    if missing_engineered:
        raise ValueError(
            f"Colonnes manquantes après feature engineering : {missing_engineered}. "
            f"Vérifier engineer_features()."
        )

    # [4] Copie explicite pour éviter SettingWithCopyWarning
    X_input = df_engineered[MODEL_FEATURES_ORDER].copy()

    # Nettoyage de sécurité (engineer_features devrait déjà le faire)
    if X_input.isnull().any().any():
        logger.warning("[predictor] NaN résiduels → remplacement par 0")
        X_input.fillna(0, inplace=True)

    if np.isinf(X_input.values).any():
        logger.warning("[predictor] Inf résiduels → remplacement par 0")
        X_input.replace([np.inf, -np.inf], 0, inplace=True)

    # ── 6. PRÉDICTION ─────────────────────────────────────────────────────────

    try:
        raw_preds = model.predict(X_input)   # shape (1, 3)
        preds_row = raw_preds[0]             # [Resistance, Diffusion_Cl, Carbonatation]

        # [5] Borne supérieure résistance : 200 MPa (BUHP compatibles)
        resistance    = float(np.clip(preds_row[0], 0.0, 200.0))
        diffusion_cl  = float(np.clip(preds_row[1], 0.0, 30.0))
        carbonatation = float(np.clip(preds_row[2], 0.0, 100.0))

    except Exception as exc:
        logger.error("[predictor] model.predict() échoué : %s", exc, exc_info=True)
        raise RuntimeError(f"Erreur lors de la prédiction : {exc}") from exc

    # ── 7. MÉTRIQUES DÉRIVÉES ─────────────────────────────────────────────────

    liant_total = float(df_engineered['Liant_Total'].values[0])
    ratio_el    = float(df_engineered['Ratio_E_L'].values[0])

    laitier = float(full_composition['Laitier'])
    cendres = float(full_composition['CendresVolantes'])
    pct_sub = (laitier + cendres) / (liant_total + 1e-5)

    result: Dict[str, float] = {
        'Resistance':       round(resistance,    2),
        'Diffusion_Cl':     round(diffusion_cl,  3),
        'Carbonatation':    round(carbonatation, 2),
        'Ratio_E_L':        round(ratio_el,      4),
        'Liant_Total':      round(liant_total,   1),
        'Pct_Substitution': round(pct_sub,       4),
    }

    logger.debug(
        "[predictor] R=%.1f MPa | Diff=%.2f | Carb=%.1f mm | E/L=%.3f | Liant=%.0f kg",
        result['Resistance'], result['Diffusion_Cl'], result['Carbonatation'],
        result['Ratio_E_L'], result['Liant_Total'],
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PRÉDICTION AVEC MÉTAKAOLIN
# ═══════════════════════════════════════════════════════════════════════════════

def predict_with_mk(
    composition: Dict[str, float],
    model: Any,
    feature_list: Optional[List[str]] = None,
    mk_corrector: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, float]:
    """
    Prédiction intégrant la correction Métakaolin empirique.

    Stratégie post-processing :
      1. Prédiction de base (MK ignoré par le modèle — non dans RAW_FEATURES)
      2. Si MK > 0 et mk_corrector fourni :
         - Résistance    : +correction (MPa) — gain pouzzolanaque ✅
         - Diffusion Cl⁻: ×(1 - factor_cl)  — réduction porosité ✅
         - Carbonatation : ×(1 + factor_carb) — légère hausse à fort taux ✅ [3]
           (MK consomme Ca(OH)₂ → réserve alcaline réduite)

    Règles physiques (littérature) :
      MK 10-15 % :
        Résistance    : +5 à +20 MPa
        Diffusion Cl⁻ : -30 à -50 %
        Carbonatation : ±0 à +5 % (effet quasi-nul à 15 %)
      MK > 20 % :
        Résistance    : plafonne (clip 25 MPa dans MKCorrector)
        Carbonatation : +5 à +15 % (Ca(OH)₂ trop consommé)

    Args:
        composition:  Dict dosages, peut contenir 'Metakaolin' (kg/m³)
        model:        Modèle ML (same as predict_concrete_properties)
        feature_list: Ignoré (compatibilité ascendante)
        mk_corrector: Instance MKCorrector v4.0 (ou None → pas de correction)
        validate:     Valider la composition avant prédiction

    Returns:
        Même structure que predict_concrete_properties()
    """

    # ── 1. Prédiction base ────────────────────────────────────────────────────
    # Note : 'Metakaolin' n'est pas dans RAW_FEATURES → ignoré par le modèle
    # C'est intentionnel : on le gère en post-processing

    predictions = predict_concrete_properties(
        composition=composition,
        model=model,
        feature_list=feature_list,
        validate=validate,
    )

    # ── 2. Correction MK ─────────────────────────────────────────────────────

    mk_dose = float(composition.get('Metakaolin', 0))

    if mk_dose <= 0 or mk_corrector is None:
        return predictions    # Pas de MK → résultat identique à la base

    try:
        # Correction résistance (modèle empirique v4.0 — forme en cloche)
        correction_mpa = mk_corrector.predict_correction(composition)
        predictions['Resistance'] = round(
            predictions['Resistance'] + correction_mpa, 2
        )

        # Effets différenciés sur durabilité
        ciment    = float(composition.get('Ciment', 350))
        liant_tot = ciment + float(composition.get('Laitier', 0)) \
                           + float(composition.get('CendresVolantes', 0)) \
                           + mk_dose
        mk_pct = mk_dose / (liant_tot + 1e-5)   # fraction massique réelle

        # Diffusion Cl⁻ : réduction due à l'affinement de la microstructure
        # Modèle linéaire borné : -5 % à -40 % selon taux MK
        factor_cl = np.clip(0.5 * mk_pct / 0.15, 0.05, 0.40)
        predictions['Diffusion_Cl'] = round(
            float(predictions['Diffusion_Cl']) * (1.0 - factor_cl), 3
        )

        # Carbonatation : légère hausse à fort taux MK (Ca(OH)₂ consommé)
        # Neutre à 10-15 %, +5-15 % au-delà de 20 %
        if mk_pct > 0.15:
            factor_carb = 0.5 * (mk_pct - 0.15) / 0.10   # 0 → 0.5 entre 15% et 25%
            factor_carb = min(factor_carb, 0.15)           # Plafonné à +15 %
            predictions['Carbonatation'] = round(
                float(predictions['Carbonatation']) * (1.0 + factor_carb), 2
            )
        # Entre 0-15 % : pas de correction carbonatation (effet quasi-nul)

        logger.debug(
            "[predictor-mk] MK=%.0f kg (%.0f%%) | ΔR=+%.1f MPa | "
            "ΔDiff=-%.0f%% | ΔCarb=%+.0f%%",
            mk_dose, mk_pct * 100, correction_mpa,
            factor_cl * 100,
            (factor_carb * 100) if mk_pct > 0.15 else 0,
        )

    except Exception as exc:
        logger.warning(
            "[predictor-mk] Correction MK échouée (%s) — résultat de base conservé",
            exc,
        )

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_features() -> List[str]:
    """Retourne la liste des features passées au modèle (après engineering)."""
    return MODEL_FEATURES_ORDER.copy()


def get_raw_features() -> List[str]:
    """Retourne la liste des features brutes saisies par l'utilisateur."""
    return RAW_FEATURES.copy()


def verify_features_alignment(model: Any, log: bool = True) -> bool:
    """
    Vérifie que le modèle accepte les 15 colonnes de MODEL_FEATURES_ORDER.

    Crée un DataFrame de test avec des valeurs neutres et appelle predict().
    Si le modèle lève une exception → misalignment détecté.

    Args:
        model:  Modèle ML chargé
        log:    Émettre un log de résultat

    Returns:
        True si alignement correct, False sinon
    """
    try:
        # Composition de test → engineer_features → 16 cols
        test_composition = {f: 0.5 for f in RAW_FEATURES}
        test_composition.update({
            'Ciment': 280.0, 'Eau': 180.0, 'Age': 28.0,
            'GravilonsGros': 1100.0, 'SableFin': 750.0,
        })
        df_test = pd.DataFrame([test_composition])
        df_eng  = engineer_features(df_test)
        X_test  = df_eng[MODEL_FEATURES_ORDER]
        model.predict(X_test)

        if log:
            logger.info(
                "[predictor] Alignement OK — modèle accepte %d features",
                len(MODEL_FEATURES_ORDER),
            )
        return True

    except Exception as exc:
        if log:
            logger.error(
                "[predictor] MISALIGNMENT DÉTECTÉ — %s.\n"
                "Vérifier MODEL_FEATURES_ORDER vs features d'entraînement.",
                exc,
            )
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT PUBLIC
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Fonctions principales
    'predict_concrete_properties',
    'predict_with_mk',
    'engineer_features',
    'validate_composition',
    # Utilitaires
    'get_default_features',
    'get_raw_features',
    'verify_features_alignment',
    # Constantes
    'MODEL_FEATURES_ORDER',
    'RAW_FEATURES',
    'BOUNDS_ERROR',
    'BOUNDS_WARNING',
]