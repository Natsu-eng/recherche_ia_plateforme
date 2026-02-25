"""
═══════════════════════════════════════════════════════════════════════════════
SCRIPT: scripts/train_mk_corrector_v2.py
But: Entraîner le correcteur MK version polynomiale
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.models.loader import load_production_assets
from app.core.mk_corrector import MKCorrector, reset_mk_corrector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_mk_dataset(filepath: str) -> pd.DataFrame:
    """Charge et prépare le dataset MK."""
    
    logger.info(f"Chargement dataset: {filepath}")
    
    if not os.path.exists(filepath):
        logger.error(f"Fichier non trouvé: {filepath}")
        return pd.DataFrame()
    
    # Chargement
    df = pd.read_excel(filepath)
    logger.info(f"Colonnes trouvées: {list(df.columns)}")
    
    # Mapping des colonnes
    column_map = {
        'Cement Kg/m3': 'Ciment',
        'Water Kg/m3': 'Eau',
        'Sand Kg/m3': 'SableFin',
        'Gravel Kg/m3': 'GravilonsGros',
        'Superplasticizer kg/m3': 'Superplastifiant',
        'Metakaolin Kg/m3': 'Metakaolin',
        'Age': 'Age',
        'Actual Compressive Strength Mpa': 'Resistance'
    }
    
    df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
    
    # Colonnes essentielles
    required = ['Ciment', 'Eau', 'Age', 'Resistance', 'Metakaolin']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        logger.error(f"Colonnes manquantes: {missing}")
        return pd.DataFrame()
    
    # Nettoyage
    df = df[df['Resistance'] <= 120]
    df = df[df['Resistance'] >= 5]
    df = df[df['Metakaolin'] >= 0]
    df = df[df['Metakaolin'] <= 200]
    
    logger.info(f"Dataset prêt: {len(df)} échantillons")
    logger.info(f"  MK: {df['Metakaolin'].min():.0f}-{df['Metakaolin'].max():.0f} kg/m³")
    logger.info(f"  Résistance: {df['Resistance'].min():.0f}-{df['Resistance'].max():.0f} MPa")
    
    return df


def main():
    """Point d'entrée principal."""
    
    logger.info("="*60)
    logger.info("ENTRAÎNEMENT CORRECTEUR MK V2")
    logger.info("="*60)
    
    # Reset instance globale
    reset_mk_corrector()
    
    # Chemins
    mk_data_path = "data/metakaolin_dataset.xlsx"
    model_output_path = "models/mk_corrector.pkl"
    
    # Créer dossier
    os.makedirs("models", exist_ok=True)
    
    # Charger modèle UCI
    logger.info("Chargement modèle UCI...")
    model, features, metadata = load_production_assets()
    
    # Charger dataset MK
    df_mk = load_mk_dataset(mk_data_path)
    if len(df_mk) == 0:
        return
    
    # Créer et entraîner correcteur
    logger.info("Création du correcteur...")
    corrector = MKCorrector()
    
    # Entraînement
    logger.info("Démarrage entraînement...")
    metrics = corrector.train(df_mk, model, features, test_split=0.2)
    
    # Sauvegarde
    logger.info("Sauvegarde du modèle...")
    corrector.save(model_output_path)
    
    # Test final
    logger.info("Test final sur quelques points...")
    test_points = [20, 35, 50, 80, 100]
    base_comp = {
        'Ciment': 350, 'Eau': 175, 'Age': 28,
        'Laitier': 0, 'CendresVolantes': 0,
        'Superplastifiant': 0, 'GravilonsGros': 1000, 'SableFin': 800
    }
    
    for mk in test_points:
        comp = base_comp.copy()
        comp['Metakaolin'] = mk
        corr = corrector.predict_correction(comp)
        logger.info(f"  MK={mk:3d} kg → correction={corr:5.2f} MPa")
    
    logger.info("="*60)
    logger.info("ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
    logger.info("="*60)


if __name__ == "__main__":
    main()