"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/validator.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Validation Physique & Conformité Normes Européennes (Eurocodes)
Version: 1.0.0 - Refactorisé & Production Ready
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
  - Traçabilité contractuelle (classe exigée vs atteinte)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

from config.constants import (
    BOUNDS,
    EXPOSURE_CLASSES,
    QUALITY_THRESHOLDS,
    STATUS_EMOJI,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES INTERNES
# ═══════════════════════════════════════════════════════════════════════════════

# Ordre de sévérité croissante des classes EN 206 (du moins au plus exigeant)
# Utilisé pour comparer classe exigée vs atteinte
_EXPOSURE_CLASS_ORDER: List[str] = [
    "XC1", "XC2", "XC3", "XC4",
    "XD1", "XD2", "XD3",
    "XS1", "XS2", "XS3",
    "XF1", "XF2", "XF3", "XF4",
]

# Pénalités de conformité par sévérité (pas de bonus INFO → chiffre fiable)
_COMPLIANCE_PENALTIES: Dict[str, float] = {
    "critical": 40.0,
    "error":    20.0,
    "warning":   8.0,
    "info":      0.0,   # neutre — ne pas gonfler artificiellement le score
}


# ═══════════════════════════════════════════════════════════════════════════════
# ÉNUMÉRATIONS & CLASSES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(Enum):
    """Niveau de gravité des alertes de validation."""
    INFO     = "info"      # Information — pas d'action requise
    WARNING  = "warning"   # Attention recommandée
    ERROR    = "error"     # Non-conformité grave
    CRITICAL = "critical"  # Formulation dangereuse / inutilisable


@dataclass
class ValidationAlert:
    """
    Alerte unitaire de validation.

    Attributs:
        severity      : Niveau de gravité (INFO, WARNING, ERROR, CRITICAL)
        category      : Catégorie fonctionnelle (ex: "Ratio E/L", "Durabilité")
        message       : Description du problème détecté
        recommendation: Action corrective proposée
        norm_ref      : Référence normative (optionnel, ex: "EN 206 - Tableau 4")
    """

    severity:       Severity
    category:       str
    message:        str
    recommendation: str
    norm_ref:       Optional[str] = None

    def to_dict(self) -> Dict:
        """Export en dictionnaire (sérialisation JSON / affichage UI)."""
        return {
            "severity":       self.severity.value,
            "category":       self.category,
            "message":        self.message,
            "recommendation": self.recommendation,
            "norm_ref":       self.norm_ref,
            "emoji":          STATUS_EMOJI.get(self.severity.value, "ℹ️"),
        }


@dataclass
class ValidationReport:
    """
    Rapport de validation complet d'une formulation béton.

    DISTINCTION CONTRACTUELLE (v1.0.0) :
      - required_class           : classe d'exposition exigée par l'ingénieur / le marché
      - achieved_class           : classe réellement atteinte par la formulation
      - compliance_with_required : True si la formulation satisfait la classe exigée

    Attributs:
        is_valid                : Aucune alerte CRITICAL (formulation physiquement viable)
        alerts                  : Liste complète des alertes
        required_class          : Classe EN 206 demandée (ex: "XD2")
        achieved_class          : Classe EN 206 calculée (ex: "XS3")
        compliance_with_required: Conformité vis-à-vis de required_class
        resistance_class        : Classe résistance estimée (ex: "C35/45")
        compliance_score        : Score conformité fiable 0→100 (sans bonus INFO)
    """

    is_valid:                bool
    alerts:                  List[ValidationAlert]
    required_class:          Optional[str]   # ← NOUVEAU : classe exigée
    achieved_class:          Optional[str]   # ← NOUVEAU : classe calculée
    compliance_with_required: bool           # ← NOUVEAU : verdict contractuel
    resistance_class:        Optional[str]
    compliance_score:        float

    # ── Accesseurs filtrés ──────────────────────────────────────────────────

    def get_critical_alerts(self) -> List[ValidationAlert]:
        """Retourne uniquement les alertes CRITICAL."""
        return [a for a in self.alerts if a.severity == Severity.CRITICAL]

    def get_errors(self) -> List[ValidationAlert]:
        """Retourne uniquement les alertes ERROR."""
        return [a for a in self.alerts if a.severity == Severity.ERROR]

    def get_warnings(self) -> List[ValidationAlert]:
        """Retourne uniquement les alertes WARNING."""
        return [a for a in self.alerts if a.severity == Severity.WARNING]

    def get_infos(self) -> List[ValidationAlert]:
        """Retourne uniquement les alertes INFO."""
        return [a for a in self.alerts if a.severity == Severity.INFO]

    @property
    def verdict_label(self) -> str:
        """
        Label de verdict lisible pour l'UI.

        Returns:
            "CONFORME", "NON CONFORME" ou "INVALIDE"
        """
        if not self.is_valid:
            return "INVALIDE"
        return "CONFORME" if self.compliance_with_required else "NON CONFORME"


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATEURS PHYSIQUES MODULAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def validate_water_binder_ratio(
    ratio_el: float,
    resistance: float,
) -> List[ValidationAlert]:
    """
    Valide le rapport Eau/Liant selon EN 206 et la Loi d'Abrams.

    Règles appliquées:
      - E/L > 0.65 → ERROR  (limite béton armé EN 206)
      - E/L > 0.60 → WARNING (zone de vigilance)
      - E/L < 0.30 → WARNING (risque maniabilité)
      - E/L ≤ 0.40 → INFO   (excellent, BHP)
      - E/L > 0.50 + résistance > 45 MPa → WARNING (incohérence Abrams)

    Args:
        ratio_el  : Rapport Eau/Liant (sans unité)
        resistance: Résistance à la compression prédite (MPa)

    Returns:
        Liste d'objets ValidationAlert
    """
    alerts: List[ValidationAlert] = []

    # ── Seuils EN 206 absolus ───────────────────────────────────────────────
    if ratio_el > 0.65:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} > 0.65 (limite EN 206 béton armé)",
            recommendation=(
                "Réduire eau ou augmenter liant. "
                "Risque : porosité élevée, résistance faible, durabilité compromise."
            ),
            norm_ref="EN 206 - Tableau 4",
        ))

    elif ratio_el > 0.60:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} élevé (0.60–0.65)",
            recommendation=(
                "Acceptable pour environnements peu agressifs (XC1–XC2). "
                "Pour XD/XS, réduire à ≤ 0.55."
            ),
            norm_ref="EN 206",
        ))

    elif ratio_el < 0.30:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} très faible",
            recommendation=(
                "Risque de maniabilité insuffisante. "
                "Vérifier dosage superplastifiant (≥ 1 % du liant recommandé)."
            ),
            norm_ref="NF EN 934-2",
        ))

    elif ratio_el <= 0.40:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Ratio E/L",
            message=f"Ratio E/L = {ratio_el:.3f} — Excellent (béton haute performance)",
            recommendation=(
                "Optimal pour durabilité. Résistance élevée attendue. "
                "Prévoir cure soignée (7–14 jours)."
            ),
            norm_ref="EN 206",
        ))

    # ── Cohérence E/L vs Résistance (Loi d'Abrams) ─────────────────────────
    # fc ≈ A / (E/L)^B → E/L élevé incompatible avec résistance élevée
    if ratio_el > 0.50 and resistance > 45:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Cohérence E/L – Résistance",
            message=(
                f"Incohérence : E/L = {ratio_el:.3f} mais Résistance = {resistance:.1f} MPa. "
                "La Loi d'Abrams prédit une résistance plus faible pour ce rapport E/L."
            ),
            recommendation=(
                "Vérifier la composition. Une forte teneur en ciment peut compenser partiellement. "
                "Optimisation possible en réduisant l'eau de gâchage."
            ),
            norm_ref="Loi d'Abrams",
        ))

    return alerts


def validate_substitution_rate(
    ciment: float,
    laitier: float,
    cendres: float,
) -> List[ValidationAlert]:
    """
    Valide les taux de substitution du clinker par des ajouts cimentaires.

    Règles appliquées:
      - Laitier > 70 %  → ERROR  (prise très lente)
      - Laitier > 50 %  → INFO   (béton éco-performant)
      - Cendres > 55 %  → ERROR  (dépassement NF EN 450-1)
      - Cendres > 35 %  → INFO   (béton éco-responsable)
      - Substitution totale > 70 % → WARNING (cinétique lente)

    Args:
        ciment : Dosage ciment Portland (kg/m³)
        laitier: Dosage laitier de haut fourneau (kg/m³)
        cendres: Dosage cendres volantes (kg/m³)

    Returns:
        Liste d'objets ValidationAlert
    """
    alerts: List[ValidationAlert] = []

    liant_total = ciment + laitier + cendres
    if liant_total < 1.0:
        # Éviter la division par zéro sur compositions vides
        return alerts

    taux_laitier = (laitier / liant_total) * 100.0
    taux_cendres = (cendres / liant_total) * 100.0
    taux_total   = taux_laitier + taux_cendres

    # ── Laitier (EN 197-1) ──────────────────────────────────────────────────
    if taux_laitier > 70.0:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Taux Laitier",
            message=f"Taux laitier = {taux_laitier:.1f} % > 70 % (limite recommandée)",
            recommendation=(
                "Risque de prise lente et résistance jeune âge faible. "
                "Réduire laitier ou augmenter ciment CEM I."
            ),
            norm_ref="EN 197-1 (CEM III/C : 81–95 %)",
        ))
    elif taux_laitier > 50.0:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Taux Laitier",
            message=f"Taux laitier élevé ({taux_laitier:.1f} %) — Béton éco-performant",
            recommendation=(
                "Excellente durabilité (résistance sulfates, chlorures). "
                "Prévoir cure prolongée (14 jours minimum)."
            ),
            norm_ref="EN 197-1 CEM III/B",
        ))

    # ── Cendres volantes (NF EN 450-1) ─────────────────────────────────────
    if taux_cendres > 55.0:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Taux Cendres Volantes",
            message=f"Taux cendres = {taux_cendres:.1f} % > 55 % (limite NF EN 450-1)",
            recommendation=(
                "Dépassement de norme. Risque : prise très lente, résistance initiale insuffisante. "
                "Réduire cendres à ≤ 55 %."
            ),
            norm_ref="NF EN 450-1",
        ))
    elif taux_cendres > 35.0:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Taux Cendres Volantes",
            message=f"Taux cendres important ({taux_cendres:.1f} %) — Béton éco-responsable",
            recommendation=(
                "Réduction significative de l'empreinte carbone. "
                "Cure humide prolongée recommandée."
            ),
            norm_ref="NF EN 450-1",
        ))

    # ── Substitution totale ─────────────────────────────────────────────────
    if taux_total > 70.0:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Substitution Totale",
            message=f"Substitution totale = {taux_total:.1f} % (clinker < 30 %)",
            recommendation=(
                "Formulation très bas carbone mais cinétique lente. "
                "Vérifier résistances à 7 j et 28 j expérimentalement."
            ),
            norm_ref="Guide AFGC Bétons Bas Carbone",
        ))

    return alerts


def validate_durability(
    diffusion_cl:  float,
    carbonatation: float,
    ratio_el:      float,
) -> List[ValidationAlert]:
    """
    Valide les indicateurs de durabilité selon EN 206 / EN 1992.

    Critères vérifiés:
      - Diffusion chlorures (×10⁻¹² m²/s) : excellent < 5, moyen > 12
      - Carbonatation (mm)                 : excellente < 8, importante > 25
      - Cohérence E/L élevé + durabilité limitée

    Args:
        diffusion_cl : Coefficient de diffusion chlorures (×10⁻¹² m²/s)
        carbonatation: Profondeur de carbonatation (mm)
        ratio_el     : Rapport Eau/Liant

    Returns:
        Liste d'objets ValidationAlert
    """
    alerts: List[ValidationAlert] = []

    thresholds_cl   = QUALITY_THRESHOLDS["Diffusion_Cl"]
    thresholds_carb = QUALITY_THRESHOLDS["Carbonatation"]

    # ── Diffusion chlorures ─────────────────────────────────────────────────
    if diffusion_cl < thresholds_cl["excellent"]:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Durabilité Chlorures",
            message=f"Diffusion Cl⁻ = {diffusion_cl:.2f} — Excellente (< {thresholds_cl['excellent']})",
            recommendation=(
                "Résistance à la corrosion optimale. Adapté XS3 (zone de marnage maritime). "
                "Enrobage minimal recommandé : 45 mm (EN 1992-1-1)."
            ),
            norm_ref="EN 206 — Classe XS",
        ))
    elif diffusion_cl > thresholds_cl["moyen"]:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Durabilité Chlorures",
            message=f"Diffusion Cl⁻ = {diffusion_cl:.2f} élevée (> {thresholds_cl['moyen']})",
            recommendation=(
                "Risque de corrosion des armatures en milieu salin. "
                "Réduire E/L, augmenter la teneur en laitier ou ajouter de la fumée de silice."
            ),
            norm_ref="EN 206 — XD3/XS2",
        ))

    # ── Carbonatation ───────────────────────────────────────────────────────
    if carbonatation < thresholds_carb["excellent"]:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Durabilité Carbonatation",
            message=f"Carbonatation = {carbonatation:.1f} mm — Excellente (< {thresholds_carb['excellent']})",
            recommendation=(
                "Protection alcaline optimale. Adapté XC4 (cycles humide/sec). "
                "Enrobage 25–30 mm suffisant."
            ),
            norm_ref="EN 206 — Classe XC",
        ))
    elif carbonatation > thresholds_carb["moyen"]:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Durabilité Carbonatation",
            message=f"Carbonatation = {carbonatation:.1f} mm importante (> {thresholds_carb['moyen']})",
            recommendation=(
                "Vitesse de carbonatation élevée. Risque de dépassivation des armatures. "
                "Augmenter l'enrobage (≥ 35 mm) ou réduire E/L."
            ),
            norm_ref="EN 206 — XC3/XC4",
        ))

    # ── Cohérence E/L élevé + durabilité limitée ───────────────────────────
    if ratio_el > 0.55 and (diffusion_cl > 10.0 or carbonatation > 20.0):
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Cohérence E/L – Durabilité",
            message=(
                f"E/L élevé ({ratio_el:.3f}) combiné à une durabilité limitée. "
                "Formulation cohérente mais perfectible."
            ),
            recommendation=(
                "Pour améliorer la durabilité : réduire E/L à ≤ 0.50 "
                "ou ajouter 10–15 % de laitier / fumée de silice."
            ),
            norm_ref="EN 206",
        ))

    return alerts


def validate_cement_content(
    ciment:      float,
    liant_total: float,
) -> List[ValidationAlert]:
    """
    Valide le dosage en ciment et en liant total selon EN 206.

    Règles appliquées:
      - Liant total < 260 kg/m³ → ERROR  (minimum EN 206 béton armé)
      - Ciment < 150 + liant < 300 → WARNING (fort taux substitution)
      - Liant > 500 kg/m³ → INFO  (béton haute performance)

    Args:
        ciment      : Dosage ciment Portland (kg/m³)
        liant_total : Liant total (ciment + laitier + cendres, kg/m³)

    Returns:
        Liste d'objets ValidationAlert
    """
    alerts: List[ValidationAlert] = []

    # ── Minimum EN 206 ──────────────────────────────────────────────────────
    if liant_total < 260.0:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Dosage Liant",
            message=f"Liant total = {liant_total:.0f} kg/m³ < 260 kg/m³ (minimum EN 206 béton armé)",
            recommendation="Augmenter le dosage en liant à ≥ 280 kg/m³.",
            norm_ref="EN 206 — Tableau 4",
        ))

    elif ciment < 150.0 and liant_total < 300.0:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Dosage Ciment",
            message=(
                f"Ciment = {ciment:.0f} kg/m³ faible "
                f"avec liant total = {liant_total:.0f} kg/m³"
            ),
            recommendation=(
                "Fort taux de substitution. "
                "Vérifier la résistance initiale à 7 j expérimentalement."
            ),
            norm_ref="EN 206",
        ))

    # ── Béton haute performance ─────────────────────────────────────────────
    if liant_total > 500.0:
        alerts.append(ValidationAlert(
            severity=Severity.INFO,
            category="Dosage Liant",
            message=f"Liant total = {liant_total:.0f} kg/m³ — Béton haute performance",
            recommendation=(
                "Attention à la chaleur d'hydratation : prévoir une cure adaptée "
                "et limiter les gradients thermiques."
            ),
            norm_ref="Guide AFGC Bétons UHPC",
        ))

    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION NORMATIVE STRICTE PAR CLASSE D'EXPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_en206_exposure_strict(
    exposure_class: str,
    ratio_el:       float,
    resistance:     float,
    liant_total:    float,
) -> List[ValidationAlert]:
    """
    Validation normative stricte selon la classe d'exposition EN 206.

    Compare les paramètres réels aux exigences officielles de la classe.
    Vérifications effectuées :
      - Rapport E/L ≤ E/L_max de la classe
      - Résistance ≥ fc_min de la classe
      - Dosage liant suffisant pour milieux sévères (XD3, XS2, XS3)

    Args:
        exposure_class: Code de classe EN 206 (ex: "XD2", "XS3")
        ratio_el      : Rapport Eau/Liant mesuré/prédit
        resistance    : Résistance à la compression (MPa)
        liant_total   : Dosage liant total (kg/m³)

    Returns:
        Liste d'objets ValidationAlert
    """
    alerts: List[ValidationAlert] = []

    # Vérifier que la classe est connue du référentiel
    if exposure_class not in EXPOSURE_CLASSES:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="Classe Exposition",
            message=f"Classe d'exposition '{exposure_class}' inconnue du référentiel.",
            recommendation="Vérifier la table EXPOSURE_CLASSES dans config/constants.py.",
            norm_ref="EN 206",
        ))
        return alerts

    specs = EXPOSURE_CLASSES[exposure_class]

    # ── Vérification Ratio E/L ──────────────────────────────────────────────
    if ratio_el > specs["E_L_max"]:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="EN 206 — Ratio E/L",
            message=(
                f"E/L = {ratio_el:.3f} > {specs['E_L_max']} "
                f"(limite classe {exposure_class})"
            ),
            recommendation="Réduire l'eau de gâchage ou augmenter le dosage en liant.",
            norm_ref="EN 206 — Tableau 4",
        ))

    # ── Vérification Résistance minimale ───────────────────────────────────
    if resistance < specs["fc_min"]:
        alerts.append(ValidationAlert(
            severity=Severity.ERROR,
            category="EN 206 — Résistance minimale",
            message=(
                f"Résistance = {resistance:.1f} MPa < "
                f"{specs['fc_min']} MPa requis pour {exposure_class}"
            ),
            recommendation=(
                "Augmenter le dosage en liant ou réduire le rapport E/L "
                "pour atteindre la résistance minimale imposée."
            ),
            norm_ref="EN 206",
        ))

    # ── Liant minimum en milieux sévères ────────────────────────────────────
    _SEVERE_CLASSES = {"XD3", "XS2", "XS3"}
    if exposure_class in _SEVERE_CLASSES and liant_total < 360.0:
        alerts.append(ValidationAlert(
            severity=Severity.WARNING,
            category="Durabilité — Milieu sévère",
            message=(
                f"Liant total = {liant_total:.0f} kg/m³ insuffisant "
                f"pour la classe {exposure_class}"
            ),
            recommendation=(
                "Recommandé ≥ 360 kg/m³ en environnement agressif "
                "(zone de marnage, milieu chloruré sévère)."
            ),
            norm_ref="Guide AFGC",
        ))

    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def determine_exposure_class(
    ratio_el:      float,
    resistance:    float,
    diffusion_cl:  float,
    carbonatation: float,
) -> str:
    """
    Détermine la classe d'exposition atteinte selon EN 206.

    Hiérarchie d'évaluation :
      1. Maritime / chlorures (XS) — priorité haute
      2. Chlorures non-marins (XD)
      3. Carbonatation (XC)
      4. XC1 par défaut

    Args:
        ratio_el      : Rapport Eau/Liant
        resistance    : Résistance à la compression (MPa, non utilisé ici, réservé)
        diffusion_cl  : Diffusion chlorures (×10⁻¹² m²/s)
        carbonatation : Profondeur carbonatation (mm)

    Returns:
        Code de classe EN 206 (str)
    """
    # ── Maritime / chlorures marins ─────────────────────────────────────────
    if diffusion_cl <= 5.0 and ratio_el <= 0.45:
        return "XS3"
    if diffusion_cl <= 8.0 and ratio_el <= 0.50:
        return "XS2"
    if diffusion_cl <= 12.0:
        return "XD3"

    # ── Carbonatation ───────────────────────────────────────────────────────
    if carbonatation <= 8.0 and ratio_el <= 0.45:
        return "XC4"
    if carbonatation <= 15.0 and ratio_el <= 0.55:
        return "XC3"
    if carbonatation <= 25.0:
        return "XC2"

    # ── Par défaut (faible agressivité) ────────────────────────────────────
    return "XC1"


def determine_resistance_class(resistance: float) -> str:
    """
    Détermine la classe de résistance selon EN 206 / EN 1992.

    Utilise la résistance cylindrique (fc,cyl ≈ 0.83 × fc,cube).

    Args:
        resistance: Résistance prédite (MPa — interprétée comme fc,cyl approx.)

    Returns:
        Code de classe résistance (ex: "C35/45")
    """
    from config.constants import RESISTANCE_CLASSES

    for class_name, specs in sorted(
        RESISTANCE_CLASSES.items(),
        key=lambda x: x[1]["fc_cyl"],
        reverse=True,
    ):
        if resistance >= specs["fc_cyl"]:
            return class_name

    return "C12/15"  # Minimum normalisé EN 206


def calculate_compliance_score(alerts: List[ValidationAlert]) -> float:
    """
    Calcule un score de conformité fiable (0–100).

    Barème corrigé v1.0.0 (suppression bonus INFO trompeur) :
      - CRITICAL : −40 points
      - ERROR    : −20 points
      - WARNING  : − 8 points
      - INFO     :   0 point  (neutre — ne gonfle plus le score)

    Args:
        alerts: Liste complète des alertes de validation

    Returns:
        Score float clampé dans [0.0, 100.0]
    """
    score = 100.0

    for alert in alerts:
        penalty = _COMPLIANCE_PENALTIES.get(alert.severity.value, 0.0)
        score -= penalty

    return max(0.0, min(100.0, score))


def _compare_exposure_classes(class_a: str, class_b: str) -> int:
    """
    Compare deux classes d'exposition selon leur sévérité croissante.

    Args:
        class_a: Code de classe (ex: "XD2")
        class_b: Code de classe (ex: "XS3")

    Returns:
        -1 si class_a < class_b, 0 si égales, +1 si class_a > class_b
        Retourne 0 si l'une des classes est inconnue de l'ordre.
    """
    if class_a not in _EXPOSURE_CLASS_ORDER or class_b not in _EXPOSURE_CLASS_ORDER:
        return 0  # Impossible de comparer des classes hors référentiel

    idx_a = _EXPOSURE_CLASS_ORDER.index(class_a)
    idx_b = _EXPOSURE_CLASS_ORDER.index(class_b)

    return (idx_a > idx_b) - (idx_a < idx_b)


def _check_compliance_with_required(
    achieved_class: str,
    required_class: str,
) -> bool:
    """
    Détermine si la classe atteinte satisfait la classe exigée.

    Une classe atteinte satisfait la classe exigée si :
      - Elles sont identiques
      - La classe atteinte est de sévérité SUPÉRIEURE ou ÉGALE (surperformance)

    Args:
        achieved_class: Classe réellement atteinte par la formulation
        required_class: Classe exigée par le marché / l'ingénieur

    Returns:
        True si conforme ou surperformant
    """
    cmp = _compare_exposure_classes(achieved_class, required_class)
    # cmp >= 0 → atteinte ≥ exigée → conforme
    return cmp >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION COMPLÈTE (POINT D'ENTRÉE PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_formulation(
    composition:    Dict[str, float],
    predictions:    Dict[str, float],
    required_class: Optional[str] = None,
) -> ValidationReport:
    """
    Validation complète d'une formulation béton — point d'entrée principal.

    Pipeline de validation :
      1. Extraction des paramètres prédits
      2. Détermination de la classe d'exposition ATTEINTE (moteur industriel)
      3. Validation normative stricte vis-à-vis de la classe EXIGÉE (si fournie)
      4. Alertes issues des recommandations du moteur d'exposition
      5. Validations physiques modulaires (E/L, substitution, durabilité, ciment)
      6. Calcul score de conformité corrigé (sans bonus INFO)
      7. Construction du rapport avec distinction contractuelle

    Args:
        composition   : Composition béton (kg/m³), clés attendues :
                        Ciment, Laitier, CendresVolantes, Eau, ...
        predictions   : Résultats ML, clés attendues :
                        Ratio_E_L, Liant_Total, Resistance,
                        Diffusion_Cl, Carbonatation, Pct_Substitution
        required_class: Classe d'exposition exigée (EN 206) — optionnel.
                        Si None, seule la classe atteinte est analysée.

    Returns:
        ValidationReport complet avec :
          - required_class           : classe demandée (peut être None)
          - achieved_class           : classe calculée
          - compliance_with_required : verdict contractuel
          - compliance_score         : score fiable 0–100
          - alerts                   : toutes les alertes détaillées
    """
    alerts: List[ValidationAlert] = []

    # ── Extraction des paramètres ───────────────────────────────────────────
    ratio_el      = float(predictions["Ratio_E_L"])
    liant_total   = float(predictions["Liant_Total"])
    resistance    = float(predictions["Resistance"])
    diffusion_cl  = float(predictions["Diffusion_Cl"])
    carbonatation = float(predictions["Carbonatation"])

    ciment  = float(composition.get("Ciment", 0.0))
    laitier = float(composition.get("Laitier", 0.0))
    cendres = float(composition.get("CendresVolantes", 0.0))

    # ── Détermination de la classe ATTEINTE via moteur industriel ──────────
    from .normative_engines import IndustrialEN206Engine

    exposure_engine   = IndustrialEN206Engine()
    exposure_analysis = exposure_engine.analyze(
        composition=composition,
        predictions=predictions,
    )
    exposure_result = exposure_engine.determine(
        ratio_el=ratio_el,
        resistance=resistance,
        diffusion_cl=diffusion_cl,
        carbonatation=carbonatation,
    )
    achieved_class: str = exposure_result.governing_class

    # ── Validation normative : classe EXIGÉE vs ATTEINTE ───────────────────
    if required_class:
        # 1) Vérifier la conformité stricte vis-à-vis de la classe exigée
        alerts.extend(validate_en206_exposure_strict(
            exposure_class=required_class,
            ratio_el=ratio_el,
            resistance=resistance,
            liant_total=liant_total,
        ))

        # 2) Alerte de surperformance si la classe atteinte > exigée
        if achieved_class != required_class:
            cmp = _compare_exposure_classes(achieved_class, required_class)
            if cmp > 0:
                # Surperformance : potentielle optimisation coût / CO₂
                alerts.append(ValidationAlert(
                    severity=Severity.INFO,
                    category="Performance Exposition",
                    message=(
                        f"Surperformance : Classe atteinte {achieved_class} "
                        f"> Classe exigée {required_class}."
                    ),
                    recommendation=(
                        "La formulation dépasse les exigences. "
                        "Opportunité d'optimisation du coût ou de la teneur en CO₂ "
                        "sans compromettre la conformité."
                    ),
                    norm_ref="EN 206",
                ))
            # Pas d'alerte pour sous-performance : déjà couverte par
            # validate_en206_exposure_strict (ERROR sur E/L ou fc_min)

    else:
        # Sans classe exigée : validation par rapport à la classe calculée
        alerts.extend(validate_en206_exposure_strict(
            exposure_class=achieved_class,
            ratio_el=ratio_el,
            resistance=resistance,
            liant_total=liant_total,
        ))

    # ── Alertes issues du moteur industriel (recommandations d'optimisation) ─
    for rec in exposure_analysis.get("recommendations", []):
        priority  = rec.get("priority", "MOYENNE")
        severity  = Severity.WARNING if priority == "HAUTE" else Severity.INFO

        message        = rec.get("message", "Point d'amélioration détecté")
        action         = rec.get("action", "")
        target         = rec.get("target", "—")
        current        = rec.get("current", "—")
        recommendation = f"{action} | Cible : {target} | Actuel : {current}"

        alerts.append(ValidationAlert(
            severity=severity,
            category="Optimisation EN 206",
            message=message,
            recommendation=recommendation,
            norm_ref="EN 206",
        ))

    # ── Validations physiques modulaires ────────────────────────────────────
    alerts.extend(validate_water_binder_ratio(ratio_el, resistance))
    alerts.extend(validate_substitution_rate(ciment, laitier, cendres))
    alerts.extend(validate_durability(diffusion_cl, carbonatation, ratio_el))
    alerts.extend(validate_cement_content(ciment, liant_total))

    # ── Classe de résistance ────────────────────────────────────────────────
    resistance_class = determine_resistance_class(resistance)

    # ── Score de conformité (corrigé) ───────────────────────────────────────
    compliance_score = calculate_compliance_score(alerts)

    # Léger bonus si la probabilité de la classe gouvernante est très haute
    if hasattr(exposure_result, "probabilities"):
        gov_prob = float(exposure_result.probabilities.get(achieved_class, 0.0))
        if gov_prob > 0.80:
            compliance_score = min(100.0, compliance_score + 3.0)

    # ── Verdict contractuel ─────────────────────────────────────────────────
    if required_class:
        compliance_with_required = _check_compliance_with_required(
            achieved_class=achieved_class,
            required_class=required_class,
        )
    else:
        # Sans classe exigée : valide si aucune alerte CRITICAL
        compliance_with_required = not any(
            a.severity == Severity.CRITICAL for a in alerts
        )

    # ── Validité globale (aucune alerte CRITICAL) ───────────────────────────
    is_valid = not any(a.severity == Severity.CRITICAL for a in alerts)

    logger.info(
        "Validation terminée | alertes=%d | score=%.0f/100 | valide=%s | "
        "exigée=%s | atteinte=%s | conforme=%s",
        len(alerts),
        compliance_score,
        is_valid,
        required_class,
        achieved_class,
        compliance_with_required,
    )

    return ValidationReport(
        is_valid=is_valid,
        alerts=alerts,
        required_class=required_class,
        achieved_class=achieved_class,
        compliance_with_required=compliance_with_required,
        resistance_class=resistance_class,
        compliance_score=compliance_score,
    )


def validate_formulation_probabilistic(
    composition:       Dict[str, float],
    predictions_mean:  Dict[str, float],
    predictions_std:   Dict[str, float],
    confidence_level:  float = 0.95,
) -> Dict:
    """
    Validation probabiliste pour contrôle qualité statistique.

    Prend en compte l'incertitude des prédictions ML pour évaluer
    la robustesse de la conformité (utile en production / Q3).

    Args:
        composition      : Composition béton (kg/m³)
        predictions_mean : Moyennes des propriétés prédites
        predictions_std  : Écarts-types des propriétés prédites
        confidence_level : Niveau de confiance (défaut 0.95 = 95 %)

    Returns:
        Dictionnaire avec :
          - governing_class      : classe gouvernante
          - probabilities        : probabilités par classe
          - confidence_intervals : intervalles de confiance
          - recommendations      : recommandations
          - classes_satisfied    : liste des classes satisfaites
    """
    from .normative_engines import IndustrialEN206Engine

    engine = IndustrialEN206Engine(use_probabilistic=True)

    result = engine.determine_probabilistic(
        ratio_el_mean=predictions_mean["Ratio_E_L"],
        ratio_el_std=predictions_std["Ratio_E_L"],
        resistance_mean=predictions_mean["Resistance"],
        resistance_std=predictions_std["Resistance"],
        diffusion_cl_mean=predictions_mean.get("Diffusion_Cl"),
        diffusion_cl_std=predictions_std.get("Diffusion_Cl"),
        carbonatation_mean=predictions_mean.get("Carbonatation"),
        carbonatation_std=predictions_std.get("Carbonatation"),
        confidence_level=confidence_level,
    )

    return {
        "governing_class":      result.governing_class,
        "probabilities":        result.probabilities,
        "confidence_intervals": result.confidence_intervals,
        "recommendations":      result.recommendations,
        "classes_satisfied":    result.classes,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Point d'entrée principal
    "validate_formulation",
    # Variante probabiliste
    "validate_formulation_probabilistic",
    # Classes de données
    "ValidationReport",
    "ValidationAlert",
    "Severity",
    # Utilitaires
    "determine_exposure_class",
    "determine_resistance_class",
    "calculate_compliance_score",
]