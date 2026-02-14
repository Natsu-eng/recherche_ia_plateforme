"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/validator.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Validation Physique & Conformité Normes Européennes (Eurocodes)
Version: 2.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

Ce module valide les formulations béton selon :
  - EN 206 (Spécification, performance, production)
  - EN 197-1 (Ciments)
  - Loi d'Abrams (relation E/C - Résistance)
  - Classes d'exposition (XC, XD, XS, XF)
  - Limites physiques et chimiques

Utilisé pour :
  - Alerter l'utilisateur sur formulations hors norme
  - Recommandations automatiques
  - Aide à la décision ingénieur
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

from config.constants import (
    BOUNDS,
    EXPOSURE_CLASSES,
    QUALITY_THRESHOLDS,
    STATUS_EMOJI
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ÉNUMÉRATIONS & CLASSES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(Enum):
    """Niveau de gravité des alertes"""
    INFO = "info"           # Information
    WARNING = "warning"     # Attention recommandée
    ERROR = "error"         # Non-conformité grave
    CRITICAL = "critical"   # Formulation dangereuse/inutilisable


@dataclass
class ValidationAlert:
    """
    Alerte de validation.
    
    Attributs:
        severity: Niveau gravité (INFO, WARNING, ERROR, CRITICAL)
        category: Catégorie (E/L, Durabilité, Norme, etc.)
        message: Message descriptif
        recommendation: Recommandation corrective
        norm_ref: Référence normative (optionnel)
    """
    severity: Severity
    category: str
    message: str
    recommendation: str
    norm_ref: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Export dictionnaire"""
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "recommendation": self.recommendation,
            "norm_ref": self.norm_ref,
            "emoji": STATUS_EMOJI.get(self.severity.value, "ℹ️")
        }


@dataclass
class ValidationReport:
    """
    Rapport de validation complet.
    
    Attributs:
        is_valid: Formulation valide globalement
        alerts: Liste des alertes
        exposure_class: Classe exposition recommandée
        resistance_class: Classe résistance estimée
        compliance_score: Score conformité (0-100)
    """
    is_valid: bool
    alerts: List[ValidationAlert]
    exposure_class: Optional[str]
    resistance_class: Optional[str]
    compliance_score: float
    
    def get_critical_alerts(self) -> List[ValidationAlert]:
        """Retourne alertes critiques seulement"""
        return [a for a in self.alerts if a.severity == Severity.CRITICAL]
    
    def get_warnings(self) -> List[ValidationAlert]:
        """Retourne warnings seulement"""
        return [a for a in self.alerts if a.severity == Severity.WARNING]


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATEURS PHYSIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def validate_water_binder_ratio(
    ratio_el: float,
    resistance: float
) -> List[ValidationAlert]:
    """
    Valide le rapport E/L selon EN 206 et Loi d'Abrams.
    
    Loi d'Abrams : fc = A / (E/C)^B
    Plus E/L élevé → Résistance baisse, porosité augmente
    
    Args:
        ratio_el: Rapport Eau/Liant
        resistance: Résistance prédite (MPa)
        
    Returns:
        Liste d'alertes
    """
    alerts = []
    
    # Seuils EN 206 (béton armé)
    if ratio_el > 0.65:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} > 0.65 (limite EN 206 béton armé)",
            recommendation=(
                "Réduire eau ou augmenter liant. "
                "Risque : porosité élevée, résistance faible, durabilité compromise."
            ),
            norm_ref="EN 206 - Tableau 4"
        ))
    
    elif ratio_el > 0.60:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} élevé (0.60-0.65)",
            recommendation=(
                "Acceptable pour environnements peu agressifs (XC1-XC2). "
                "Pour XD/XS, réduire à < 0.55."
            ),
            norm_ref="EN 206"
        ))
    
    elif ratio_el < 0.30:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} très faible",
            recommendation=(
                "Risque de maniabilité insuffisante. "
                "Vérifier dosage superplastifiant (≥ 1% du liant recommandé)."
            ),
            norm_ref="NF EN 934-2"
        ))
    
    elif ratio_el <= 0.40:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} - Excellent (béton haute performance)",
            recommendation=(
                "Optimal pour durabilité. Résistance élevée attendue. "
                "Prévoir cure soignée (7-14 jours)."
            ),
            norm_ref="EN 206"
        ))
    
    # Cohérence avec résistance prédite (Loi d'Abrams)
    # Approximation : fc ≈ 100 / (E/L)^2 pour E/L > 0.4
    if ratio_el > 0.50 and resistance > 45:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Cohérence E/L - Résistance",
            message=(
                f"Incohérence : E/L={ratio_el:.3f} mais Résistance={resistance:.1f} MPa. "
                "Loi d'Abrams : E/L élevé → Résistance faible attendue."
            ),
            recommendation=(
                "Vérifier composition. Possible forte teneur en ciment compensant l'E/L. "
                "Optimisation possible en réduisant eau."
            ),
            norm_ref="Loi d'Abrams"
        ))
    
    return alerts


def validate_substitution_rate(
    ciment: float,
    laitier: float,
    cendres: float
) -> List[ValidationAlert]:
    """
    Valide les taux de substitution du clinker (ajouts cimentaires).
    
    Args:
        ciment: Dosage ciment (kg/m³)
        laitier: Dosage laitier (kg/m³)
        cendres: Dosage cendres volantes (kg/m³)
        
    Returns:
        Liste d'alertes
    """
    alerts = []
    
    liant_total = ciment + laitier + cendres
    
    if liant_total < 1:
        return alerts  # Éviter division par zéro
    
    taux_laitier = (laitier / liant_total) * 100
    taux_cendres = (cendres / liant_total) * 100
    taux_total_sub = taux_laitier + taux_cendres
    
    # Validation laitier (EN 197-1 CEM III : ≤ 95%)
    if taux_laitier > 70:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Taux Laitier",
            message=f"Taux laitier = {taux_laitier:.1f}% > 70% (limite recommandée)",
            recommendation=(
                "Risque de prise lente et résistance jeune âge faible. "
                "Réduire laitier ou augmenter ciment CEM I."
            ),
            norm_ref="EN 197-1 (CEM III/C : 81-95%)"
        ))
    
    elif taux_laitier > 50:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Taux Laitier",
            message=f"Taux laitier élevé ({taux_laitier:.1f}%) - Béton écoperformant",
            recommendation=(
                "Excellente durabilité (résistance sulfates, chlorures). "
                "Prévoir cure prolongée (14 jours min)."
            ),
            norm_ref="EN 197-1 CEM III/B"
        ))
    
    # Validation cendres volantes (EN 450-1 : ≤ 55%)
    if taux_cendres > 55:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Taux Cendres Volantes",
            message=f"Taux cendres = {taux_cendres:.1f}% > 55% (limite NF EN 450-1)",
            recommendation=(
                "Dépassement norme. Risque : prise très lente, résistance initiale insuffisante. "
                "Réduire cendres à ≤ 55%."
            ),
            norm_ref="NF EN 450-1"
        ))
    
    elif taux_cendres > 35:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Taux Cendres Volantes",
            message=f"Taux cendres important ({taux_cendres:.1f}%) - Béton éco-responsable",
            recommendation=(
                "Réduction significative empreinte carbone. "
                "Cure humide prolongée recommandée."
            ),
            norm_ref="NF EN 450-1"
        ))
    
    # Substitution totale
    if taux_total_sub > 70:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Substitution Totale",
            message=f"Substitution totale = {taux_total_sub:.1f}% (clinker < 30%)",
            recommendation=(
                "Formulation très bas carbone mais cinétique lente. "
                "Vérifier résistance 7j et 28j expérimentalement."
            ),
            norm_ref="Guide AFGC Bétons Bas Carbone"
        ))
    
    return alerts


def validate_durability(
    diffusion_cl: float,
    carbonatation: float,
    ratio_el: float
) -> List[ValidationAlert]:
    """
    Valide les indicateurs de durabilité.
    
    Args:
        diffusion_cl: Coefficient diffusion chlorures (×10⁻¹² m²/s)
        carbonatation: Profondeur carbonatation (mm)
        ratio_el: Rapport E/L
        
    Returns:
        Liste d'alertes
    """
    alerts = []
    
    # ─── DIFFUSION CHLORURES ───
    thresholds_cl = QUALITY_THRESHOLDS["Diffusion_Cl"]
    
    if diffusion_cl < thresholds_cl["excellent"]:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Durabilité Chlorures",
            message=f"Diffusion Cl⁻ = {diffusion_cl:.2f} - Excellente (< 5)",
            recommendation=(
                "Résistance corrosion optimale. Adapté XS3 (zone marnage maritime). "
                "Enrobage minimal : 45 mm (EN 1992-1-1)."
            ),
            norm_ref="EN 206 - Classe XS"
        ))
    
    elif diffusion_cl > thresholds_cl["moyen"]:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Durabilité Chlorures",
            message=f"Diffusion Cl⁻ = {diffusion_cl:.2f} élevée (> 12)",
            recommendation=(
                "Risque corrosion armatures en milieu salin. "
                "Réduire E/L, augmenter laitier, ou ajouter fumée de silice."
            ),
            norm_ref="EN 206 - XD3/XS2"
        ))
    
    # ─── CARBONATATION ───
    thresholds_carb = QUALITY_THRESHOLDS["Carbonatation"]
    
    if carbonatation < thresholds_carb["excellent"]:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Durabilité Carbonatation",
            message=f"Carbonatation = {carbonatation:.1f} mm - Excellente (< 8)",
            recommendation=(
                "Protection alcaline optimale. Adapté XC4 (cycles humide/sec). "
                "Enrobage : 25-30 mm suffisant."
            ),
            norm_ref="EN 206 - Classe XC"
        ))
    
    elif carbonatation > thresholds_carb["moyen"]:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Durabilité Carbonatation",
            message=f"Carbonatation = {carbonatation:.1f} mm importante (> 25)",
            recommendation=(
                "Vitesse carbonatation élevée. Risque dépassivation armatures. "
                "Augmenter enrobage (≥ 35 mm) ou réduire E/L."
            ),
            norm_ref="EN 206 - XC3/XC4"
        ))
    
    # ─── COHÉRENCE E/L - DURABILITÉ ───
    if ratio_el > 0.55 and (diffusion_cl > 10 or carbonatation > 20):
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Cohérence E/L - Durabilité",
            message=(
                f"E/L élevé ({ratio_el:.3f}) + durabilité limitée. "
                "Formulation cohérente mais perfectible."
            ),
            recommendation=(
                "Pour améliorer durabilité : réduire E/L à ≤ 0.50 "
                "ou ajouter 10-15% laitier/fumée silice."
            ),
            norm_ref="EN 206"
        ))
    
    return alerts


def validate_cement_content(ciment: float, liant_total: float) -> List[ValidationAlert]:
    """
    Valide le dosage en ciment selon EN 206.
    
    Args:
        ciment: Dosage ciment (kg/m³)
        liant_total: Liant total (kg/m³)
        
    Returns:
        Liste d'alertes
    """
    alerts = []
    
    # EN 206 : ciment min = 260-280 kg/m³ (béton armé)
    if liant_total < 260:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Dosage Liant",
            message=f"Liant total = {liant_total:.0f} kg/m³ < 260 kg/m³ (minimum EN 206)",
            recommendation=(
                "Dosage insuffisant pour béton armé. Augmenter liant à ≥ 280 kg/m³."
            ),
            norm_ref="EN 206 - Tableau 4"
        ))
    
    elif ciment < 150 and liant_total < 300:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Dosage Ciment",
            message=f"Ciment = {ciment:.0f} kg/m³ faible avec liant total = {liant_total:.0f} kg/m³",
            recommendation=(
                "Fort taux substitution. Vérifier résistance initiale (7j) expérimentalement."
            ),
            norm_ref="EN 206"
        ))
    
    # Dosage très élevé (béton HP/THR)
    if liant_total > 500:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Dosage Liant",
            message=f"Liant total = {liant_total:.0f} kg/m³ élevé (béton HP)",
            recommendation=(
                "Béton haute/très haute performance. "
                "Attention chaleur d'hydratation : prévoir cure adaptée et limitation gradients thermiques."
            ),
            norm_ref="Guide AFGC Bétons UHPC"
        ))
    
    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION COMPLÈTE
# ═══════════════════════════════════════════════════════════════════════════════

def validate_formulation(
    composition: Dict[str, float],
    predictions: Dict[str, float]
) -> ValidationReport:
    """
    Validation complète d'une formulation béton.
    
    Effectue toutes les vérifications :
      - Ratio E/L (EN 206, Loi d'Abrams)
      - Taux substitution (EN 197-1, EN 450-1)
      - Durabilité (diffusion chlorures, carbonatation)
      - Dosage ciment (EN 206)
      - Cohérence globale
    
    Args:
        composition: Composition béton (kg/m³)
        predictions: Résultats prédiction ML
        
    Returns:
        ValidationReport complet avec alertes et recommandations
    """
    alerts: List[ValidationAlert] = []
    
    # Extraire données
    ratio_el = predictions["Ratio_E_L"]
    liant_total = predictions["Liant_Total"]
    resistance = predictions["Resistance"]
    diffusion_cl = predictions["Diffusion_Cl"]
    carbonatation = predictions["Carbonatation"]
    
    ciment = composition["Ciment"]
    laitier = composition["Laitier"]
    cendres = composition["CendresVolantes"]
    
    # ─── VALIDATIONS MODULAIRES ───
    alerts.extend(validate_water_binder_ratio(ratio_el, resistance))
    alerts.extend(validate_substitution_rate(ciment, laitier, cendres))
    alerts.extend(validate_durability(diffusion_cl, carbonatation, ratio_el))
    alerts.extend(validate_cement_content(ciment, liant_total))
    
    # ─── DÉTERMINATION CLASSE EXPOSITION ───
    exposure_class = determine_exposure_class(ratio_el, resistance)
    
    # ─── DÉTERMINATION CLASSE RÉSISTANCE ───
    resistance_class = determine_resistance_class(resistance)
    
    # ─── CALCUL SCORE CONFORMITÉ ───
    compliance_score = calculate_compliance_score(alerts)
    
    # ─── VALIDITÉ GLOBALE ───
    is_valid = not any(a.severity == Severity.CRITICAL for a in alerts)
    
    logger.info(
        f"Validation terminée : {len(alerts)} alertes, "
        f"Score={compliance_score:.0f}/100, Valide={is_valid}"
    )
    
    return ValidationReport(
        is_valid=is_valid,
        alerts=alerts,
        exposure_class=exposure_class,
        resistance_class=resistance_class,
        compliance_score=compliance_score
    )


def determine_exposure_class(ratio_el: float, resistance: float) -> str:
    """Détermine classe exposition recommandée selon EN 206"""
    
    # Parcourir classes exposition par ordre de sévérité décroissante
    for class_name, specs in sorted(
        EXPOSURE_CLASSES.items(), 
        key=lambda x: x[1]["E_L_max"]
    ):
        if ratio_el <= specs["E_L_max"] and resistance >= specs["fc_min"]:
            return class_name
    
    return "XC1"  # Par défaut (moins agressif)


def determine_resistance_class(resistance: float) -> str:
    """Détermine classe résistance selon EN 206"""
    from config.constants import RESISTANCE_CLASSES
    
    # Approximation cylindre (fc,cyl ≈ 0.83 × fc,cube)
    for class_name, specs in sorted(
        RESISTANCE_CLASSES.items(),
        key=lambda x: x[1]["fc_cyl"],
        reverse=True
    ):
        if resistance >= specs["fc_cyl"]:
            return class_name
    
    return "C12/15"  # Minimum


def calculate_compliance_score(alerts: List[ValidationAlert]) -> float:
    """
    Calcule un score de conformité (0-100).
    
    Pénalités :
      - CRITICAL : -30 points
      - ERROR : -20 points
      - WARNING : -10 points
      - INFO : +5 points (bonus)
    """
    score = 100.0
    
    for alert in alerts:
        if alert.severity == Severity.CRITICAL:
            score -= 30
        elif alert.severity == Severity.ERROR:
            score -= 20
        elif alert.severity == Severity.WARNING:
            score -= 10
        elif alert.severity == Severity.INFO:
            score += 5
    
    return max(0.0, min(100.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "validate_formulation",
    "ValidationReport",
    "ValidationAlert",
    "Severity",
    "determine_exposure_class",
    "determine_resistance_class"
]