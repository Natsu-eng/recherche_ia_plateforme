"""
═══════════════════════════════════════════════════════════════════════
MODULE: normative_engine.py
Moteur normatif avancé EN 206 - Version Industrielle
Gestion multi-classes exposition avec approches déterministe et probabiliste
Auteur: Stage R&D - IMT Nord Europe
Version: 2.0.0 - Industrial Grade with Probabilistic Approach
═══════════════════════════════════════════════════════════════════════

Caractéristiques:
✅ Toutes classes d'exposition (XC, XD, XS, XF, XA)
✅ Approche déterministe (seuils stricts)
✅ Approche probabiliste (avec incertitudes)
✅ Recommandations intelligentes
✅ Intégration avec constantes centralisées
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
import numpy as np
from scipy import stats

from config.constants import EXPOSURE_CLASSES, QUALITY_THRESHOLDS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# ÉNUMÉRATIONS & TYPES
# ═══════════════════════════════════════════════════════════════════════

class ExposureCategory(Enum):
    """Catégories d'exposition selon EN 206"""
    XC = "Carbonatation"
    XD = "Chlorures (non marin)"
    XS = "Chlorures marins"
    XF = "Gel/Dégel"
    XA = "Attaques chimiques"
    
    @classmethod
    def from_class_name(cls, class_name: str) -> 'ExposureCategory':
        """Détermine la catégorie à partir du nom de classe"""
        prefix = class_name[:2] if len(class_name) >= 2 else ""
        for category in cls:
            if category.value == prefix or category.name == prefix:
                return category
        return cls.XC  # Default


class SeverityLevel(Enum):
    """Niveau de sévérité pour les recommandations"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ═══════════════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ExposureCriteria:
    """
    Critères complets pour une classe d'exposition selon EN 206
    
    Attributs:
        class_name: Nom de la classe (ex: "XC1")
        e_l_max: Rapport E/L maximum
        fc_min: Résistance minimale (MPa)
        diffusion_cl_max: Coefficient diffusion chlorures max (×10⁻¹² m²/s)
        carbonatation_max: Profondeur carbonatation max (mm)
        air_content_min: Teneur en air minimale (%) - pour classes XF
        cement_type_recommended: Type de ciment recommandé
        special_requirements: Exigences spéciales (texte)
    """
    class_name: str
    e_l_max: float
    fc_min: float
    diffusion_cl_max: Optional[float] = None
    carbonatation_max: Optional[float] = None
    air_content_min: Optional[float] = None
    cement_type_recommended: Optional[str] = None
    special_requirements: Optional[str] = None
    
    @property
    def category(self) -> ExposureCategory:
        """Catégorie d'exposition"""
        return ExposureCategory.from_class_name(self.class_name)
    
    @property
    def description(self) -> str:
        """Description de la classe"""
        from config.constants import EXPOSURE_CLASSES
        return EXPOSURE_CLASSES.get(self.class_name, {}).get("description", "")


@dataclass
class ExposureResult:
    """
    Résultat de détermination des classes d'exposition
    
    Attributs:
        classes: Liste de toutes les classes satisfaites
        governing_class: Classe la plus sévère
        satisfied_classes: Classes satisfaites avec détails
        failed_classes: Classes échouées avec raisons
        recommendations: Recommandations pour amélioration
    """
    classes: List[str]
    governing_class: str
    satisfied_classes: Dict[str, List[str]] = field(default_factory=dict)
    failed_classes: Dict[str, List[str]] = field(default_factory=dict)
    recommendations: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Conversion en dictionnaire pour API"""
        return {
            "classes": self.classes,
            "governing_class": self.governing_class,
            "satisfied_classes": self.satisfied_classes,
            "failed_classes": self.failed_classes,
            "recommendations": self.recommendations
        }
    
    def get_summary(self) -> str:
        """Résumé textuel"""
        return (f"Classe gouvernante: {self.governing_class} | "
                f"Classes satisfaites: {len(self.satisfied_classes)} | "
                f"Recommandations: {len(self.recommendations)}")


@dataclass
class ProbabilisticExposureResult(ExposureResult):
    """
    Résultat avec approche probabiliste
    
    Attributs supplémentaires:
        probabilities: Probabilités pour chaque classe
        confidence_level: Niveau de confiance
        confidence_intervals: Intervalles de confiance
    """
    probabilities: Dict[str, float] = field(default_factory=dict)
    confidence_level: float = 0.95
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    def get_most_probable(self, threshold: float = 0.5) -> List[str]:
        """Retourne les classes avec probabilité > threshold"""
        return [c for c, p in self.probabilities.items() if p > threshold]


@dataclass
class ExposureRecommendation:
    """
    Recommandation pour atteindre une classe d'exposition
    
    Attributs:
        target_class: Classe cible à atteindre
        current_class: Classe actuelle
        modifications: Modifications suggérées (clé: composant, valeur: delta)
        priority: Priorité d'action (Haute/Moyenne/Basse)
        reasoning: Raisonnement détaillé
        estimated_impact: Impact estimé sur la performance
    """
    target_class: str
    current_class: str
    modifications: Dict[str, float]
    priority: str
    reasoning: str
    estimated_impact: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Conversion pour affichage"""
        return {
            "target": self.target_class,
            "current": self.current_class,
            "modifications": self.modifications,
            "priority": self.priority,
            "reasoning": self.reasoning,
            "impact": self.estimated_impact
        }


# ═══════════════════════════════════════════════════════════════════════
# MOTEUR PRINCIPAL - VERSION DÉTERMINISTE
# ═══════════════════════════════════════════════════════════════════════

class EN206ExposureEngine:
    """
    Moteur de détermination des classes d'exposition selon EN 206
    Version déterministe avec tous les critères normatifs
    """
    
    # Ordre de sévérité des classes (de la plus sévère à la moins sévère)
    SEVERITY_ORDER = [
        "XS3", "XS2", "XS1",  # Classes marines
        "XD3", "XD2", "XD1",  # Classes chlorures
        "XF4", "XF3", "XF2", "XF1",  # Classes gel
        "XA3", "XA2", "XA1",  # Classes chimiques
        "XC4", "XC3", "XC2", "XC1"  # Classes carbonatation
    ]
    
    def __init__(self):
        """Initialisation du moteur avec les constantes EN 206"""
        self._build_criteria_matrix()
        logger.info(f"Moteur EN 206 initialisé avec {len(self.criteria)} classes")
    
    def _build_criteria_matrix(self):
        """
        Construit la matrice de critères à partir des constantes
        Utilise les données de config.constants.EXPOSURE_CLASSES
        """
        self.criteria = {}
        
        for class_name, specs in EXPOSURE_CLASSES.items():
            # Définir des seuils spécifiques selon la classe
            diffusion_max = None
            carbonatation_max = None
            air_min = None
            
            # Seuils spécifiques pour classes chlorures
            if class_name in ["XS3", "XD3"]:
                diffusion_max = 5.0
            elif class_name in ["XS2", "XD2"]:
                diffusion_max = 8.0
            elif class_name in ["XS1", "XD1"]:
                diffusion_max = 12.0
            
            # Seuils spécifiques pour carbonatation
            if class_name == "XC4":
                carbonatation_max = 8.0
            elif class_name == "XC3":
                carbonatation_max = 15.0
            elif class_name == "XC2":
                carbonatation_max = 25.0
            
            # Seuils spécifiques pour classes gel (XF)
            if class_name in ["XF4", "XF3"]:
                air_min = 4.0  # Teneur en air minimale 4%
            elif class_name in ["XF2", "XF1"]:
                air_min = 3.0
            
            self.criteria[class_name] = ExposureCriteria(
                class_name=class_name,
                e_l_max=specs["E_L_max"],
                fc_min=specs["fc_min"],
                diffusion_cl_max=diffusion_max,
                carbonatation_max=carbonatation_max,
                air_content_min=air_min,
                special_requirements=specs.get("description", "")
            )
    
    def determine(
        self,
        ratio_el: float,
        resistance: float,
        diffusion_cl: Optional[float] = None,
        carbonatation: Optional[float] = None,
        air_content: Optional[float] = None
    ) -> ExposureResult:
        """
        Détermine les classes d'exposition satisfaites
        
        Args:
            ratio_el: Rapport Eau/Liant
            resistance: Résistance à la compression (MPa)
            diffusion_cl: Coefficient diffusion chlorures (optionnel)
            carbonatation: Profondeur carbonatation (mm) (optionnel)
            air_content: Teneur en air (%) (optionnel, pour classes XF)
            
        Returns:
            ExposureResult avec toutes les classes satisfaites
        """
        satisfied_classes = {}
        failed_classes = {}
        
        # Vérifier chaque classe d'exposition
        for class_name, criteria in self.criteria.items():
            is_satisfied, reasons = self._check_class(
                criteria, ratio_el, resistance, 
                diffusion_cl, carbonatation, air_content
            )
            
            if is_satisfied:
                satisfied_classes[class_name] = reasons
            else:
                failed_classes[class_name] = reasons
        
        # Liste des classes satisfaites
        classes_satisfied = list(satisfied_classes.keys())
        
        # Déterminer la classe gouvernante (la plus sévère)
        governing = self._get_governing_class(classes_satisfied)
        
        # Générer des recommandations si aucune classe sévère n'est satisfaite
        recommendations = self._generate_recommendations(
            ratio_el, resistance, diffusion_cl, carbonatation,
            satisfied_classes, failed_classes
        )
        
        return ExposureResult(
            classes=classes_satisfied,
            governing_class=governing,
            satisfied_classes=satisfied_classes,
            failed_classes=failed_classes,
            recommendations=recommendations
        )
    
    def _check_class(
        self,
        criteria: ExposureCriteria,
        ratio_el: float,
        resistance: float,
        diffusion_cl: Optional[float],
        carbonatation: Optional[float],
        air_content: Optional[float]
    ) -> Tuple[bool, List[str]]:
        """
        Vérifie si la formulation satisfait une classe d'exposition spécifique
        
        Returns:
            Tuple (est_satisfaite, liste_des_raisons)
        """
        reasons = []
        satisfied = True
        
        # 1. Vérification du rapport E/L
        if ratio_el > criteria.e_l_max:
            satisfied = False
            reasons.append(f"E/L ({ratio_el:.3f}) > {criteria.e_l_max} (max autorisé)")
        else:
            reasons.append(f"✓ E/L ≤ {criteria.e_l_max}")
        
        # 2. Vérification de la résistance minimale
        if resistance < criteria.fc_min:
            satisfied = False
            reasons.append(f"Résistance ({resistance:.1f} MPa) < {criteria.fc_min} MPa (minimum requis)")
        else:
            reasons.append(f"✓ Résistance ≥ {criteria.fc_min} MPa")
        
        # 3. Vérification diffusion chlorures (si applicable)
        if criteria.diffusion_cl_max is not None:
            if diffusion_cl is None:
                satisfied = False
                reasons.append(f"Donnée diffusion Cl⁻ manquante pour classe {criteria.class_name}")
            elif diffusion_cl > criteria.diffusion_cl_max:
                satisfied = False
                reasons.append(f"Diffusion Cl⁻ ({diffusion_cl:.2f}) > {criteria.diffusion_cl_max} (max autorisé)")
            else:
                reasons.append(f"✓ Diffusion Cl⁻ ≤ {criteria.diffusion_cl_max}")
        
        # 4. Vérification carbonatation (si applicable)
        if criteria.carbonatation_max is not None:
            if carbonatation is None:
                satisfied = False
                reasons.append(f"Donnée carbonatation manquante pour classe {criteria.class_name}")
            elif carbonatation > criteria.carbonatation_max:
                satisfied = False
                reasons.append(f"Carbonatation ({carbonatation:.1f} mm) > {criteria.carbonatation_max} mm (max autorisé)")
            else:
                reasons.append(f"✓ Carbonatation ≤ {criteria.carbonatation_max} mm")
        
        # 5. Vérification teneur en air (pour classes gel)
        if criteria.air_content_min is not None:
            if air_content is None:
                # Non bloquant mais recommandation
                reasons.append(f"⚠ Teneur en air recommandée ≥ {criteria.air_content_min}% pour {criteria.class_name}")
            elif air_content < criteria.air_content_min:
                satisfied = False
                reasons.append(f"Teneur en air ({air_content:.1f}%) < {criteria.air_content_min}% (minimum requis)")
            else:
                reasons.append(f"✓ Teneur en air ≥ {criteria.air_content_min}%")
        
        return satisfied, reasons
    
    def _get_governing_class(self, classes: List[str]) -> str:
        """
        Détermine la classe la plus sévère parmi la liste
        
        Ordre de sévérité (du plus sévère au moins sévère):
        XS3 > XS2 > XS1 > XD3 > XD2 > XD1 > XF4 > XF3 > XF2 > XF1 > XC4 > XC3 > XC2 > XC1
        """
        for severe_class in self.SEVERITY_ORDER:
            if severe_class in classes:
                return severe_class
        
        return classes[0] if classes else "XC1"
    
    def _generate_recommendations(
        self,
        ratio_el: float,
        resistance: float,
        diffusion_cl: Optional[float],
        carbonatation: Optional[float],
        satisfied: Dict,
        failed: Dict
    ) -> List[Dict]:
        """
        Génère des recommandations pour améliorer la classe d'exposition
        """
        recommendations = []
        
        # Analyser les classes échouées les plus critiques
        priority_classes = [c for c in self.SEVERITY_ORDER if c in failed]
        
        for class_name in priority_classes[:3]:  # Top 3 des plus critiques
            reasons = failed[class_name]
            
            # Analyser les raisons d'échec
            for reason in reasons:
                if "E/L" in reason and ">" in reason:
                    # Recommandation pour réduire E/L
                    target_el = self.criteria[class_name].e_l_max
                    reduction_needed = ((ratio_el - target_el) / ratio_el) * 100
                    
                    recommendations.append({
                        "class": class_name,
                        "priority": "HIGH" if "XS" in class_name or "XD" in class_name else "MEDIUM",
                        "message": f"Réduire E/L de {reduction_needed:.1f}% pour atteindre {class_name}",
                        "action": "reduce_water_or_increase_binder",
                        "target": f"E/L ≤ {target_el}",
                        "current": f"{ratio_el:.3f}"
                    })
                
                elif "Résistance" in reason and "<" in reason:
                    # Recommandation pour augmenter résistance
                    target_fc = self.criteria[class_name].fc_min
                    increase_needed = target_fc - resistance
                    
                    recommendations.append({
                        "class": class_name,
                        "priority": "MEDIUM",
                        "message": f"Augmenter résistance de {increase_needed:.1f} MPa pour atteindre {class_name}",
                        "action": "increase_binder_or_reduce_w/c",
                        "target": f"Résistance ≥ {target_fc} MPa",
                        "current": f"{resistance:.1f} MPa"
                    })
                
                elif "Diffusion" in reason and ">" in reason:
                    # Recommandation pour améliorer résistance aux chlorures
                    recommendations.append({
                        "class": class_name,
                        "priority": "HIGH",
                        "message": f"Améliorer résistance aux chlorures - Ajouter laitier ou fumée de silice",
                        "action": "add_slag_or_silica_fume",
                        "details": "Laitier (20-30%) ou fumée de silice (5-10%) recommandé"
                    })
        
        return recommendations


# ═══════════════════════════════════════════════════════════════════════
# MOTEUR PROBABILISTE (POUR CONTRÔLE QUALITÉ)
# ═══════════════════════════════════════════════════════════════════════

class ProbabilisticEN206Engine(EN206ExposureEngine):
    """
    Extension du moteur avec approche probabiliste
    Prend en compte les incertitudes des mesures
    Utilisé pour contrôle qualité industriel
    """
    
    def determine_probabilistic(
        self,
        ratio_el_mean: float,
        ratio_el_std: float,
        resistance_mean: float,
        resistance_std: float,
        diffusion_cl_mean: Optional[float] = None,
        diffusion_cl_std: Optional[float] = None,
        carbonatation_mean: Optional[float] = None,
        carbonatation_std: Optional[float] = None,
        confidence_level: float = 0.95
    ) -> ProbabilisticExposureResult:
        """
        Détermination probabiliste des classes d'exposition
        
        Args:
            ratio_el_mean: Moyenne du rapport E/L
            ratio_el_std: Écart-type du rapport E/L
            resistance_mean: Moyenne de la résistance
            resistance_std: Écart-type de la résistance
            diffusion_cl_mean: Moyenne diffusion chlorures (optionnel)
            diffusion_cl_std: Écart-type diffusion chlorures (optionnel)
            carbonatation_mean: Moyenne carbonatation (optionnel)
            carbonatation_std: Écart-type carbonatation (optionnel)
            confidence_level: Niveau de confiance (défaut: 95%)
            
        Returns:
            ProbabilisticExposureResult avec probabilités
        """
        probabilities = {}
        confidence_intervals = {}
        
        # Calculer les bornes de l'intervalle de confiance
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        
        for class_name, criteria in self.criteria.items():
            # Probabilité de respecter le ratio E/L
            p_el = stats.norm.cdf(
                criteria.e_l_max,
                loc=ratio_el_mean,
                scale=ratio_el_std
            )
            
            # Probabilité de respecter la résistance minimale
            p_res = 1 - stats.norm.cdf(
                criteria.fc_min,
                loc=resistance_mean,
                scale=resistance_std
            )
            
            # Probabilité conjointe (indépendance supposée)
            p_total = p_el * p_res
            
            # Ajuster avec les autres critères si disponibles
            if criteria.diffusion_cl_max is not None and diffusion_cl_mean is not None and diffusion_cl_std is not None:
                p_diff = stats.norm.cdf(
                    criteria.diffusion_cl_max,
                    loc=diffusion_cl_mean,
                    scale=diffusion_cl_std
                )
                p_total *= p_diff
            
            if criteria.carbonatation_max is not None and carbonatation_mean is not None and carbonatation_std is not None:
                p_carb = stats.norm.cdf(
                    criteria.carbonatation_max,
                    loc=carbonatation_mean,
                    scale=carbonatation_std
                )
                p_total *= p_carb
            
            probabilities[class_name] = min(1.0, p_total)  # Limiter à 1.0
            
            # Calculer l'intervalle de confiance pour la classe gouvernante
            # (approximation simple)
            ci_lower = max(0, p_total - z_score * np.sqrt(p_total * (1 - p_total) / 30))
            ci_upper = min(1, p_total + z_score * np.sqrt(p_total * (1 - p_total) / 30))
            confidence_intervals[class_name] = (ci_lower, ci_upper)
        
        # Classes avec probabilité > 0.5 (seuil arbitraire)
        probable_classes = [c for c, p in probabilities.items() if p > 0.5]
        
        # Classe gouvernante (celle avec la plus haute probabilité parmi les sévères)
        governing = self._get_probabilistic_governing_class(probabilities)
        
        # Résultat déterministe pour la structure de base
        det_result = super().determine(
            ratio_el=ratio_el_mean,
            resistance=resistance_mean,
            diffusion_cl=diffusion_cl_mean,
            carbonatation=carbonatation_mean,
            air_content=None
        )
        
        return ProbabilisticExposureResult(
            classes=det_result.classes,
            governing_class=governing,
            satisfied_classes=det_result.satisfied_classes,
            failed_classes=det_result.failed_classes,
            recommendations=det_result.recommendations,
            probabilities=probabilities,
            confidence_level=confidence_level,
            confidence_intervals=confidence_intervals
        )
    
    def _get_probabilistic_governing_class(self, probabilities: Dict[str, float]) -> str:
        """
        Détermine la classe gouvernante en approche probabiliste
        Prend la classe la plus sévère avec probabilité > 0.5
        """
        for severe_class in self.SEVERITY_ORDER:
            if severe_class in probabilities and probabilities[severe_class] > 0.5:
                return severe_class
        
        # Sinon, prendre celle avec la plus haute probabilité
        if probabilities:
            return max(probabilities, key=probabilities.get)
        
        return "XC1"


# ═══════════════════════════════════════════════════════════════════════
# CONSEILLER POUR AMÉLIORATION
# ═══════════════════════════════════════════════════════════════════════

class ExposureAdvisor:
    """
    Conseiller intelligent pour atteindre des classes d'exposition cibles
    Utilise les données historiques et les règles métier
    """
    
    def __init__(self, engine: EN206ExposureEngine):
        """
        Initialise le conseiller avec un moteur EN 206
        
        Args:
            engine: Moteur EN 206 pour les calculs
        """
        self.engine = engine
        
        # Facteurs d'impact approximatifs
        self.IMPACT_FACTORS = {
            "Ciment": {"resistance": 0.15, "e_l": -0.02, "diffusion": -0.05},  # +10 kg → +1.5 MPa, -0.02 E/L
            "Laitier": {"resistance": 0.08, "diffusion": -0.15, "carbonatation": 0.10},  # +10 kg → +0.8 MPa, -15% diffusion
            "Eau": {"resistance": -0.30, "e_l": 0.10},  # +10 kg → -3 MPa, +0.1 E/L
            "Superplastifiant": {"resistance": 0.20, "e_l": -0.03}  # +1 kg → +0.2 MPa, -0.03 E/L
        }
    
    def recommend_for_target(
        self,
        composition: Dict[str, float],
        predictions: Dict[str, float],
        target_class: str,
        max_iterations: int = 5
    ) -> ExposureRecommendation:
        """
        Recommande des modifications pour atteindre une classe cible
        
        Args:
            composition: Composition actuelle (kg/m³)
            predictions: Prédictions actuelles
            target_class: Classe d'exposition cible
            max_iterations: Nombre max d'itérations d'optimisation
            
        Returns:
            ExposureRecommendation avec modifications suggérées
        """
        if target_class not in self.engine.criteria:
            raise ValueError(f"Classe cible {target_class} inconnue")
        
        # Résultat actuel
        current_result = self.engine.determine(
            ratio_el=predictions["Ratio_E_L"],
            resistance=predictions["Resistance"],
            diffusion_cl=predictions.get("Diffusion_Cl"),
            carbonatation=predictions.get("Carbonatation")
        )
        
        current_class = current_result.governing_class
        
        # Si déjà atteint
        if target_class in current_result.classes:
            return ExposureRecommendation(
                target_class=target_class,
                current_class=current_class,
                modifications={},
                priority="BASSE",
                reasoning=f"✅ La classe {target_class} est déjà satisfaite",
                estimated_impact={}
            )
        
        # Analyser les critères non satisfaits pour la classe cible
        criteria = self.engine.criteria[target_class]
        modifications = {}
        reasoning_lines = []
        
        # Vérifier E/L
        if predictions["Ratio_E_L"] > criteria.e_l_max:
            reduction_needed = predictions["Ratio_E_L"] - criteria.e_l_max
            # Stratégie: réduire eau OU augmenter liant
            if composition.get("Eau", 0) > 140:  # Si assez d'eau à réduire
                water_reduction = min(reduction_needed * 100, 20)  # Max 20 kg/m³
                modifications["Eau"] = -water_reduction
                reasoning_lines.append(
                    f"Réduire eau de {water_reduction:.0f} kg/m³ pour "
                    f"atteindre E/L ≤ {criteria.e_l_max}"
                )
            else:
                binder_increase = reduction_needed * 200  # Approximation
                modifications["Ciment"] = +binder_increase
                reasoning_lines.append(
                    f"Augmenter ciment de {binder_increase:.0f} kg/m³ pour "
                    f"atteindre E/L ≤ {criteria.e_l_max}"
                )
        
        # Vérifier résistance
        if predictions["Resistance"] < criteria.fc_min:
            increase_needed = criteria.fc_min - predictions["Resistance"]
            cement_increase = increase_needed / 0.15  # ~15 MPa pour 100 kg ciment
            modifications["Ciment"] = modifications.get("Ciment", 0) + cement_increase
            reasoning_lines.append(
                f"Augmenter ciment de {cement_increase:.0f} kg/m³ pour "
                f"atteindre résistance ≥ {criteria.fc_min} MPa"
            )
        
        # Vérifier diffusion chlorures (si applicable)
        if (criteria.diffusion_cl_max is not None and 
            predictions.get("Diffusion_Cl", 100) > criteria.diffusion_cl_max):
            
            if composition.get("Laitier", 0) < 150:
                slag_increase = 50  # Ajouter 50 kg/m³ de laitier
                modifications["Laitier"] = modifications.get("Laitier", 0) + slag_increase
                # Compenser avec réduction ciment pour garder liant constant
                modifications["Ciment"] = modifications.get("Ciment", 0) - 30
                reasoning_lines.append(
                    f"Ajouter {slag_increase:.0f} kg/m³ de laitier pour améliorer "
                    f"résistance aux chlorures"
                )
        
        # Calculer l'impact estimé
        estimated_impact = self._estimate_impact(composition, modifications, predictions)
        
        # Déterminer la priorité
        priority = self._determine_priority(target_class, current_class)
        
        reasoning = "\n".join(reasoning_lines) if reasoning_lines else (
            f"Optimisation pour atteindre {target_class}"
        )
        
        return ExposureRecommendation(
            target_class=target_class,
            current_class=current_class,
            modifications=modifications,
            priority=priority,
            reasoning=reasoning,
            estimated_impact=estimated_impact
        )
    
    def _estimate_impact(
        self,
        composition: Dict[str, float],
        modifications: Dict[str, float],
        predictions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Estime l'impact des modifications sur les propriétés
        """
        impact = {
            "Ratio_E_L": predictions["Ratio_E_L"],
            "Resistance": predictions["Resistance"],
            "Diffusion_Cl": predictions.get("Diffusion_Cl", 0),
            "Carbonatation": predictions.get("Carbonatation", 0)
        }
        
        # Appliquer les facteurs d'impact
        for comp, delta in modifications.items():
            if comp in self.IMPACT_FACTORS:
                factors = self.IMPACT_FACTORS[comp]
                for prop, factor in factors.items():
                    if prop == "e_l" and "Ratio_E_L" in impact:
                        impact["Ratio_E_L"] += delta * factor / 100  # Conversion
                    elif prop == "resistance" and "Resistance" in impact:
                        impact["Resistance"] += delta * factor
                    elif prop == "diffusion" and "Diffusion_Cl" in impact:
                        impact["Diffusion_Cl"] *= (1 + delta * factor / 100)
                    elif prop == "carbonatation" and "Carbonatation" in impact:
                        impact["Carbonatation"] *= (1 + delta * factor / 100)
        
        return impact
    
    def _determine_priority(self, target_class: str, current_class: str) -> str:
        """
        Détermine la priorité d'action
        """
        # Classes critiques
        critical_classes = ["XS3", "XS2", "XD3", "XF4"]
        high_classes = ["XS1", "XD2", "XF3", "XA3"]
        
        if target_class in critical_classes:
            return "HAUTE"
        elif target_class in high_classes:
            return "MOYENNE"
        else:
            return "BASSE"


# ═══════════════════════════════════════════════════════════════════════
# MOTEUR INDUSTRIEL COMPLET
# ═══════════════════════════════════════════════════════════════════════

class IndustrialEN206Engine:
    """
    Moteur EN 206 version industrielle complète
    Intègre les approches déterministe, probabiliste et recommandations
    
    Usage:
        engine = IndustrialEN206Engine()
        
        # Mode déterministe
        result = engine.determine(ratio_el=0.45, resistance=40)
        
        # Mode probabiliste (contrôle qualité)
        prob_result = engine.determine_probabilistic(
            ratio_el_mean=0.45, ratio_el_std=0.02,
            resistance_mean=40, resistance_std=3
        )
        
        # Recommandations
        advice = engine.recommend(composition, predictions, target_class="XS3")
    """
    
    def __init__(self, use_probabilistic: bool = False):
        """
        Initialise le moteur industriel
        
        Args:
            use_probabilistic: Utiliser l'approche probabiliste par défaut
        """
        self.deterministic = EN206ExposureEngine()
        self.probabilistic = ProbabilisticEN206Engine()
        self.advisor = ExposureAdvisor(self.deterministic)
        self.use_probabilistic = use_probabilistic
    
    def determine(
        self,
        ratio_el: float,
        resistance: float,
        diffusion_cl: Optional[float] = None,
        carbonatation: Optional[float] = None,
        air_content: Optional[float] = None,
        **kwargs
    ) -> ExposureResult:
        """
        Détermination des classes d'exposition (mode déterministe)
        """
        return self.deterministic.determine(
            ratio_el=ratio_el,
            resistance=resistance,
            diffusion_cl=diffusion_cl,
            carbonatation=carbonatation,
            air_content=air_content
        )
    
    def determine_probabilistic(
        self,
        ratio_el_mean: float,
        ratio_el_std: float,
        resistance_mean: float,
        resistance_std: float,
        diffusion_cl_mean: Optional[float] = None,
        diffusion_cl_std: Optional[float] = None,
        carbonatation_mean: Optional[float] = None,
        carbonatation_std: Optional[float] = None,
        confidence_level: float = 0.95
    ) -> ProbabilisticExposureResult:
        """
        Détermination probabiliste avec incertitudes
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
            confidence_level=confidence_level
        )
    
    def recommend(
        self,
        composition: Dict[str, float],
        predictions: Dict[str, float],
        target_class: str
    ) -> ExposureRecommendation:
        """
        Génère des recommandations pour atteindre une classe cible
        """
        return self.advisor.recommend_for_target(
            composition=composition,
            predictions=predictions,
            target_class=target_class
        )
    
    def analyze(
        self,
        composition: Dict[str, float],
        predictions: Dict[str, float]
    ) -> Dict:
        """
        Analyse complète: détermination + recommandations
        """
        # Détermination
        result = self.determine(
            ratio_el=predictions["Ratio_E_L"],
            resistance=predictions["Resistance"],
            diffusion_cl=predictions.get("Diffusion_Cl"),
            carbonatation=predictions.get("Carbonatation")
        )
        
        # Recommandations pour la classe supérieure
        recommendations = []
        severe_classes = ["XS3", "XS2", "XD3", "XF4", "XC4"]
        
        for target in severe_classes:
            if target not in result.classes:
                try:
                    rec = self.recommend(composition, predictions, target)
                    recommendations.append(rec.to_dict())
                except:
                    pass
        
        return {
            "current": result.to_dict(),
            "recommendations": recommendations[:3],  # Top 3
            "summary": result.get_summary()
        }


# ═══════════════════════════════════════════════════════════════════════
# FONCTION DE COMPATIBILITÉ POUR L'ANCIENNE VERSION
# ═══════════════════════════════════════════════════════════════════════

def get_exposure_engine(version: str = "industrial") -> IndustrialEN206Engine:
    """
    Factory function pour obtenir le moteur d'exposition
    
    Args:
        version: "simple", "probabilistic", ou "industrial"
        
    Returns:
        Moteur d'exposition approprié
    """
    if version == "simple":
        # Pour compatibilité avec l'ancien code
        class SimpleWrapper:
            def determine(self, ratio_el, resistance, diffusion_cl, carbonatation):
                engine = EN206ExposureEngine()
                result = engine.determine(
                    ratio_el=ratio_el,
                    resistance=resistance,
                    diffusion_cl=diffusion_cl,
                    carbonatation=carbonatation
                )
                return result
        return SimpleWrapper()
    
    elif version == "probabilistic":
        return ProbabilisticEN206Engine()
    
    else:  # industrial
        return IndustrialEN206Engine()


# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    # Classes principales
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
    
    # Fonctions utilitaires
    "get_exposure_engine"
]