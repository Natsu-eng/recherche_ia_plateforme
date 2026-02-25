"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/normative_engines.py
Moteur normatif avancé EN 206 — Version Industrielle
Gestion multi-classes exposition avec approches déterministe et probabiliste
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Refactorisé & Production Ready
═══════════════════════════════════════════════════════════════════════════════

Caractéristiques:
  ✅ Toutes classes d'exposition (XC, XD, XS, XF, XA)
  ✅ Approche déterministe (seuils stricts EN 206)
  ✅ Approche probabiliste (avec incertitudes — contrôle qualité)
  ✅ Recommandations intelligentes par classe cible
  ✅ Intégration avec constantes centralisées (config/constants.py)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from config.constants import EXPOSURE_CLASSES, QUALITY_THRESHOLDS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ÉNUMÉRATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ExposureCategory(Enum):
    """
    Catégories d'exposition selon EN 206.

    Le nom de l'enum (ex: "XC") correspond au préfixe à 2 caractères
    des codes de classe (ex: "XC1", "XC4").
    """
    XC = "Carbonatation"
    XD = "Chlorures (non marin)"
    XS = "Chlorures marins"
    XF = "Gel / Dégel"
    XA = "Attaques chimiques"

    @classmethod
    def from_class_name(cls, class_name: str) -> "ExposureCategory":
        """
        Détermine la catégorie à partir du code de classe.

        Compare les 2 premiers caractères du code (ex: "XC" de "XC1")
        au nom de l'enum (pas à sa valeur textuelle).

        Args:
            class_name: Code de classe EN 206 (ex: "XC1", "XS3", "XF4")

        Returns:
            ExposureCategory correspondante, XC par défaut si inconnue.

        Example:
            >>> ExposureCategory.from_class_name("XS3")
            <ExposureCategory.XS: 'Chlorures marins'>
        """
        prefix = class_name[:2].upper() if len(class_name) >= 2 else ""
        try:
            # Comparaison sur le NOM de l'enum (ex: "XS"), pas sur sa valeur
            return cls[prefix]
        except KeyError:
            logger.warning(
                "Préfixe '%s' (classe '%s') inconnu dans ExposureCategory — "
                "repli sur XC par défaut.",
                prefix, class_name,
            )
            return cls.XC


class SeverityLevel(Enum):
    """Niveau de sévérité pour les recommandations internes."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExposureCriteria:
    """
    Critères complets pour une classe d'exposition selon EN 206.

    Attributs:
        class_name              : Code de classe (ex: "XC1", "XS3")
        e_l_max                 : Rapport Eau/Liant maximum autorisé
        fc_min                  : Résistance à la compression minimale (MPa)
        diffusion_cl_max        : Diffusion chlorures maximale (×10⁻¹² m²/s) — classes XD/XS
        carbonatation_max       : Profondeur carbonatation maximale (mm) — classes XC
        air_content_min         : Teneur en air minimale (%) — classes XF
        cement_type_recommended : Type de ciment recommandé (texte libre)
        special_requirements    : Exigences spéciales (texte libre)
    """

    class_name:               str
    e_l_max:                  float
    fc_min:                   float
    diffusion_cl_max:         Optional[float] = None
    carbonatation_max:        Optional[float] = None
    air_content_min:          Optional[float] = None
    cement_type_recommended:  Optional[str]   = None
    special_requirements:     Optional[str]   = None

    @property
    def category(self) -> ExposureCategory:
        """Catégorie d'exposition de cette classe."""
        return ExposureCategory.from_class_name(self.class_name)

    @property
    def description(self) -> str:
        """Description normative de la classe (depuis config/constants.py)."""
        return EXPOSURE_CLASSES.get(self.class_name, {}).get("description", "")


@dataclass
class ExposureResult:
    """
    Résultat de la détermination des classes d'exposition (approche déterministe).

    Attributs:
        classes           : Liste de toutes les classes d'exposition satisfaites
        governing_class   : Classe la plus sévère parmi les classes satisfaites
        satisfied_classes : {code_classe: [raisons de satisfaction]}
        failed_classes    : {code_classe: [raisons d'échec]}
        recommendations   : Liste de recommandations pour progresser vers des classes supérieures
    """

    classes:           List[str]
    governing_class:   str
    satisfied_classes: Dict[str, List[str]] = field(default_factory=dict)
    failed_classes:    Dict[str, List[str]] = field(default_factory=dict)
    recommendations:   List[Dict]           = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Sérialisation en dictionnaire (pour API / session Streamlit)."""
        return {
            "classes":           self.classes,
            "governing_class":   self.governing_class,
            "satisfied_classes": self.satisfied_classes,
            "failed_classes":    self.failed_classes,
            "recommendations":   self.recommendations,
        }

    def get_summary(self) -> str:
        """Résumé textuel compact du résultat."""
        return (
            f"Classe gouvernante : {self.governing_class} | "
            f"Classes satisfaites : {len(self.satisfied_classes)} | "
            f"Recommandations : {len(self.recommendations)}"
        )


@dataclass
class ProbabilisticExposureResult(ExposureResult):
    """
    Résultat enrichi avec approche probabiliste (contrôle qualité).

    Attributs supplémentaires:
        probabilities        : {code_classe: probabilité de satisfaction [0–1]}
        confidence_level     : Niveau de confiance utilisé (ex: 0.95)
        confidence_intervals : {code_classe: (borne_inf, borne_sup)}
    """

    probabilities:        Dict[str, float]              = field(default_factory=dict)
    confidence_level:     float                         = 0.95
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def get_most_probable(self, threshold: float = 0.50) -> List[str]:
        """
        Retourne les classes dont la probabilité de satisfaction dépasse le seuil.

        Args:
            threshold: Seuil de probabilité (défaut 0.50)

        Returns:
            Liste de codes de classe
        """
        return [c for c, p in self.probabilities.items() if p > threshold]


@dataclass
class ExposureRecommendation:
    """
    Recommandation de modifications pour atteindre une classe d'exposition cible.

    Attributs:
        target_class     : Classe d'exposition à atteindre
        current_class    : Classe actuellement atteinte
        modifications    : {composant: delta_kg_m3} — modifications suggérées
        priority         : "HAUTE", "MOYENNE" ou "BASSE"
        reasoning        : Raisonnement explicatif (texte multi-lignes)
        estimated_impact : {propriété: valeur_estimée_après_modification}
    """

    target_class:     str
    current_class:    str
    modifications:    Dict[str, float]
    priority:         str
    reasoning:        str
    estimated_impact: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Sérialisation pour l'affichage UI."""
        return {
            "target":        self.target_class,
            "current":       self.current_class,
            "modifications": self.modifications,
            "priority":      self.priority,
            "reasoning":     self.reasoning,
            "impact":        self.estimated_impact,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MOTEUR DÉTERMINISTE
# ═══════════════════════════════════════════════════════════════════════════════

class EN206ExposureEngine:
    """
    Moteur de détermination des classes d'exposition selon EN 206.

    Version déterministe : compare les paramètres réels aux seuils normatifs stricts.
    Construit sa matrice de critères depuis config/constants.EXPOSURE_CLASSES.
    """

    # Ordre de sévérité décroissante (XS3 = le plus sévère, XC1 = le moins sévère)
    SEVERITY_ORDER: List[str] = [
        "XS3", "XS2", "XS1",
        "XD3", "XD2", "XD1",
        "XF4", "XF3", "XF2", "XF1",
        "XA3", "XA2", "XA1",
        "XC4", "XC3", "XC2", "XC1",
    ]

    def __init__(self) -> None:
        """Initialise le moteur et construit la matrice de critères."""
        self._build_criteria_matrix()
        logger.info(
            "Moteur EN 206 (déterministe) initialisé — %d classes chargées",
            len(self.criteria),
        )

    def _build_criteria_matrix(self) -> None:
        """
        Construit la matrice de critères depuis config/constants.EXPOSURE_CLASSES.

        Ajoute les seuils spécifiques par classe (diffusion chlorures, carbonatation,
        teneur en air) qui ne sont pas directement dans les constantes globales.
        """
        self.criteria: Dict[str, ExposureCriteria] = {}

        for class_name, specs in EXPOSURE_CLASSES.items():
            diffusion_max:   Optional[float] = None
            carbonatation_max: Optional[float] = None
            air_min:         Optional[float] = None

            # ── Seuils diffusion chlorures (classes XS et XD) ───────────────
            if class_name in {"XS3", "XD3"}:
                diffusion_max = 5.0
            elif class_name in {"XS2", "XD2"}:
                diffusion_max = 8.0
            elif class_name in {"XS1", "XD1"}:
                diffusion_max = 12.0

            # ── Seuils carbonatation (classes XC) ───────────────────────────
            if class_name == "XC4":
                carbonatation_max = 8.0
            elif class_name == "XC3":
                carbonatation_max = 15.0
            elif class_name == "XC2":
                carbonatation_max = 25.0

            # ── Teneur en air minimale (classes XF) ─────────────────────────
            if class_name in {"XF4", "XF3"}:
                air_min = 4.0
            elif class_name in {"XF2", "XF1"}:
                air_min = 3.0

            self.criteria[class_name] = ExposureCriteria(
                class_name=class_name,
                e_l_max=specs["E_L_max"],
                fc_min=specs["fc_min"],
                diffusion_cl_max=diffusion_max,
                carbonatation_max=carbonatation_max,
                air_content_min=air_min,
                special_requirements=specs.get("description", ""),
            )

    def determine(
        self,
        ratio_el:      float,
        resistance:    float,
        diffusion_cl:  Optional[float] = None,
        carbonatation: Optional[float] = None,
        air_content:   Optional[float] = None,
    ) -> ExposureResult:
        """
        Détermine l'ensemble des classes d'exposition satisfaites.

        Args:
            ratio_el     : Rapport Eau/Liant
            resistance   : Résistance à la compression (MPa)
            diffusion_cl : Diffusion chlorures (×10⁻¹² m²/s) — optionnel
            carbonatation: Profondeur de carbonatation (mm) — optionnel
            air_content  : Teneur en air (%) — optionnel, pour classes XF

        Returns:
            ExposureResult avec classes satisfaites, classe gouvernante et recommandations
        """
        satisfied_classes: Dict[str, List[str]] = {}
        failed_classes:    Dict[str, List[str]] = {}

        for class_name, criteria in self.criteria.items():
            ok, reasons = self._check_class(
                criteria, ratio_el, resistance,
                diffusion_cl, carbonatation, air_content,
            )
            if ok:
                satisfied_classes[class_name] = reasons
            else:
                failed_classes[class_name] = reasons

        classes_list = list(satisfied_classes.keys())
        governing    = self._get_governing_class(classes_list)

        recommendations = self._generate_recommendations(
            ratio_el, resistance, diffusion_cl, carbonatation,
            satisfied_classes, failed_classes,
        )

        return ExposureResult(
            classes=classes_list,
            governing_class=governing,
            satisfied_classes=satisfied_classes,
            failed_classes=failed_classes,
            recommendations=recommendations,
        )

    def _check_class(
        self,
        criteria:      ExposureCriteria,
        ratio_el:      float,
        resistance:    float,
        diffusion_cl:  Optional[float],
        carbonatation: Optional[float],
        air_content:   Optional[float],
    ) -> Tuple[bool, List[str]]:
        """
        Vérifie si une formulation satisfait une classe d'exposition.

        Critères vérifiés dans l'ordre :
          1. Rapport E/L ≤ E/L_max
          2. Résistance ≥ fc_min
          3. Diffusion chlorures ≤ diffusion_cl_max (si applicable)
          4. Carbonatation ≤ carbonatation_max (si applicable)
          5. Teneur en air ≥ air_content_min (si applicable)

        Args:
            criteria     : Critères de la classe à vérifier
            ratio_el     : Rapport E/L
            resistance   : Résistance (MPa)
            diffusion_cl : Diffusion chlorures (optionnel)
            carbonatation: Carbonatation (mm, optionnel)
            air_content  : Teneur en air (%, optionnel)

        Returns:
            (True/False, liste des messages de vérification)
        """
        reasons:   List[str] = []
        satisfied: bool      = True

        # 1. Rapport E/L
        if ratio_el > criteria.e_l_max:
            satisfied = False
            reasons.append(
                f"E/L ({ratio_el:.3f}) > {criteria.e_l_max} (max autorisé)"
            )
        else:
            reasons.append(f"✓ E/L ≤ {criteria.e_l_max}")

        # 2. Résistance minimale
        if resistance < criteria.fc_min:
            satisfied = False
            reasons.append(
                f"Résistance ({resistance:.1f} MPa) < {criteria.fc_min} MPa (minimum requis)"
            )
        else:
            reasons.append(f"✓ Résistance ≥ {criteria.fc_min} MPa")

        # 3. Diffusion chlorures (si la classe l'exige)
        if criteria.diffusion_cl_max is not None:
            if diffusion_cl is None:
                satisfied = False
                reasons.append(
                    f"Donnée diffusion Cl⁻ manquante pour classe {criteria.class_name}"
                )
            elif diffusion_cl > criteria.diffusion_cl_max:
                satisfied = False
                reasons.append(
                    f"Diffusion Cl⁻ ({diffusion_cl:.2f}) > "
                    f"{criteria.diffusion_cl_max} (max autorisé)"
                )
            else:
                reasons.append(f"✓ Diffusion Cl⁻ ≤ {criteria.diffusion_cl_max}")

        # 4. Carbonatation (si la classe l'exige)
        if criteria.carbonatation_max is not None:
            if carbonatation is None:
                satisfied = False
                reasons.append(
                    f"Donnée carbonatation manquante pour classe {criteria.class_name}"
                )
            elif carbonatation > criteria.carbonatation_max:
                satisfied = False
                reasons.append(
                    f"Carbonatation ({carbonatation:.1f} mm) > "
                    f"{criteria.carbonatation_max} mm (max autorisé)"
                )
            else:
                reasons.append(f"✓ Carbonatation ≤ {criteria.carbonatation_max} mm")

        # 5. Teneur en air (classes XF — non bloquant si donnée absente)
        if criteria.air_content_min is not None:
            if air_content is None:
                reasons.append(
                    f"⚠ Teneur en air non fournie — "
                    f"recommandée ≥ {criteria.air_content_min} % pour {criteria.class_name}"
                )
            elif air_content < criteria.air_content_min:
                satisfied = False
                reasons.append(
                    f"Teneur en air ({air_content:.1f} %) < "
                    f"{criteria.air_content_min} % (minimum requis)"
                )
            else:
                reasons.append(f"✓ Teneur en air ≥ {criteria.air_content_min} %")

        return satisfied, reasons

    def _get_governing_class(self, classes: List[str]) -> str:
        """
        Retourne la classe d'exposition la plus sévère parmi la liste fournie.

        Parcourt SEVERITY_ORDER (du plus sévère au moins sévère) et retourne
        la première classe présente dans `classes`.

        Args:
            classes: Liste des classes satisfaites

        Returns:
            Code de la classe gouvernante, "XC1" si la liste est vide ou inconnue.
        """
        if not classes:
            return "XC1"

        for severe_class in self.SEVERITY_ORDER:
            if severe_class in classes:
                return severe_class

        # Fallback : première classe de la liste si aucune dans l'ordre connu
        return classes[0]

    def _generate_recommendations(
        self,
        ratio_el:      float,
        resistance:    float,
        diffusion_cl:  Optional[float],
        carbonatation: Optional[float],
        satisfied:     Dict[str, List[str]],
        failed:        Dict[str, List[str]],
    ) -> List[Dict]:
        """
        Génère des recommandations pour progresser vers des classes supérieures.

        Analyse les 3 classes échouées les plus sévères et propose des actions
        correctives pour chaque critère non satisfait.

        Args:
            ratio_el     : Rapport E/L actuel
            resistance   : Résistance actuelle (MPa)
            diffusion_cl : Diffusion chlorures (optionnel)
            carbonatation: Carbonatation (mm, optionnel)
            satisfied    : Classes satisfaites
            failed       : Classes non satisfaites

        Returns:
            Liste de dictionnaires de recommandations (max 3)
        """
        recommendations: List[Dict] = []

        # Classes échouées triées par sévérité décroissante
        priority_classes = [c for c in self.SEVERITY_ORDER if c in failed]

        for class_name in priority_classes[:3]:
            reasons  = failed[class_name]
            criteria = self.criteria[class_name]
            is_severe = class_name[:2] in {"XS", "XD"}

            for reason in reasons:

                # ── Recommandation : réduction E/L ─────────────────────────
                if "E/L" in reason and ">" in reason:
                    reduction_pct = ((ratio_el - criteria.e_l_max) / ratio_el) * 100
                    recommendations.append({
                        "class":    class_name,
                        "priority": "HAUTE" if is_severe else "MOYENNE",
                        "message":  (
                            f"Réduire E/L de {reduction_pct:.1f} % "
                            f"pour atteindre {class_name}"
                        ),
                        "action":  "Réduire eau ou augmenter liant",
                        "target":  f"E/L ≤ {criteria.e_l_max}",
                        "current": f"{ratio_el:.3f}",
                    })

                # ── Recommandation : augmentation résistance ────────────────
                elif "Résistance" in reason and "<" in reason:
                    delta_fc = criteria.fc_min - resistance
                    recommendations.append({
                        "class":    class_name,
                        "priority": "MOYENNE",
                        "message":  (
                            f"Augmenter résistance de {delta_fc:.1f} MPa "
                            f"pour atteindre {class_name}"
                        ),
                        "action":  "Augmenter dosage liant ou réduire E/L",
                        "target":  f"Résistance ≥ {criteria.fc_min} MPa",
                        "current": f"{resistance:.1f} MPa",
                    })

                # ── Recommandation : résistance aux chlorures ───────────────
                elif "Diffusion" in reason and ">" in reason:
                    recommendations.append({
                        "class":    class_name,
                        "priority": "HAUTE",
                        "message":  (
                            f"Améliorer résistance aux chlorures pour atteindre {class_name}"
                        ),
                        "action":  "Ajouter laitier (20–30 %) ou fumée de silice (5–10 %)",
                        "target":  f"Diffusion Cl⁻ ≤ {criteria.diffusion_cl_max}",
                        "current": f"{diffusion_cl:.2f}" if diffusion_cl is not None else "N/A",
                    })

        return recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# MOTEUR PROBABILISTE
# ═══════════════════════════════════════════════════════════════════════════════

class ProbabilisticEN206Engine(EN206ExposureEngine):
    """
    Extension probabiliste du moteur EN 206 pour contrôle qualité industriel.

    Prend en compte l'incertitude de mesure des paramètres en calculant
    la probabilité que chaque critère soit satisfait (loi normale).
    Utilisé pour évaluer la robustesse d'une formulation en production.
    """

    def determine_probabilistic(
        self,
        ratio_el_mean:      float,
        ratio_el_std:       float,
        resistance_mean:    float,
        resistance_std:     float,
        diffusion_cl_mean:  Optional[float] = None,
        diffusion_cl_std:   Optional[float] = None,
        carbonatation_mean: Optional[float] = None,
        carbonatation_std:  Optional[float] = None,
        confidence_level:   float = 0.95,
    ) -> ProbabilisticExposureResult:
        """
        Détermine les classes d'exposition avec prise en compte des incertitudes.

        Modèle probabiliste :
          - P(E/L ≤ seuil) = CDF normale(seuil | μ_EL, σ_EL)
          - P(fc ≥ seuil)  = 1 - CDF normale(seuil | μ_fc, σ_fc)
          - P_totale       = produit des probabilités (indépendance supposée)

        Args:
            ratio_el_mean      : Moyenne du rapport E/L
            ratio_el_std       : Écart-type du rapport E/L
            resistance_mean    : Moyenne de la résistance (MPa)
            resistance_std     : Écart-type de la résistance (MPa)
            diffusion_cl_mean  : Moyenne diffusion chlorures (optionnel)
            diffusion_cl_std   : Écart-type diffusion chlorures (optionnel)
            carbonatation_mean : Moyenne carbonatation (mm, optionnel)
            carbonatation_std  : Écart-type carbonatation (mm, optionnel)
            confidence_level   : Niveau de confiance pour les IC (défaut 0.95)

        Returns:
            ProbabilisticExposureResult avec probabilités et intervalles de confiance
        """
        probabilities:        Dict[str, float]               = {}
        confidence_intervals: Dict[str, Tuple[float, float]] = {}

        z_score = float(stats.norm.ppf((1.0 + confidence_level) / 2.0))

        for class_name, criteria in self.criteria.items():

            # P(E/L ≤ seuil)
            p_el = float(stats.norm.cdf(
                criteria.e_l_max,
                loc=ratio_el_mean,
                scale=max(ratio_el_std, 1e-9),  # éviter std=0
            ))

            # P(résistance ≥ seuil)
            p_res = 1.0 - float(stats.norm.cdf(
                criteria.fc_min,
                loc=resistance_mean,
                scale=max(resistance_std, 1e-9),
            ))

            p_total = p_el * p_res

            # P(diffusion ≤ seuil) — si applicable
            if (criteria.diffusion_cl_max is not None
                    and diffusion_cl_mean is not None
                    and diffusion_cl_std is not None):
                p_diff = float(stats.norm.cdf(
                    criteria.diffusion_cl_max,
                    loc=diffusion_cl_mean,
                    scale=max(diffusion_cl_std, 1e-9),
                ))
                p_total *= p_diff

            # P(carbonatation ≤ seuil) — si applicable
            if (criteria.carbonatation_max is not None
                    and carbonatation_mean is not None
                    and carbonatation_std is not None):
                p_carb = float(stats.norm.cdf(
                    criteria.carbonatation_max,
                    loc=carbonatation_mean,
                    scale=max(carbonatation_std, 1e-9),
                ))
                p_total *= p_carb

            probabilities[class_name] = min(1.0, max(0.0, p_total))

            # Intervalle de confiance de Wilson pour la probabilité estimée
            # (hypothèse : n ≈ 30 observations comme approximation de production)
            n  = 30.0
            se = float(np.sqrt(p_total * (1.0 - p_total) / n))
            confidence_intervals[class_name] = (
                max(0.0, p_total - z_score * se),
                min(1.0, p_total + z_score * se),
            )

        # Classe gouvernante probabiliste
        governing = self._get_probabilistic_governing_class(probabilities)

        # Résultat déterministe de base (sur les valeurs moyennes)
        det_result = super().determine(
            ratio_el=ratio_el_mean,
            resistance=resistance_mean,
            diffusion_cl=diffusion_cl_mean,
            carbonatation=carbonatation_mean,
        )

        return ProbabilisticExposureResult(
            classes=det_result.classes,
            governing_class=governing,
            satisfied_classes=det_result.satisfied_classes,
            failed_classes=det_result.failed_classes,
            recommendations=det_result.recommendations,
            probabilities=probabilities,
            confidence_level=confidence_level,
            confidence_intervals=confidence_intervals,
        )

    def _get_probabilistic_governing_class(
        self,
        probabilities: Dict[str, float],
        threshold: float = 0.50,
    ) -> str:
        """
        Classe gouvernante en approche probabiliste.

        Retourne la classe la plus sévère dont P > threshold,
        ou la classe avec la probabilité maximale si aucune ne dépasse le seuil.

        Args:
            probabilities: {code_classe: probabilité}
            threshold    : Seuil de confiance (défaut 0.50)

        Returns:
            Code de classe gouvernante
        """
        for severe_class in self.SEVERITY_ORDER:
            if severe_class in probabilities and probabilities[severe_class] > threshold:
                return severe_class

        # Fallback : classe avec probabilité maximale
        if probabilities:
            return max(probabilities, key=lambda c: probabilities[c])

        return "XC1"


# ═══════════════════════════════════════════════════════════════════════════════
# CONSEILLER POUR AMÉLIORATION
# ═══════════════════════════════════════════════════════════════════════════════

class ExposureAdvisor:
    """
    Conseiller intelligent pour atteindre des classes d'exposition cibles.

    Utilise des facteurs d'impact approximatifs (issus de la littérature)
    pour estimer l'effet des modifications de composition sur les propriétés.
    """

    # Facteurs d'impact approximatifs par constituant et propriété.
    # Interprétation : +10 kg/m³ de "Ciment" → +0.15 × 10 = +1.5 MPa résistance
    _IMPACT_FACTORS: Dict[str, Dict[str, float]] = {
        "Ciment":          {"resistance": 0.15, "e_l": -0.02, "diffusion": -0.05},
        "Laitier":         {"resistance": 0.08, "diffusion": -0.15, "carbonatation": 0.10},
        "Eau":             {"resistance": -0.30, "e_l": 0.10},
        "Superplastifiant":{"resistance": 0.20, "e_l": -0.03},
    }

    # Classes nécessitant une action prioritaire
    _HAUTE_PRIORITY_PREFIXES: frozenset = frozenset({"XS", "XD", "XA"})

    def __init__(self, engine: EN206ExposureEngine) -> None:
        """
        Initialise le conseiller avec un moteur EN 206.

        Args:
            engine: Instance du moteur déterministe
        """
        self.engine = engine

    def recommend_for_target(
        self,
        composition: Dict[str, float],
        predictions: Dict[str, float],
        target_class: str,
        max_iterations: int = 5,
    ) -> ExposureRecommendation:
        """
        Recommande des modifications de composition pour atteindre une classe cible.

        Si la classe est déjà satisfaite, retourne une recommandation vide
        avec priorité "BASSE" et message de confirmation.

        Args:
            composition    : Composition actuelle (kg/m³)
            predictions    : Prédictions actuelles (Ratio_E_L, Resistance, etc.)
            target_class   : Code de classe cible (ex: "XS3")
            max_iterations : Nombre max d'itérations d'analyse (réservé)

        Returns:
            ExposureRecommendation avec modifications suggérées et impact estimé

        Raises:
            ValueError: Si target_class n'est pas dans le référentiel
        """
        if target_class not in self.engine.criteria:
            raise ValueError(
                f"Classe cible '{target_class}' inconnue. "
                f"Classes disponibles : {list(self.engine.criteria.keys())}"
            )

        # Résultat actuel
        current_result = self.engine.determine(
            ratio_el=predictions["Ratio_E_L"],
            resistance=predictions["Resistance"],
            diffusion_cl=predictions.get("Diffusion_Cl"),
            carbonatation=predictions.get("Carbonatation"),
        )
        current_class = current_result.governing_class

        # Classe cible déjà satisfaite ?
        if target_class in current_result.classes:
            return ExposureRecommendation(
                target_class=target_class,
                current_class=current_class,
                modifications={},
                priority="BASSE",
                reasoning=(
                    f"La classe {target_class} est déjà satisfaite par la formulation."
                ),
            )

        criteria         = self.engine.criteria[target_class]
        modifications:   Dict[str, float] = {}
        reasoning_lines: List[str]        = []

        # ── Correction E/L ──────────────────────────────────────────────────
        if predictions["Ratio_E_L"] > criteria.e_l_max:
            excess_el = predictions["Ratio_E_L"] - criteria.e_l_max
            eau_actuelle = composition.get("Eau", 0.0)

            if eau_actuelle > 140.0:
                # Réduire l'eau
                water_reduction = min(excess_el * 100.0, 20.0)
                modifications["Eau"] = -water_reduction
                reasoning_lines.append(
                    f"Réduire l'eau de {water_reduction:.0f} kg/m³ "
                    f"pour atteindre E/L ≤ {criteria.e_l_max}"
                )
            else:
                # Augmenter le liant
                binder_increase = excess_el * 200.0
                modifications["Ciment"] = modifications.get("Ciment", 0.0) + binder_increase
                reasoning_lines.append(
                    f"Augmenter ciment de {binder_increase:.0f} kg/m³ "
                    f"pour atteindre E/L ≤ {criteria.e_l_max}"
                )

        # ── Correction résistance ────────────────────────────────────────────
        if predictions["Resistance"] < criteria.fc_min:
            delta_fc       = criteria.fc_min - predictions["Resistance"]
            cement_needed  = delta_fc / 0.15  # ~0.15 MPa / kg ciment
            modifications["Ciment"] = modifications.get("Ciment", 0.0) + cement_needed
            reasoning_lines.append(
                f"Augmenter ciment de {cement_needed:.0f} kg/m³ "
                f"pour atteindre résistance ≥ {criteria.fc_min} MPa"
            )

        # ── Correction diffusion chlorures ───────────────────────────────────
        if (criteria.diffusion_cl_max is not None
                and predictions.get("Diffusion_Cl", 99.0) > criteria.diffusion_cl_max):
            laitier_actuel = composition.get("Laitier", 0.0)
            if laitier_actuel < 150.0:
                slag_add = 50.0
                modifications["Laitier"] = modifications.get("Laitier", 0.0) + slag_add
                modifications["Ciment"]  = modifications.get("Ciment", 0.0) - 30.0
                reasoning_lines.append(
                    f"Ajouter {slag_add:.0f} kg/m³ de laitier pour améliorer "
                    f"la résistance aux chlorures (Diffusion cible ≤ {criteria.diffusion_cl_max})"
                )

        estimated_impact = self._estimate_impact(composition, modifications, predictions)
        priority         = self._determine_priority(target_class)
        reasoning        = "\n".join(reasoning_lines) or f"Optimisation vers {target_class}"

        return ExposureRecommendation(
            target_class=target_class,
            current_class=current_class,
            modifications=modifications,
            priority=priority,
            reasoning=reasoning,
            estimated_impact=estimated_impact,
        )

    def _estimate_impact(
        self,
        composition:   Dict[str, float],
        modifications: Dict[str, float],
        predictions:   Dict[str, float],
    ) -> Dict[str, float]:
        """
        Estime l'impact des modifications proposées sur les propriétés béton.

        Utilise les facteurs d'impact linéaires de _IMPACT_FACTORS.
        L'estimation est une approximation au premier ordre, non une prédiction ML.

        Args:
            composition  : Composition actuelle (kg/m³)
            modifications: Deltas de composition (kg/m³)
            predictions  : Prédictions actuelles

        Returns:
            Dictionnaire des propriétés estimées après modification
        """
        impact: Dict[str, float] = {
            "Ratio_E_L":   predictions["Ratio_E_L"],
            "Resistance":  predictions["Resistance"],
            "Diffusion_Cl":  predictions.get("Diffusion_Cl", 0.0),
            "Carbonatation": predictions.get("Carbonatation", 0.0),
        }

        for comp, delta in modifications.items():
            factors = self._IMPACT_FACTORS.get(comp, {})
            for prop, factor in factors.items():
                if prop == "e_l":
                    impact["Ratio_E_L"]    += delta * factor / 100.0
                elif prop == "resistance":
                    impact["Resistance"]   += delta * factor
                elif prop == "diffusion":
                    impact["Diffusion_Cl"] = max(
                        0.0, impact["Diffusion_Cl"] * (1.0 + delta * factor / 100.0)
                    )
                elif prop == "carbonatation":
                    impact["Carbonatation"] = max(
                        0.0, impact["Carbonatation"] * (1.0 + delta * factor / 100.0)
                    )

        return {k: round(v, 3) for k, v in impact.items()}

    def _determine_priority(self, target_class: str) -> str:
        """
        Détermine le niveau de priorité selon la classe cible.

        Args:
            target_class: Code de classe EN 206

        Returns:
            "HAUTE", "MOYENNE" ou "BASSE"
        """
        prefix = target_class[:2].upper()
        if prefix in self._HAUTE_PRIORITY_PREFIXES:
            return "HAUTE"
        if target_class in {"XC4", "XF3", "XF4"}:
            return "MOYENNE"
        return "BASSE"


# ═══════════════════════════════════════════════════════════════════════════════
# MOTEUR INDUSTRIEL COMPLET (FAÇADE)
# ═══════════════════════════════════════════════════════════════════════════════

class IndustrialEN206Engine:
    """
    Façade du moteur EN 206 version industrielle.

    Intègre les approches déterministe, probabiliste et les recommandations
    dans une interface unifiée.

    Usage:
        engine = IndustrialEN206Engine()

        # Mode déterministe
        result = engine.determine(ratio_el=0.45, resistance=40.0)

        # Mode probabiliste (contrôle qualité)
        result = engine.determine_probabilistic(
            ratio_el_mean=0.45, ratio_el_std=0.02,
            resistance_mean=40.0, resistance_std=3.0,
        )

        # Analyse complète + recommandations
        analysis = engine.analyze(composition, predictions)
    """

    # Classes cibles pour les recommandations automatiques dans analyze()
    _AUTO_RECOMMEND_CLASSES: List[str] = ["XS3", "XS2", "XD3", "XF4", "XC4"]

    def __init__(self, use_probabilistic: bool = False) -> None:
        """
        Initialise le moteur industriel avec ses sous-moteurs.

        Args:
            use_probabilistic: Réservé — active le mode probabiliste par défaut
                               dans les appels futurs (non encore utilisé).
        """
        self.deterministic    = EN206ExposureEngine()
        self.probabilistic    = ProbabilisticEN206Engine()
        self.advisor          = ExposureAdvisor(self.deterministic)
        self.use_probabilistic = use_probabilistic

    def determine(
        self,
        ratio_el:      float,
        resistance:    float,
        diffusion_cl:  Optional[float] = None,
        carbonatation: Optional[float] = None,
        air_content:   Optional[float] = None,
        **kwargs,
    ) -> ExposureResult:
        """
        Détermination déterministe des classes d'exposition.

        Args:
            ratio_el     : Rapport E/L
            resistance   : Résistance à la compression (MPa)
            diffusion_cl : Diffusion chlorures (optionnel)
            carbonatation: Carbonatation (mm, optionnel)
            air_content  : Teneur en air (%, optionnel)

        Returns:
            ExposureResult avec classes satisfaites et recommandations
        """
        return self.deterministic.determine(
            ratio_el=ratio_el,
            resistance=resistance,
            diffusion_cl=diffusion_cl,
            carbonatation=carbonatation,
            air_content=air_content,
        )

    def determine_probabilistic(
        self,
        ratio_el_mean:      float,
        ratio_el_std:       float,
        resistance_mean:    float,
        resistance_std:     float,
        diffusion_cl_mean:  Optional[float] = None,
        diffusion_cl_std:   Optional[float] = None,
        carbonatation_mean: Optional[float] = None,
        carbonatation_std:  Optional[float] = None,
        confidence_level:   float = 0.95,
    ) -> ProbabilisticExposureResult:
        """
        Détermination probabiliste avec prise en compte des incertitudes.

        Args:
            ratio_el_mean/std      : Moyenne et écart-type du rapport E/L
            resistance_mean/std    : Moyenne et écart-type de la résistance (MPa)
            diffusion_cl_mean/std  : Diffusion chlorures (optionnel)
            carbonatation_mean/std : Carbonatation (mm, optionnel)
            confidence_level       : Niveau de confiance (défaut 0.95)

        Returns:
            ProbabilisticExposureResult avec probabilités et intervalles
        """
        return self.probabilistic.determine_probabilistic(
            ratio_el_mean=ratio_el_mean,
            ratio_el_std=ratio_el_std,
            resistance_mean=resistance_mean,
            resistance_std=resistance_std,
            diffusion_cl_mean=diffusion_cl_mean,
            diffusion_cl_std=diffusion_cl_std,
            carbonatation_mean=carbonatation_mean,
            carbonatation_std=carbonatation_std,
            confidence_level=confidence_level,
        )

    def recommend(
        self,
        composition:  Dict[str, float],
        predictions:  Dict[str, float],
        target_class: str,
    ) -> ExposureRecommendation:
        """
        Génère des recommandations pour atteindre une classe d'exposition cible.

        Args:
            composition : Composition béton actuelle (kg/m³)
            predictions : Prédictions ML actuelles
            target_class: Code de classe cible (ex: "XS3")

        Returns:
            ExposureRecommendation avec modifications et impact estimé
        """
        return self.advisor.recommend_for_target(
            composition=composition,
            predictions=predictions,
            target_class=target_class,
        )

    def analyze(
        self,
        composition: Dict[str, float],
        predictions: Dict[str, float],
    ) -> Dict:
        """
        Analyse complète : détermination + recommandations vers classes supérieures.

        Tente de générer des recommandations vers les classes de _AUTO_RECOMMEND_CLASSES
        non encore satisfaites. Les erreurs individuelles sont logguées mais n'arrêtent
        pas l'analyse (robustesse).

        Args:
            composition: Composition béton (kg/m³)
            predictions: Prédictions ML (doit contenir Ratio_E_L, Resistance, etc.)

        Returns:
            Dictionnaire avec :
              - "current"        : résultat to_dict() de la classe atteinte
              - "recommendations": liste de recommendations.to_dict() (max 3)
              - "summary"        : résumé textuel
        """
        result = self.determine(
            ratio_el=predictions["Ratio_E_L"],
            resistance=predictions["Resistance"],
            diffusion_cl=predictions.get("Diffusion_Cl"),
            carbonatation=predictions.get("Carbonatation"),
        )

        recommendations: List[Dict] = []

        for target in self._AUTO_RECOMMEND_CLASSES:
            if target in result.classes:
                continue  # Déjà satisfaite, pas de recommandation nécessaire

            try:
                rec = self.advisor.recommend_for_target(
                    composition=composition,
                    predictions=predictions,
                    target_class=target,
                )
                recommendations.append(rec.to_dict())
            except ValueError as ve:
                # Classe cible inconnue — non critique, on continue
                logger.debug(
                    "Recommandation ignorée pour classe '%s' : %s", target, ve
                )
            except Exception as exc:
                # Erreur inattendue — logguer mais ne pas interrompre l'analyse
                logger.warning(
                    "Erreur lors de la recommandation vers '%s' : %s",
                    target, exc, exc_info=True,
                )

        return {
            "current":         result.to_dict(),
            "recommendations": recommendations[:3],  # Top 3
            "summary":         result.get_summary(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_exposure_engine(version: str = "industrial") -> IndustrialEN206Engine:
    """
    Factory function — retourne le moteur d'exposition demandé.

    Args:
        version: "simple", "probabilistic" ou "industrial" (défaut)

    Returns:
        Instance de moteur EN 206

    Note:
        Pour rétro-compatibilité, "simple" et "probabilistic" retournent
        tous deux un IndustrialEN206Engine (la façade unifiée).
    """
    if version == "probabilistic":
        return IndustrialEN206Engine(use_probabilistic=True)

    # "simple" et "industrial" retournent la même façade
    return IndustrialEN206Engine()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Moteurs
    "EN206ExposureEngine",
    "ProbabilisticEN206Engine",
    "ExposureAdvisor",
    "IndustrialEN206Engine",
    # Structures de données
    "ExposureResult",
    "ProbabilisticExposureResult",
    "ExposureRecommendation",
    "ExposureCriteria",
    # Énumérations
    "ExposureCategory",
    "SeverityLevel",
    # Factory
    "get_exposure_engine",
]