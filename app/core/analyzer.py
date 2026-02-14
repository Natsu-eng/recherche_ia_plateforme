"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/analyzer.py - VERSION CORRIGÉE
Auteur: Stage R&D - IMT Nord Europe
Fonction: Analyses Statistiques Avancées pour Formulations Béton
Version: 2.1.0 - Compatible avec predictor.py
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT CORRIGÉ : Import de la fonction de prédiction standard
# ═══════════════════════════════════════════════════════════════════════════════
from app.core.predictor import predict_concrete_properties

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SensitivityResult:
    """Résultat d'une analyse de sensibilité."""
    
    parameter_name: str
    """Nom du paramètre varié"""
    
    baseline_value: float
    """Valeur de référence"""
    
    variation_range: Tuple[float, float]
    """Plage de variation testée (min, max)"""
    
    impacts: Dict[str, List[float]]
    """Impact sur chaque cible {cible: [valeurs]}"""
    
    elasticities: Dict[str, float]
    """Élasticités calculées {cible: élasticité}"""


@dataclass
class CorrelationAnalysis:
    """Résultat d'une analyse de corrélation."""
    
    correlation_matrix: pd.DataFrame
    """Matrice de corrélation"""
    
    significant_pairs: List[Tuple[str, str, float]]
    """Paires significativement corrélées (var1, var2, r)"""
    
    vif_scores: Dict[str, float]
    """Variance Inflation Factor (multicolinéarité)"""


@dataclass
class ConfidenceInterval:
    """Intervalle de confiance d'une prédiction."""
    
    mean: float
    """Valeur moyenne prédite"""
    
    lower_bound: float
    """Borne inférieure (percentile 2.5%)"""
    
    upper_bound: float
    """Borne supérieure (percentile 97.5%)"""
    
    confidence_level: float = 0.95
    """Niveau de confiance (défaut 95%)"""


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class ConcreteAnalyzer:
    """
    Analyseur statistique avancé pour formulations béton.
    
    Fournit des méthodes pour comprendre l'influence des paramètres,
    détecter les corrélations, et quantifier l'incertitude des prédictions.
    """
    
    def __init__(self):
        """Initialise l'analyseur."""
        self.scaler = StandardScaler()
    
    # ───────────────────────────────────────────────────────────────────
    # ANALYSE DE SENSIBILITÉ (CORRIGÉE)
    # ───────────────────────────────────────────────────────────────────
    
    def sensitivity_analysis(
        self,
        baseline_formulation: Dict[str, float],
        parameter: str,
        feature_list: List[str],  # AJOUTÉ : Liste des features pour alignement
        predictor: Any,             # AJOUTÉ : Le modèle ML
        variation_percent: float = 20.0,
        n_points: int = 20
    ) -> SensitivityResult:
        """
        Analyse l'impact de la variation d'un paramètre sur les cibles.
        
        Args:
            baseline_formulation: Formulation de référence
            parameter: Nom du paramètre à faire varier (ex: "Ciment")
            feature_list: Liste ordonnée des features (pour predictor.py)
            predictor: Instance du modèle ML
            variation_percent: % de variation autour de la baseline
            n_points: Nombre de points de test
        
        Returns:
            SensitivityResult avec impacts détaillés
        """
        if parameter not in baseline_formulation:
            raise ValueError(f"Paramètre '{parameter}' absent de la formulation")
        
        baseline_value = baseline_formulation[parameter]
        
        # Définir la plage de variation
        delta = baseline_value * (variation_percent / 100)
        min_value = max(0, baseline_value - delta)
        max_value = baseline_value + delta
        
        # Générer les valeurs de test
        test_values = np.linspace(min_value, max_value, n_points)
        
        # Stocker les impacts sur chaque cible
        impacts = {
            "Resistance": [],
            "Diffusion_Cl": [],
            "Carbonatation": []
        }
        
        # Simulation : variation du paramètre
        for value in test_values:
            # Créer formulation modifiée
            modified_formulation = baseline_formulation.copy()
            modified_formulation[parameter] = value
            
            # PRÉDICTION CORRIGÉE : Utilisation de la fonction standard
            if predictor is not None:
                try:
                    predictions = predict_concrete_properties(
                        composition=modified_formulation,
                        model=predictor,
                        feature_list=feature_list
                    )
                    # Extraction des valeurs
                    impacts["Resistance"].append(predictions["Resistance"])
                    impacts["Diffusion_Cl"].append(predictions["Diffusion_Cl"])
                    impacts["Carbonatation"].append(predictions["Carbonatation"])
                except Exception as e:
                    logger.error(f"Erreur prédiction sensibilité: {e}")
                    # Valeurs par défaut en cas d'erreur
                    impacts["Resistance"].append(30)
                    impacts["Diffusion_Cl"].append(10)
                    impacts["Carbonatation"].append(15)
            else:
                # Mode simulation (sans modèle réel)
                if parameter == "Ciment":
                    impacts["Resistance"].append(25 + value * 0.05)
                elif parameter == "Eau":
                    impacts["Resistance"].append(40 - value * 0.05)
                else:
                    impacts["Resistance"].append(30)
                impacts["Diffusion_Cl"].append(10)
                impacts["Carbonatation"].append(15)
        
        # Calculer les élasticités (sensibilité relative)
        elasticities = self._calculate_elasticity(
            test_values,
            impacts,
            baseline_value
        )
        
        logger.info(
            f"Analyse sensibilité {parameter} : "
            f"Élasticité Résistance = {elasticities.get('Resistance', 0):.3f}"
        )
        
        return SensitivityResult(
            parameter_name=parameter,
            baseline_value=baseline_value,
            variation_range=(min_value, max_value),
            impacts=impacts,
            elasticities=elasticities
        )
    
    def _calculate_elasticity(
        self,
        param_values: np.ndarray,
        impacts: Dict[str, List[float]],
        baseline_param: float
    ) -> Dict[str, float]:
        """Calcule l'élasticité : (ΔY/Y) / (ΔX/X)"""
        elasticities = {}
        
        for target_name, target_values in impacts.items():
            slope, _, _, _, _ = stats.linregress(param_values, target_values)
            
            # Élasticité au point baseline
            baseline_idx = len(param_values) // 2
            baseline_target = target_values[baseline_idx]
            
            if baseline_target != 0 and baseline_param != 0:
                elasticity = slope * (baseline_param / baseline_target)
            else:
                elasticity = 0.0
            
            elasticities[target_name] = elasticity
        
        return elasticities
    
    # ───────────────────────────────────────────────────────────────────
    # INTERVALLES DE CONFIANCE (CORRIGÉ)
    # ───────────────────────────────────────────────────────────────────
    
    def confidence_interval(
        self,
        formulation: Dict[str, float],
        feature_list: List[str],  # AJOUTÉ
        predictor: Any,             # AJOUTÉ
        n_bootstrap: int = 100,
        confidence_level: float = 0.95
    ) -> Dict[str, ConfidenceInterval]:
        """
        Calcule les intervalles de confiance des prédictions par bootstrap.
        
        Args:
            formulation: Composition béton
            feature_list: Liste des features
            predictor: Modèle de prédiction
            n_bootstrap: Nombre d'échantillons bootstrap
            confidence_level: Niveau de confiance
        
        Returns:
            {cible: ConfidenceInterval}
        """
        if predictor is None:
            raise RuntimeError("Modèle requis pour calculer les intervalles de confiance")
        
        # Prédiction de référence
        baseline_pred = predict_concrete_properties(
            composition=formulation,
            model=predictor,
            feature_list=feature_list
        )
        
        # Générer des variantes par perturbation
        bootstrap_predictions = {
            target: [] for target in ["Resistance", "Diffusion_Cl", "Carbonatation"]
        }
        
        for _ in range(n_bootstrap):
            # Perturbation aléatoire (±5% de bruit gaussien)
            perturbed = {
                key: max(0, value * np.random.normal(1.0, 0.05))
                for key, value in formulation.items()
            }
            
            # PRÉDICTION CORRIGÉE
            try:
                pred = predict_concrete_properties(
                    composition=perturbed,
                    model=predictor,
                    feature_list=feature_list
                )
                
                # Stockage des résultats
                if "Resistance" in pred:
                    bootstrap_predictions["Resistance"].append(pred["Resistance"])
                if "Diffusion_Cl" in pred:
                    bootstrap_predictions["Diffusion_Cl"].append(pred["Diffusion_Cl"])
                if "Carbonatation" in pred:
                    bootstrap_predictions["Carbonatation"].append(pred["Carbonatation"])
                    
            except Exception as e:
                logger.warning(f"Erreur bootstrap itération: {e}")
                continue
        
        # Calcul des intervalles
        alpha = 1 - confidence_level
        intervals = {}
        
        for target, values in bootstrap_predictions.items():
            if not values:
                continue # Skip si pas de données
                
            values_array = np.array(values)
            
            intervals[target] = ConfidenceInterval(
                mean=np.mean(values_array),
                lower_bound=np.percentile(values_array, alpha/2 * 100),
                upper_bound=np.percentile(values_array, (1 - alpha/2) * 100),
                confidence_level=confidence_level
            )
        
        logger.info(
            f"Intervalles confiance calculés : {len(intervals)} cibles"
        )
        
        return intervals
    
    # ───────────────────────────────────────────────────────────────────
    # ANALYSE COMPARATIVE (CORRIGÉE)
    # ───────────────────────────────────────────────────────────────────
    
    def compare_formulations(
        self,
        formulations: List[Dict[str, float]],
        names: List[str],
        feature_list: List[str],  # AJOUTÉ
        predictor: Any             # AJOUTÉ
    ) -> pd.DataFrame:
        """
        Compare plusieurs formulations côte à côte.
        """
        if len(formulations) != len(names):
            raise ValueError("Nombre de formulations ≠ nombre de noms")
        
        results = []
        
        for i, (formulation, name) in enumerate(zip(formulations, names)):
            # PRÉDICTION CORRIGÉE
            if predictor:
                try:
                    pred = predict_concrete_properties(
                        composition=formulation,
                        model=predictor,
                        feature_list=feature_list
                    )
                    
                    # Compilation résultats
                    result = {
                        "Nom": name,
                        **formulation, # On ajoute toute la composition
                        **pred      # On ajoute les prédictions
                    }
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Erreur prédiction formulation {name}: {e}")
            else:
                # Mode simulation (test sans modèle)
                result = {
                    "Nom": name,
                    **formulation,
                    "Resistance": 30.0,
                    "Diffusion_Cl": 10.0,
                    "Carbonatation": 15.0,
                    "Ratio_E_L": formulation["Eau"] / (
                        formulation["Ciment"] + formulation.get("Laitier", 0) + 1e-5
                    ),
                    "Liant_Total": (
                        formulation["Ciment"] + 
                        formulation.get("Laitier", 0) + 
                        formulation.get("CendresVolantes", 0)
                    )
                }
                results.append(result)
        
        logger.info(f"Comparaison de {len(results)} formulations")
        
        return pd.DataFrame(results)
    
    # ───────────────────────────────────────────────────────────────────
    # AUTRES MÉTHODES (Inchangées, fournies pour complétude)
    # ───────────────────────────────────────────────────────────────────
    
    def correlation_analysis(
        self,
        data: pd.DataFrame,
        threshold: float = 0.7
    ) -> CorrelationAnalysis:
        """Analyse les corrélations entre variables."""
        corr_matrix = data.corr()
        significant_pairs = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                var1 = corr_matrix.columns[i]
                var2 = corr_matrix.columns[j]
                r = corr_matrix.iloc[i, j]
                
                if abs(r) >= threshold:
                    significant_pairs.append((var1, var2, r))
        
        significant_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        vif_scores = self._calculate_vif(data)
        
        return CorrelationAnalysis(
            correlation_matrix=corr_matrix,
            significant_pairs=significant_pairs,
            vif_scores=vif_scores
        )
    
    def _calculate_vif(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calcule le VIF pour détecter la multicolinéarité."""
        from sklearn.linear_model import LinearRegression
        vif_scores = {}
        
        for i, col in enumerate(data.columns):
            X = data.drop(columns=[col]).values
            y = data[col].values
            
            model = LinearRegression()
            model.fit(X, y)
            r_squared = model.score(X, y)
            
            if r_squared < 0.9999:
                vif = 1 / (1 - r_squared)
            else:
                vif = float('inf')
            
            vif_scores[col] = vif
        
        return vif_scores
    
    def detect_outliers(
        self,
        data: pd.DataFrame,
        method: str = "zscore",
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """Détecte les formulations aberrantes."""
        result = data.copy()
        result["is_outlier"] = False
        
        if method == "zscore":
            z_scores = np.abs(stats.zscore(data.select_dtypes(include=[np.number])))
            outlier_mask = (z_scores > threshold).any(axis=1)
            result["is_outlier"] = outlier_mask
        elif method == "iqr":
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            
            outlier_mask = (
                (data < (Q1 - 1.5 * IQR)) | 
                (data > (Q3 + 1.5 * IQR))
            ).any(axis=1)
            result["is_outlier"] = outlier_mask
        
        n_outliers = result["is_outlier"].sum()
        logger.info(f"Détection outliers : {n_outliers} détectés")
        
        return result
    
    def performance_score(
        self,
        predictions: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calcule un score de performance global multi-critères."""
        if weights is None:
            weights = {
                "Resistance": 0.40,
                "Diffusion_Cl": 0.30,
                "Carbonatation": 0.30
            }
        
        # Normalisation (0-100)
        normalized = {}
        
        # Résistance
        res = predictions["Resistance"]
        normalized["Resistance"] = np.clip((res - 10) / (60 - 10) * 100, 0, 100)
        
        # Diffusion Cl
        diff_cl = predictions["Diffusion_Cl"]
        normalized["Diffusion_Cl"] = np.clip((20 - diff_cl) / (20 - 2) * 100, 0, 100)
        
        # Carbonatation
        carb = predictions["Carbonatation"]
        normalized["Carbonatation"] = np.clip((40 - carb) / (40 - 5) * 100, 0, 100)
        
        # Score pondéré
        score = sum(
            normalized[key] * weights[key]
            for key in weights.keys()
        )
        
        return round(score, 1)
    
    def robustness_analysis(
        self,
        formulation: Dict[str, float],
        feature_list: List[str],  # AJOUTÉ
        predictor: Any,             # AJOUTÉ
        n_simulations: int = 50
    ) -> Dict[str, float]:
        """Analyse la robustesse de la formulation."""
        results = {
            "Resistance": [],
            "Diffusion_Cl": [],
            "Carbonatation": []
        }
        
        for _ in range(n_simulations):
            # Perturbation ±3%
            perturbed = {
                key: max(0, value * np.random.uniform(0.97, 1.03))
                for key, value in formulation.items()
            }
            
            # PRÉDICTION CORRIGÉE
            try:
                pred = predict_concrete_properties(
                    composition=perturbed,
                    model=predictor,
                    feature_list=feature_list
                )
                
                results["Resistance"].append(pred["Resistance"])
                results["Diffusion_Cl"].append(pred["Diffusion_Cl"])
                results["Carbonatation"].append(pred["Carbonatation"])
            except Exception:
                continue
        
        # Calcul coefficients de variation (CV)
        cv_resistance = (
            np.std(results["Resistance"]) / 
            (np.mean(results["Resistance"]) + 1e-10) * 100
        )
        cv_diffusion = (
            np.std(results["Diffusion_Cl"]) / 
            (np.mean(results["Diffusion_Cl"]) + 1e-10) * 100
        )
        cv_carbonatation = (
            np.std(results["Carbonatation"]) / 
            (np.mean(results["Carbonatation"]) + 1e-10) * 100
        )
        
        # Score de fiabilité
        mean_cv = (cv_resistance + cv_diffusion + cv_carbonatation) / 3
        reliability_score = max(0, 100 - mean_cv * 10)
        
        logger.info(
            f"Analyse robustesse : Score fiabilité = {reliability_score:.1f}/100"
        )
        
        return {
            "cv_resistance": round(cv_resistance, 2),
            "cv_diffusion_cl": round(cv_diffusion, 2),
            "cv_carbonatation": round(cv_carbonatation, 2),
            "reliability_score": round(reliability_score, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═════════════════════════════════════════════════════════════════════════════

def quick_sensitivity(
    baseline: Dict[str, float],
    parameter: str,
    feature_list: List[str], # AJOUTÉ
    predictor: Any              # AJOUTÉ
) -> SensitivityResult:
    """
    Analyse rapide de sensibilité (version simplifiée).
    """
    analyzer = ConcreteAnalyzer()
    return analyzer.sensitivity_analysis(
        baseline_formulation=baseline,
        parameter=parameter,
        feature_list=feature_list,
        predictor=predictor,
        variation_percent=20,
        n_points=15
    )


def format_sensitivity_report(result: SensitivityResult) -> str:
    """Formate un rapport de sensibilité en Markdown."""
    lines = []
    lines.append(f"# 📊 ANALYSE DE SENSIBILITÉ : {result.parameter_name}")
    lines.append("")
    lines.append(f"**Valeur baseline :** {result.baseline_value:.2f}")
    lines.append(f"**Plage testée :** {result.variation_range[0]:.1f} - {result.variation_range[1]:.1f}")
    lines.append("")
    
    lines.append("## 🎯 Élasticités")
    for target, elasticity in result.elasticities.items():
        interpretation = ""
        if abs(elasticity) > 1:
            interpretation = "(Très sensible)"
        elif abs(elasticity) > 0.5:
            interpretation = "(Sensible)"
        else:
            interpretation = "(Peu sensible)"
        
        lines.append(f"- **{target}** : {elasticity:.3f} {interpretation}")
    
    lines.append("")
    lines.append("### 📖 Interprétation")
    lines.append(
        "Élasticité = variation relative de la sortie / variation relative de l'entrée"
    )
    lines.append(
        "Ex : Élasticité = 0.8 → +10% du paramètre → +8% de la cible"
    )
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ConcreteAnalyzer",
    "SensitivityResult",
    "CorrelationAnalysis",
    "ConfidenceInterval",
    "quick_sensitivity",
    "format_sensitivity_report"
]