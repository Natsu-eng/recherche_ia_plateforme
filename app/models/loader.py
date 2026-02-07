"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/models/loader.py
Version: 2.1.2 - Final (fix KeyError Pct_Laitier + validation complète)
═══════════════════════════════════════════════════════════════════════════════
"""

import joblib
import numpy as np
from pathlib import Path
from typing import Tuple, Any, Dict, List
import logging
import pandas as pd
import json

from app.models.model_config import (
    MODEL_FEATURES_ORDER,
    DEFAULT_MODELS_DIR,
    MODEL_FILENAME,         # "best_model_safe.joblib"
    FEATURES_FILENAME,      # "features.joblib"
    METADATA_FILENAME       # "metadata.json"
)

logger = logging.getLogger(__name__)


def load_production_assets(
    models_dir: Path = DEFAULT_MODELS_DIR
) -> Tuple[Any, List[str], Dict]:
    """
    Charge le modèle, les features et les métadonnées avec validation robuste.
    """
    try:
        models_dir = models_dir.resolve()
        logger.info(f"Chargement depuis : {models_dir}")

        # Chemins
        model_path = models_dir / MODEL_FILENAME
        features_path = models_dir / FEATURES_FILENAME
        metadata_path = models_dir / METADATA_FILENAME

        # Vérification existence
        for p, name in [(model_path, "modèle"), (features_path, "features"), (metadata_path, "métadonnées")]:
            if not p.exists():
                raise FileNotFoundError(f"Fichier manquant : {p} ({name})")

        # Chargement modèle
        logger.info("Chargement modèle...")
        model = joblib.load(model_path)
        logger.info(f"Modèle chargé : {type(model).__name__}")

        # Chargement features → conversion robuste
        logger.info("Chargement features...")
        features_raw = joblib.load(features_path)

        if isinstance(features_raw, np.ndarray):
            features = features_raw.tolist()
            logger.info("Conversion numpy.ndarray → list Python effectuée")
        elif isinstance(features_raw, list):
            features = features_raw
        else:
            raise TypeError(f"Format inattendu pour features : {type(features_raw)}")

        if len(features) != 15:
            raise ValueError(f"15 features attendues, {len(features)} trouvées")

        # Vérification ordre
        if features == MODEL_FEATURES_ORDER:
            logger.info("Ordre des features parfait")
        else:
            logger.warning("Ordre features chargé ≠ MODEL_FEATURES_ORDER")
            logger.warning(f"Chargé (5 premiers) : {features[:5]}")
            logger.warning(f"Attendu (5 premiers): {MODEL_FEATURES_ORDER[:5]}")

        # Chargement métadonnées
        logger.info("Chargement métadonnées...")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # ─────────────────────────────────────────────────────
        # VALIDATION RAPIDE DU MODÈLE (test C25/30)
        # ─────────────────────────────────────────────────────
        logger.info("Validation rapide du modèle (formulation C25/30)...")
        test_comp = {
            "Ciment": 280.0, "Laitier": 0.0, "CendresVolantes": 0.0,
            "Eau": 180.0, "Superplastifiant": 0.0,
            "GravilonsGros": 1100.0, "SableFin": 750.0, "Age": 28.0
        }
        df_test = pd.DataFrame([test_comp])

        # Fonction minimale → DOIT créer TOUTES les features utilisées par le modèle
        def engineer_minimal(df):
            df = df.copy()
            df['Liant_Total'] = df['Ciment'] + df['Laitier'] + df['CendresVolantes']
            df['Ratio_E_L'] = df['Eau'] / (df['Liant_Total'] + 1e-5)
            df['Pct_Laitier'] = df['Laitier'] / (df['Liant_Total'] + 1e-5)          # ← AJOUTÉ
            df['Pct_CendresVolantes'] = df['CendresVolantes'] / (df['Liant_Total'] + 1e-5)  # ← AJOUTÉ (si besoin)
            df['Log_Age'] = np.log(df['Age'] + 1)
            df['Sqrt_Age'] = np.sqrt(df['Age'])
            df['Ciment_x_LogAge'] = df['Ciment'] * df['Log_Age']
            df['Eau_x_SP'] = df['Eau'] * df['Superplastifiant']
            df['Liant_x_RatioEL'] = df['Liant_Total'] * df['Ratio_E_L']
            volume_total = df[['Ciment','Laitier','CendresVolantes','Eau','GravilonsGros','SableFin']].sum(axis=1)
            df['Ratio_Granulats'] = (df['GravilonsGros'] + df['SableFin']) / (volume_total + 1e-5)
            df.replace([np.inf, -np.inf], 0, inplace=True)
            return df

        df_eng = engineer_minimal(df_test)
        
        # Vérification rapide : toutes les features doivent exister
        missing_in_eng = [f for f in features if f not in df_eng.columns]
        if missing_in_eng:
            logger.error(f"Features manquantes dans df_eng : {missing_in_eng}")
            raise ValueError(f"Colonnes manquantes pour validation : {missing_in_eng}")

        X_test = df_eng[features]
        pred_test = model.predict(X_test)[0][0]

        expected = 27.02
        if abs(pred_test - expected) < 0.5:
            logger.info(f"Validation OK : Résistance C25/30 = {pred_test:.2f} MPa (attendu ~{expected})")
        else:
            logger.warning(f"Attention : Résistance C25/30 = {pred_test:.2f} MPa (attendu ~{expected})")

        logger.info("═"*60)
        logger.info("ASSETS CHARGÉS AVEC SUCCÈS")
        logger.info("═"*60)

        return model, features, metadata

    except Exception as e:
        logger.error(f"Erreur critique lors du chargement : {e}", exc_info=True)
        raise


# Test rapide si exécuté directement
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        model, features, metadata = load_production_assets()
        print("Test réussi !")
        print(f"Modèle : {type(model).__name__}")
        print(f"Features : {len(features)} ({features[:5]}...)")
    except Exception as e:
        print("Erreur :", e)