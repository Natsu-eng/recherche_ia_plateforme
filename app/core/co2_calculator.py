"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: Calculateur CO₂ - Empreinte Carbone Béton
Fichier: app/core/co2_calculator.py
Auteur: Expert ACV - IMT Nord Europe
Version: 1.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

Calcul empreinte carbone selon NF EN 15804
Validation : ATILH, FDES, RE2020
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from config.co2_database import (
    CO2_FACTORS_KG_PER_TONNE,
    CEMENT_CO2_KG_PER_TONNE,
    CO2Result,
    get_cement_co2,
    get_co2_class,
    get_reduction_potential
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class CO2Calculator:
    """
    Calculateur d'empreinte carbone pour formulations béton.
    
    Méthode de calcul :
    1. Identifier type de ciment
    2. Calculer CO₂ de chaque constituant
    3. Sommer les contributions
    4. Classifier résultat
    
    Thread-safe : Oui
    """
    
    def __init__(self):
        """Initialise le calculateur."""
        self.co2_factors = CO2_FACTORS_KG_PER_TONNE
        self.cement_co2 = CEMENT_CO2_KG_PER_TONNE
        logger.debug("Calculateur initialisé")
    
    def calculate(
        self,
        formulation: Dict[str, float],
        cement_type: str = 'CEM I'
    ) -> CO2Result:
        """
        Calcule l'empreinte CO₂ d'une formulation.
        
        Args:
            formulation: Dict avec dosages en kg/m³
                - Ciment (kg/m³)
                - Laitier (kg/m³) [optionnel]
                - CendresVolantes (kg/m³) [optionnel]
                - Eau (kg/m³)
                - SableFin (kg/m³)
                - GravilonsGros (kg/m³)
                - Superplastifiant (kg/m³) [optionnel]
            
            cement_type: Type de ciment ('CEM I', 'CEM II/B-LL', 'CEM III/B', etc.)
        
        Returns:
            CO2Result avec détail par constituant
        
        Raises:
            ValueError: Si formulation invalide
        """
        try:
            # ─────────────────────────────────────────────────────
            # 1. VALIDATION
            # ─────────────────────────────────────────────────────
            
            self._validate_formulation(formulation)
            
            # ─────────────────────────────────────────────────────
            # 2. EXTRACTION DOSAGES
            # ─────────────────────────────────────────────────────
            
            # Obligatoires
            ciment = float(formulation.get('Ciment', 0))
            eau = float(formulation.get('Eau', 0))
            sable = float(formulation.get('SableFin', 0))
            gravier = float(formulation.get('GravilonsGros', 0))
            
            # Optionnels (additions minérales)
            laitier = float(formulation.get('Laitier', 0))
            cendres = float(formulation.get('CendresVolantes', 0))
            adjuvants = float(formulation.get('Superplastifiant', 0))
            
            logger.debug(
                f"[CO2] Calcul pour: C={ciment}, L={laitier}, CV={cendres}, "
                f"E={eau}, S={sable}, G={gravier}"
            )
            
            # ─────────────────────────────────────────────────────
            # 3. FACTEUR CO₂ DU CIMENT
            # ─────────────────────────────────────────────────────
            
            cement_co2_factor = get_cement_co2(cement_type)
            
            # ─────────────────────────────────────────────────────
            # 4. CALCUL CO₂ PAR CONSTITUANT
            # ─────────────────────────────────────────────────────
            
            # Ciment (kg CO₂)
            co2_ciment = (ciment / 1000) * cement_co2_factor
            
            # Additions minérales (kg CO₂)
            # Note: Si utilisées en substitution du ciment, on compte leur propre facteur
            co2_laitier = (laitier / 1000) * self.co2_factors['Laitier']
            co2_cendres = (cendres / 1000) * self.co2_factors['CendresVolantes']
            
            # Granulats (kg CO₂)
            co2_sable = (sable / 1000) * self.co2_factors['Sable']
            co2_gravier = (gravier / 1000) * self.co2_factors['Gravier']
            
            # Eau (kg CO₂)
            co2_eau = (eau / 1000) * self.co2_factors['Eau']
            
            # Adjuvants (kg CO₂)
            co2_adjuvants = (adjuvants / 1000) * self.co2_factors['Superplastifiant']
            
            # ─────────────────────────────────────────────────────
            # 5. TOTAL
            # ─────────────────────────────────────────────────────
            
            co2_total = (
                co2_ciment +
                co2_laitier +
                co2_cendres +
                co2_sable +
                co2_gravier +
                co2_eau +
                co2_adjuvants
            )
            
            logger.info(
                f"Empreinte calculée: {co2_total:.1f} kg CO₂/m³ avec "
                f"(Ciment {cement_type})"
            )
            
            # ─────────────────────────────────────────────────────
            # 6. RÉSULTAT
            # ─────────────────────────────────────────────────────
            
            return CO2Result(
                co2_ciment=round(co2_ciment, 2),
                co2_laitier=round(co2_laitier, 2),
                co2_cendres=round(co2_cendres, 2),
                co2_sable=round(co2_sable, 2),
                co2_gravier=round(co2_gravier, 2),
                co2_eau=round(co2_eau, 2),
                co2_adjuvants=round(co2_adjuvants, 2),
                co2_total_kg_m3=round(co2_total, 1),
                cement_type=cement_type,
                cement_co2_factor=cement_co2_factor
            )
        
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Calcul error: {e}", exc_info=True)
            raise RuntimeError(f"Erreur calcul CO₂: {e}")
    
    def _validate_formulation(self, formulation: Dict[str, float]) -> None:
        """
        Valide une formulation.
        
        Raises:
            ValueError: Si formulation invalide
        """
        # Vérifier présence dosages obligatoires
        required = ['Ciment', 'Eau', 'SableFin', 'GravilonsGros']
        
        for param in required:
            if param not in formulation:
                raise ValueError(f"Paramètre obligatoire manquant: {param}")
            
            value = formulation[param]
            if not isinstance(value, (int, float)):
                raise ValueError(f"{param} doit être numérique, reçu: {type(value)}")
            
            if value < 0:
                raise ValueError(f"{param} ne peut pas être négatif: {value}")
        
        # Vérifier cohérence
        ciment = formulation['Ciment']
        if ciment <= 0:
            raise ValueError(f"Dosage ciment invalide: {ciment} kg/m³")
        
        if ciment > 600:
            logger.warning(f"Dosage ciment élevé: {ciment} kg/m³")
    
    def compare_cements(
        self,
        formulation: Dict[str, float],
        cement_types: Optional[List[str]] = None
    ) -> Dict[str, CO2Result]:
        """
        Compare l'empreinte CO₂ pour différents types de ciments.
        
        Args:
            formulation: Formulation de base
            cement_types: Liste types à comparer (None = tous)
        
        Returns:
            Dict {cement_type: CO2Result}
        """
        if cement_types is None:
            cement_types = list(self.cement_co2.keys())
        
        results = {}
        
        for cement_type in cement_types:
            try:
                results[cement_type] = self.calculate(formulation, cement_type)
            except Exception as e:
                logger.error(f"Erreur comparaison {cement_type}: {e}")
        
        return results
    
    def get_breakdown_percentages(self, result: CO2Result) -> Dict[str, float]:
        """
        Calcule la répartition en % de chaque constituant.
        
        Args:
            result: Résultat CO2Result
        
        Returns:
            Dict {constituant: pourcentage}
        """
        total = result.co2_total_kg_m3
        
        if total == 0:
            return {}
        
        return {
            'Ciment': round(result.co2_ciment / total * 100, 1),
            'Laitier': round(result.co2_laitier / total * 100, 1),
            'Cendres': round(result.co2_cendres / total * 100, 1),
            'Sable': round(result.co2_sable / total * 100, 1),
            'Gravier': round(result.co2_gravier / total * 100, 1),
            'Eau': round(result.co2_eau / total * 100, 1),
            'Adjuvants': round(result.co2_adjuvants / total * 100, 1)
        }
    
    def suggest_reduction(
        self,
        current_result: CO2Result,
        target_reduction_percent: float = 30.0
    ) -> Dict:
        """
        Suggère des pistes de réduction CO₂.
        
        Args:
            current_result: Résultat actuel
            target_reduction_percent: Réduction cible (%)
        
        Returns:
            Dict avec suggestions
        """
        current_co2 = current_result.co2_total_kg_m3
        target_co2 = current_co2 * (1 - target_reduction_percent / 100)
        
        suggestions = []
        
        # Suggestion 1: Changer type de ciment
        current_type = current_result.cement_type
        
        if current_type == 'CEM I':
            suggestions.append({
                'action': 'Utiliser CEM III/B au lieu de CEM I',
                'reduction_potentielle': '~60-70%',
                'impact': 'Fort',
                'facilite': 'Facile'
            })
        elif 'CEM II' in current_type:
            suggestions.append({
                'action': 'Passer à CEM III/B',
                'reduction_potentielle': '~40-50%',
                'impact': 'Fort',
                'facilite': 'Moyen'
            })
        
        # Suggestion 2: Augmenter additions minérales
        if current_result.co2_laitier + current_result.co2_cendres < 5:
            suggestions.append({
                'action': 'Ajouter laitier ou cendres volantes (20-30%)',
                'reduction_potentielle': '~20-30%',
                'impact': 'Moyen',
                'facilite': 'Facile'
            })
        
        # Suggestion 3: Optimiser dosage ciment
        suggestions.append({
            'action': 'Réduire dosage ciment de 10-15%',
            'reduction_potentielle': '~10-15%',
            'impact': 'Moyen',
            'facilite': 'Facile (si résistance le permet)'
        })
        
        return {
            'current_co2': current_co2,
            'target_co2': target_co2,
            'reduction_needed': current_co2 - target_co2,
            'suggestions': suggestions
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def quick_calculate_co2(formulation: Dict[str, float], cement_type: str = 'CEM I') -> float:
    """
    Calcul rapide CO₂ (retourne juste le total).
    
    Args:
        formulation: Dosages en kg/m³
        cement_type: Type de ciment
    
    Returns:
        Empreinte en kg CO₂/m³
    """
    calculator = CO2Calculator()
    result = calculator.calculate(formulation, cement_type)
    return result.co2_total_kg_m3


def get_environmental_grade(co2_total: float) -> Tuple[str, str, str]:
    """
    Détermine le grade environnemental.
    
    Args:
        co2_total: Empreinte totale (kg CO₂/m³)
    
    Returns:
        (classe, emoji, couleur)
    """
    classe = get_co2_class(co2_total)
    
    grades = {
        'Très Faible': ('Très Faible', '🟢', '#2ecc71'),
        'Faible': ('Faible', '🟢', '#27ae60'),
        'Moyen': ('Moyen', '🟡', '#f39c12'),
        'Élevé': ('Élevé', '🟠', '#e67e22'),
        'Très Élevé': ('Très Élevé', '🔴', '#e74c3c')
    }
    
    return grades.get(classe, grades['Très Élevé'])


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'CO2Calculator',
    'quick_calculate_co2',
    'get_environmental_grade'
]