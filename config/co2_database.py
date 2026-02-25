"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: Base de Données CO₂ - ACV Béton
Fichier: config/co2_database.py
Auteur: Expert ACV - IMT Nord Europe
Version: 1.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

Source: ACV_-_Tableau_CO2_Ciments_-_10-12-2025.xlsx
Norme: NF EN 15804 (Empreinte environnementale)

Données validées pour calcul empreinte carbone béton
"""

from typing import Dict, Optional
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════
# FACTEURS D'ÉMISSION CO₂ PAR CONSTITUANT
# ═══════════════════════════════════════════════════════════════════════════════

# En kg CO₂ équivalent par tonne de matériau
CO2_FACTORS_KG_PER_TONNE = {
    # Liants
    'Clinker': 806.0,              # Source: ATILH 2024
    'Laitier': 45.0,               # Laitier de haut-fourneau
    'CendresVolantes': 10.0,       # Cendres volantes
    'Metakaolin': 260.0,           # Métakaolin (argile calcinée)
    'Pouzzolane': 2.0,             # Pouzzolane naturelle
    'ArgileCalcinee': 260.0,       # Argile calcinée (Metakaolin)
    'Calcaire': 2.5,               # Filler calcaire
    'Gypse': 8.0,                  # Régulateur prise
    
    # Granulats
    'Sable': 5.0,                  # Sable naturel 0/4
    'Gravier': 5.0,                # Gravillons 4/20
    
    # Eau & Adjuvants
    'Eau': 0.3,                    # Eau de gâchage
    'Superplastifiant': 1500.0,    # Adjuvants organiques
}


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITION DES CIMENTS NORMALISÉS (NF EN 197-1)
# ═══════════════════════════════════════════════════════════════════════════════

# Proportions en % massique (Base 100%)
CEMENT_COMPOSITIONS = {
    # CEM I - Portland pur
    'CEM I': {
        'Clinker': 0.94,
        'Gypse': 0.06
    },
    
    # CEM II - Ciments Portland composés
    'CEM II/A-LL': {              # 6-20% calcaire
        'Clinker': 0.79,
        'Calcaire': 0.15,
        'Gypse': 0.06
    },
    
    'CEM II/B-LL': {              # 21-35% calcaire
        'Clinker': 0.64,
        'Calcaire': 0.31,
        'Gypse': 0.05
    },
    
    'CEM II/A-S': {               # 6-20% laitier
        'Clinker': 0.74,
        'Laitier': 0.20,
        'Gypse': 0.06
    },
    
    'CEM II/B-S': {               # 21-35% laitier
        'Clinker': 0.60,
        'Laitier': 0.35,
        'Gypse': 0.05
    },
    
    # CEM III - Ciments de haut fourneau
    'CEM III/A': {                # 36-65% laitier
        'Clinker': 0.45,
        'Laitier': 0.50,
        'Gypse': 0.05
    },
    
    'CEM III/B': {                # 66-80% laitier
        'Clinker': 0.23,
        'Laitier': 0.72,
        'Gypse': 0.05
    },
    
    'CEM III/C': {                # 81-95% laitier
        'Clinker': 0.10,
        'Laitier': 0.85,
        'Gypse': 0.05
    },
    
    # CEM IV - Ciments pouzzolaniques
    'CEM IV/A': {                 # 11-35% pouzzolane
        'Clinker': 0.71,
        'Pouzzolane': 0.24,
        'Gypse': 0.05
    },
    
    # CEM V - Ciments composés
    'CEM V/A': {                  # Laitier + Cendres (18-30% chacun)
        'Clinker': 0.50,
        'Laitier': 0.25,
        'CendresVolantes': 0.20,
        'Gypse': 0.05
    },
    
    # LC3 - Low Carbon Cement (Nouveau béton bas-carbone)
    'LC3-50': {
        'Clinker': 0.50,
        'ArgileCalcinee': 0.15,
        'Calcaire': 0.30,
        'Gypse': 0.05
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# EMPREINTE CO₂ PRÉCALCULÉE PAR TYPE DE CIMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_cement_co2() -> Dict[str, float]:
    """
    Calcule l'empreinte CO₂ de chaque type de ciment.
    
    Returns:
        Dict avec empreinte en kg CO₂/tonne de ciment
    """
    cement_co2 = {}
    
    for cement_name, composition in CEMENT_COMPOSITIONS.items():
        total_co2 = 0.0
        
        for constituent, proportion in composition.items():
            co2_factor = CO2_FACTORS_KG_PER_TONNE.get(constituent, 0.0)
            total_co2 += proportion * co2_factor
        
        cement_co2[cement_name] = round(total_co2, 1)
    
    return cement_co2


# Empreinte CO₂ par type de ciment (kg CO₂/tonne)
CEMENT_CO2_KG_PER_TONNE = _calculate_cement_co2()


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS POUR RÉSULTATS CO₂
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CO2Result:
    """Résultat complet du calcul CO₂."""
    
    # Empreintes par matériau (kg CO₂)
    co2_ciment: float
    co2_laitier: float
    co2_cendres: float
    co2_sable: float
    co2_gravier: float
    co2_eau: float
    co2_adjuvants: float
    
    # Total
    co2_total_kg_m3: float
    
    # Métadonnées
    cement_type: str
    cement_co2_factor: float      # kg CO₂/tonne ciment
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire."""
        return {
            'co2_ciment': self.co2_ciment,
            'co2_laitier': self.co2_laitier,
            'co2_cendres': self.co2_cendres,
            'co2_sable': self.co2_sable,
            'co2_gravier': self.co2_gravier,
            'co2_eau': self.co2_eau,
            'co2_adjuvants': self.co2_adjuvants,
            'co2_total_kg_m3': self.co2_total_kg_m3,
            'cement_type': self.cement_type,
            'cement_co2_factor': self.cement_co2_factor
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES UTILES
# ═══════════════════════════════════════════════════════════════════════════════

# Classes environnementales selon empreinte CO₂
CO2_CLASSES = {
    'Très Faible': (0, 200),      # < 200 kg/m³ (LC3, CEM III/C)
    'Faible': (200, 280),          # 200-280 kg/m³ (CEM III/B)
    'Moyen': (280, 350),           # 280-350 kg/m³ (CEM II/B, CEM III/A)
    'Élevé': (350, 420),           # 350-420 kg/m³ (CEM II/A, CEM IV)
    'Très Élevé': (420, 1000)      # > 420 kg/m³ (CEM I)
}


# Labels environnementaux français
ENVIRONMENTAL_LABELS = {
    'HQE': 'Haute Qualité Environnementale',
    'BBC': 'Bâtiment Basse Consommation',
    'NF': 'Norme Française',
    'RE2020': 'Réglementation Environnementale 2020'
}


# Équivalences CO₂ pédagogiques
CO2_EQUIVALENTS = {
    'voiture_km': 0.12,            # 1 kg CO₂ = 8.3 km en voiture
    'arbre_annee': 25.0,           # 1 arbre absorbe ~25 kg CO₂/an
    'repas_viande': 7.0,           # 1 repas viande = ~7 kg CO₂
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_cement_co2(cement_type: str) -> float:
    """
    Retourne l'empreinte CO₂ d'un type de ciment.
    
    Args:
        cement_type: Type de ciment (ex: 'CEM I', 'CEM III/B')
    
    Returns:
        kg CO₂/tonne de ciment
    """
    return CEMENT_CO2_KG_PER_TONNE.get(cement_type, CEMENT_CO2_KG_PER_TONNE['CEM I'])


def get_co2_class(co2_total: float) -> str:
    """
    Détermine la classe environnementale d'une formulation.
    
    Args:
        co2_total: Empreinte totale en kg CO₂/m³
    
    Returns:
        Classe environnementale
    """
    for class_name, (min_val, max_val) in CO2_CLASSES.items():
        if min_val <= co2_total < max_val:
            return class_name
    
    return 'Très Élevé'


def get_reduction_potential(current_co2: float, target_class: str = 'Faible') -> Dict:
    """
    Calcule le potentiel de réduction CO₂.
    
    Args:
        current_co2: Empreinte actuelle (kg CO₂/m³)
        target_class: Classe cible
    
    Returns:
        Dict avec réduction possible et recommandations
    """
    target_max = CO2_CLASSES[target_class][1]
    reduction_needed = max(0, current_co2 - target_max)
    reduction_percent = (reduction_needed / current_co2 * 100) if current_co2 > 0 else 0
    
    return {
        'current_co2': current_co2,
        'target_max': target_max,
        'reduction_needed': reduction_needed,
        'reduction_percent': reduction_percent,
        'achievable': reduction_percent < 50  # Réduction > 50% = difficile
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'CO2_FACTORS_KG_PER_TONNE',
    'CEMENT_COMPOSITIONS',
    'CEMENT_CO2_KG_PER_TONNE',
    'CO2_CLASSES',
    'CO2_EQUIVALENTS',
    'CO2Result',
    'get_cement_co2',
    'get_co2_class',
    'get_reduction_potential'
]