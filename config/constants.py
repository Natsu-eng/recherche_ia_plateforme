"""
═══════════════════════════════════════════════════════════════════════════════
FICHIER: config/constants.py
Description: Constantes métier pour la formulation du béton
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════

Ce fichier centralise :
  - Les bornes physiques de chaque constituant (min, max, défaut)
  - Les labels d'affichage en français
  - Les normes européennes (Eurocodes)
  - Les catégories de béton selon EN 206
"""

from typing import Dict, Any

# ═══════════════════════════════════════════════════════════════════════════════
# BORNES DES CONSTITUANTS DU BÉTON (kg/m³)
# ═══════════════════════════════════════════════════════════════════════════════

BOUNDS: Dict[str, Dict[str, Any]] = {
    # ─── LIANTS HYDRAULIQUES ───
    "Ciment": {
        "min": 150,
        "max": 550,
        "default": 350,
        "step": 10,
        "unit": "kg/m³",
        "description": "Ciment Portland CEM I, CEM II selon EN 197-1",
        "norme": "EN 206 : 150-550 kg/m³ typique"
    },
    
    "Laitier": {
        "min": 0,
        "max": 250,
        "default": 60,
        "step": 10,
        "unit": "kg/m³",
        "description": "Laitier de haut-fourneau moulu (addition type II)",
        "norme": "Taux de substitution < 70% recommandé"
    },
    
    "CendresVolantes": {
        "min": 0,
        "max": 200,
        "default": 0,
        "step": 10,
        "unit": "kg/m³",
        "description": "Cendres volantes siliceuses (addition type II)",
        "norme": "Taux de substitution < 55% (NF EN 450-1)"
    },
    
    # ─── EAU & ADJUVANTS ───
    "Eau": {
        "min": 120,
        "max": 220,
        "default": 175,
        "step": 5,
        "unit": "kg/m³ (litres)",
        "description": "Eau de gâchage selon NF EN 1008",
        "norme": "Ratio E/C : 0.40-0.65 pour béton armé"
    },
    
    "Superplastifiant": {
        "min": 0.0,
        "max": 20.0,
        "default": 4.0,
        "step": 0.5,
        "unit": "kg/m³",
        "description": "Superplastifiant haut réducteur d'eau (HRWR)",
        "norme": "Dosage typique : 0.5-2% du liant"
    },
    
    # ─── GRANULATS ───
    "GravilonsGros": {
        "min": 800,
        "max": 1200,
        "default": 1070,
        "step": 10,
        "unit": "kg/m³",
        "description": "Gravillon 4/20 mm (NF EN 12620)",
        "norme": "Masse volumique apparente 1300-1600 kg/m³"
    },
    
    "SableFin": {
        "min": 600,
        "max": 950,
        "default": 710,
        "step": 10,
        "unit": "kg/m³",
        "description": "Sable 0/4 mm (NF EN 12620)",
        "norme": "Module de finesse MF : 2.2-2.8"
    },
    
    # ─── TEMPS ───
    "Age": {
        "min": 1,
        "max": 365,
        "default": 28,
        "step": 1,
        "unit": "jours",
        "description": "Âge du béton pour essai de résistance",
        "norme": "Résistance caractéristique à 28 jours (EN 206)"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# LABELS D'AFFICHAGE (FR)
# ═══════════════════════════════════════════════════════════════════════════════

LABELS_MAP: Dict[str, str] = {
    "Ciment": "Ciment CEM I/II",
    "Laitier": "Laitier de Haut-Fourneau",
    "CendresVolantes": "Cendres Volantes",
    "Eau": "Eau de Gâchage",
    "Superplastifiant": "Superplastifiant",
    "GravilonsGros": "Gravillons 4/20",
    "SableFin": "Sable 0/4",
    "Age": "Âge du Béton",
    
    # Features engineerées
    "Liant_Total": "Liant Total",
    "Ratio_E_L": "Rapport E/L",
    "Pct_Substitution": "Taux de Substitution",
    
    # Cibles
    "Resistance": "Résistance fc",
    "Diffusion_Cl": "Diffusion Cl⁻",
    "Carbonatation": "Carbonatation",
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSES DE RÉSISTANCE SELON EN 206
# ═══════════════════════════════════════════════════════════════════════════════

RESISTANCE_CLASSES = {
    "C8/10": {"fc_cyl": 8, "fc_cube": 10},
    "C12/15": {"fc_cyl": 12, "fc_cube": 15},
    "C16/20": {"fc_cyl": 16, "fc_cube": 20},
    "C20/25": {"fc_cyl": 20, "fc_cube": 25},
    "C25/30": {"fc_cyl": 25, "fc_cube": 30},
    "C30/37": {"fc_cyl": 30, "fc_cube": 37},
    "C35/45": {"fc_cyl": 35, "fc_cube": 45},
    "C40/50": {"fc_cyl": 40, "fc_cube": 50},
    "C45/55": {"fc_cyl": 45, "fc_cube": 55},
    "C50/60": {"fc_cyl": 50, "fc_cube": 60},
    "C55/67": {"fc_cyl": 55, "fc_cube": 67},
    "C60/75": {"fc_cyl": 60, "fc_cube": 75},
    "C70/85": {"fc_cyl": 70, "fc_cube": 85},
    "C80/95": {"fc_cyl": 80, "fc_cube": 95},
    "C90/105": {"fc_cyl": 90, "fc_cube": 105},
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSES D'EXPOSITION SELON EN 206
# ═══════════════════════════════════════════════════════════════════════════════

EXPOSURE_CLASSES = {
    "XC1": {
        "name": "Carbonatation - Sec",
        "E_L_max": 0.70,
        "fc_min": 20,
        "description": "Intérieur, faible humidité"
    },
    "XC2": {
        "name": "Carbonatation - Humide",
        "E_L_max": 0.65,
        "fc_min": 25,
        "description": "Surfaces en contact avec l'eau"
    },
    "XC3": {
        "name": "Carbonatation - Humidité modérée",
        "E_L_max": 0.60,
        "fc_min": 30,
        "description": "Extérieur abrité"
    },
    "XC4": {
        "name": "Carbonatation - Cycles humide/sec",
        "E_L_max": 0.55,
        "fc_min": 30,
        "description": "Extérieur exposé pluie"
    },
    "XD1": {
        "name": "Chlorures - Humidité modérée",
        "E_L_max": 0.55,
        "fc_min": 30,
        "description": "Surfaces soumises à chlorures aéroportés"
    },
    "XD2": {
        "name": "Chlorures - Humide",
        "E_L_max": 0.50,
        "fc_min": 35,
        "description": "Piscines, eaux industrielles"
    },
    "XD3": {
        "name": "Chlorures - Cycles humide/sec",
        "E_L_max": 0.45,
        "fc_min": 35,
        "description": "Éléments exposés embruns marins, sels de déverglaçage"
    },
    "XS1": {
        "name": "Eau de mer - Aérien",
        "E_L_max": 0.50,
        "fc_min": 35,
        "description": "Structures maritimes, air salin"
    },
    "XS2": {
        "name": "Eau de mer - Immergé",
        "E_L_max": 0.45,
        "fc_min": 40,
        "description": "Parties immergées en permanence"
    },
    "XS3": {
        "name": "Eau de mer - Zone de marnage",
        "E_L_max": 0.40,
        "fc_min": 45,
        "description": "Zone de marnage, projections"
    },
    "XF1": {
        "name": "Gel/Dégel - Saturation modérée",
        "E_L_max": 0.60,
        "fc_min": 30,
        "description": "Surfaces extérieures verticales"
    },
    "XF2": {
        "name": "Gel/Dégel - Saturation modérée + sels",
        "E_L_max": 0.55,
        "fc_min": 30,
        "description": "Surfaces exposées sels de déverglaçage"
    },
    "XF3": {
        "name": "Gel/Dégel - Forte saturation",
        "E_L_max": 0.55,
        "fc_min": 30,
        "description": "Surfaces horizontales exposées pluie et gel"
    },
    "XF4": {
        "name": "Gel/Dégel - Forte saturation + sels",
        "E_L_max": 0.45,
        "fc_min": 35,
        "description": "Routes, trottoirs avec sels de déverglaçage"
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# COÛTS ET ÉMISSIONS (POUR OPTIMISATION) 
# ═══════════════════════════════════════════════════════════════════════════════

MATERIALS_COST_EURO_KG: Dict[str, float] = {
    "Ciment": 0.12,
    "Laitier": 0.04,
    "CendresVolantes": 0.03,
    "Eau": 0.0001,
    "Superplastifiant": 2.5,
    "GravilonsGros": 0.015,
    "SableFin": 0.015
}

CO2_EMISSIONS_KG: Dict[str, float] = {
    "Ciment": 0.9,
    "Laitier": 0.05,
    "CendresVolantes": 0.02,
    "Eau": 0.0001,
    "Superplastifiant": 0.5,
    "GravilonsGros": 0.005,
    "SableFin": 0.005
}

# ═══════════════════════════════════════════════════════════════════════════════
# FORMULATIONS TYPES PRÉDÉFINIES
# ═══════════════════════════════════════════════════════════════════════════════

PRESET_FORMULATIONS = {
    "C25/30 Standard": {
        "Ciment": 280,
        "Laitier": 0,
        "CendresVolantes": 0,
        "Eau": 180,
        "Superplastifiant": 0,
        "GravilonsGros": 1100,
        "SableFin": 750,
        "Age": 28,
        "description": "Béton standard pour ouvrages courants (bâtiment)",
        "classe": "C25/30",
        "exposition": "XC1-XC2"
    },
    
    "C30/37 Armé": {
        "Ciment": 320,
        "Laitier": 40,
        "CendresVolantes": 0,
        "Eau": 170,
        "Superplastifiant": 3,
        "GravilonsGros": 1080,
        "SableFin": 730,
        "Age": 28,
        "description": "Béton armé pour structures bâtiment et génie civil",
        "classe": "C30/37",
        "exposition": "XC3-XC4"
    },
    
    "C35/45 Haute Performance": {
        "Ciment": 380,
        "Laitier": 50,
        "CendresVolantes": 0,
        "Eau": 165,
        "Superplastifiant": 5,
        "GravilonsGros": 1050,
        "SableFin": 700,
        "Age": 28,
        "description": "Béton HP pour structures exigeantes (ponts, parkings)",
        "classe": "C35/45",
        "exposition": "XD1-XD2"
    },
    
    "C50/60 Très Haute Performance": {
        "Ciment": 450,
        "Laitier": 80,
        "CendresVolantes": 0,
        "Eau": 150,
        "Superplastifiant": 10,
        "GravilonsGros": 1000,
        "SableFin": 650,
        "Age": 28,
        "description": "Béton THP pour ouvrages d'art et précontrainte",
        "classe": "C50/60",
        "exposition": "XD3-XS1"
    },
    
    "Béton Durable Maritime": {
        "Ciment": 250,
        "Laitier": 150,
        "CendresVolantes": 0,
        "Eau": 160,
        "Superplastifiant": 4,
        "GravilonsGros": 1070,
        "SableFin": 715,
        "Age": 28,
        "description": "Béton résistant eau de mer (laitier 60%)",
        "classe": "C40/50",
        "exposition": "XS2-XS3"
    },
    
    "Béton Écologique": {
        "Ciment": 200,
        "Laitier": 0,
        "CendresVolantes": 120,
        "Eau": 175,
        "Superplastifiant": 3,
        "GravilonsGros": 1120,
        "SableFin": 760,
        "Age": 28,
        "description": "Faible empreinte carbone (cendres volantes 60%)",
        "classe": "C25/30",
        "exposition": "XC1"
    },
    
    "Béton Autoplaçant BAP": {
        "Ciment": 400,
        "Laitier": 100,
        "CendresVolantes": 0,
        "Eau": 180,
        "Superplastifiant": 12,
        "GravilonsGros": 850,
        "SableFin": 850,
        "Age": 28,
        "description": "Béton autoplaçant pour coffrages complexes",
        "classe": "C35/45",
        "exposition": "XC3"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# SEUILS QUALITÉ POUR INDICATEURS
# ═══════════════════════════════════════════════════════════════════════════════

QUALITY_THRESHOLDS = {
    "Diffusion_Cl": {
        "excellent": 5.0,    # < 5 ×10⁻¹² m²/s
        "bon": 8.0,          # 5-8
        "moyen": 12.0,       # 8-12
        "faible": float("inf")  # > 12
    },
    
    "Carbonatation": {
        "excellent": 8.0,    # < 8 mm
        "bon": 15.0,         # 8-15
        "moyen": 25.0,       # 15-25
        "faible": float("inf")  # > 25
    },
    
    "Ratio_E_L": {
        "excellent": 0.40,   # < 0.40
        "bon": 0.50,         # 0.40-0.50
        "acceptable": 0.60,  # 0.50-0.60
        "faible": float("inf")  # > 0.60
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# COULEURS THÉMATIQUES (CHARTE IMT NORD EUROPE)
# ═══════════════════════════════════════════════════════════════════════════════

COLOR_PALETTE = {
    "primary": "#1e3c72",      # Bleu IMT foncé
    "secondary": "#2a5298",    # Bleu IMT clair
    "accent": "#3d5a99",       # Bleu accent
    "success": "#28a745",      # Vert
    "warning": "#ffc107",      # Orange/Jaune
    "danger": "#dc3545",       # Rouge
    "info": "#17a2b8",         # Cyan
    "light": "#f8f9fa",        # Gris clair
    "dark": "#343a40",         # Gris foncé
    "white": "#ffffff",
    "black": "#000000"
}


# ═══════════════════════════════════════════════════════════════════════════════
# ÉMOJIS STATUT (POUR UX)
# ═══════════════════════════════════════════════════════════════════════════════

STATUS_EMOJI = {
    "excellent": "🟢",
    "bon": "🟡",
    "moyen": "🟠",
    "faible": "🔴",
    "ok": "✅",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️"
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "BOUNDS",
    "LABELS_MAP",
    "RESISTANCE_CLASSES",
    "EXPOSURE_CLASSES",
    "PRESET_FORMULATIONS",
    "QUALITY_THRESHOLDS",
    "COLOR_PALETTE",
    "STATUS_EMOJI",
    "MATERIALS_COST_EURO_KG",
    "CO2_EMISSIONS_KG"
]