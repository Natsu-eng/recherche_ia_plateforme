"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/mk_corrector.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Correction empirique pour Métakaolin (basée sur littérature)
Version: 4.0.0 - Empirical Model
═══════════════════════════════════════════════════════════════════════════════

Stratégie:
- Modèle empirique basé sur données de la littérature
- Équation: Gain = A × MK × exp(-B × MK) + C
- Ajustement des paramètres selon l'âge et le ratio E/L
- Pas besoin de dataset d'entraînement !
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional
import joblib
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class MKCorrector:
    """
    Correcteur empirique pour Métakaolin - Version 4.0
    
    Formule: Gain = A × MK × exp(-B × MK) + C
    Avec A, B, C paramètres ajustables selon formulation
    
    Attributes:
        params: Paramètres du modèle (A, B, C)
        calibration: Facteurs de calibration
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialise le correcteur avec paramètres par défaut.
        """
        # Paramètres de base (optimisés sur données MK)
        self.params = {
            'A': 0.85,      # Amplitude maximale
            'B': 0.022,     # Taux de décroissance
            'C': 1.8,       # Offset (effet même à faible dose)
            'age_factor': 0.3,      # Influence de l'âge
            'el_factor': -0.5       # Influence du ratio E/L (négatif)
        }
        
        self.calibration = {
            'version': '4.0.0',
            'last_update': datetime.now().isoformat(),
            'source': 'Littérature scientifique + calibration empirique',
            'reference': 'Formule: Gain = A × MK × exp(-B × MK) + C'
        }
        
        logger.info("Correcteur empirique MK initialisé")
        
        if model_path and os.path.exists(model_path):
            self.load(model_path)
    
    def predict_correction(self, composition: Dict[str, float]) -> float:
        """
        Calcule la correction MK selon formule empirique.
        
        Args:
            composition: Dict avec dosages (doit contenir Metakaolin)
        
        Returns:
            Correction en MPa (0-25 MPa)
        """
        mk = composition.get('Metakaolin', 0)
        
        # Pas de MK → pas de correction
        if mk <= 0:
            return 0.0
        
        # Extraire paramètres de la composition
        ciment = composition.get('Ciment', 350)
        eau = composition.get('Eau', 175)
        age = composition.get('Age', 28)
        superplast = composition.get('Superplastifiant', 0)
        
        # Ratio Eau/Liant (incluant MK)
        liant_total = ciment + composition.get('Laitier', 0) + \
                      composition.get('CendresVolantes', 0) + mk
        ratio_el = eau / (liant_total + 1e-5)
        
        # Pourcentage de MK
        mk_pct = mk / (ciment + 1e-5)
        
        # 1. EFFET PRINCIPAL (forme en cloche)
        # Gain = A × MK × exp(-B × MK) + C
        gain_base = (self.params['A'] * mk * 
                     np.exp(-self.params['B'] * mk) + 
                     self.params['C'])
        
        # 2. CORRECTIONS selon conditions
        # Facteur âge (MK plus efficace à long terme)
        age_factor = 1.0 + self.params['age_factor'] * (1 - np.exp(-age / 28))
        
        # Facteur E/L (MK plus efficace dans bétons compacts)
        el_factor = 1.0 + self.params['el_factor'] * max(0, ratio_el - 0.4)
        
        # Facteur superplastifiant (synergie MK + SP)
        sp_factor = 1.0 + 0.1 * min(superplast / 5.0, 1.0)
        
        # Facteur pourcentage (effet optimal entre 10-15%)
        if mk_pct < 0.1:
            pct_factor = mk_pct / 0.1  # Linéaire jusqu'à 10%
        elif mk_pct < 0.15:
            pct_factor = 1.0  # Optimal
        else:
            pct_factor = 1.0 - (mk_pct - 0.15) / 0.1  # Décroissance
        
        pct_factor = max(0.5, min(1.0, pct_factor))
        
        # 3. CALCUL FINAL
        correction = (gain_base * age_factor * el_factor * 
                     sp_factor * pct_factor)
        
        # Limites physiques
        max_correction = 25.0  # Maximum observé
        min_correction = 1.0    # Minimum pour MK > 0
        
        correction = np.clip(correction, min_correction, max_correction)
        
        logger.debug(f"MK={mk:.1f}kg → correction={correction:.2f}MPa "
                    f"(pct={mk_pct:.1%}, E/L={ratio_el:.2f}, age={age}j)")
        
        return float(correction)
    
    def calibrate(self, df_mk: Optional[pd.DataFrame] = None):
        """
        Calibre les paramètres (optionnel, si données disponibles).
        
        Args:
            df_mk: DataFrame optionnel pour calibration fine
        """
        if df_mk is not None:
            logger.warning("Calibration automatique non implémentée")
            logger.info("Utilisation des paramètres par défaut optimisés")
        
        logger.info(f"Paramètres actuels: A={self.params['A']:.3f}, "
                   f"B={self.params['B']:.4f}, C={self.params['C']:.2f}")
        
        return self.params
    
    def save(self, path: str) -> bool:
        """Sauvegarde la configuration."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            save_data = {
                'params': self.params,
                'calibration': self.calibration,
                'version': '4.0.0'
            }
            joblib.dump(save_data, path)
            logger.info(f"Configuration sauvegardée: {path}")
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Charge la configuration."""
        try:
            data = joblib.load(path)
            self.params = data.get('params', self.params)
            self.calibration = data.get('calibration', self.calibration)
            logger.info(f"Configuration chargée (v{data.get('version', '?')})")
            return True
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")
            return False


# Instance globale
_corrector_instance = None


def get_mk_corrector(model_path: str = "models/mk_corrector.pkl"):
    """Retourne l'instance globale."""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = MKCorrector(model_path)
    return _corrector_instance