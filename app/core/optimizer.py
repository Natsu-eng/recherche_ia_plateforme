"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/optimizer.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Optimisation Génétique des Formulations Béton
Version: 1.0.0 - Refactorisé & Production Ready
═══════════════════════════════════════════════════════════════════════════════

CHANGELOG v1.0.0 (refactoring depuis version précédente):
  ✅ Validation désactivée uniquement pendant l'évaluation (performance)
  ✅ Validation finale robuste avec fallback explicite
  ✅ Contrainte classe d'exposition isolée dans _check_exposure_constraint()
  ✅ Logs structurés avec métriques de convergence
  ✅ Typing strict (Python 3.10+)
  ✅ Docstrings complètes sur toutes les fonctions

Algorithme : Algorithme Génétique (AG)
  - Sélection : Tournoi
  - Croisement : Arithmétique (α aléatoire par gène)
  - Mutation : Gaussienne (5 % de la plage par gène)
  - Élitisme : Conservation des N meilleurs individus

Objectifs supportés :
  - "minimize_cost" : Minimiser le coût matériaux (€/m³)
  - "minimize_co2"  : Minimiser l'empreinte carbone (kg CO₂/m³)

Contraintes :
  - Résistance ≥ target_strength (MPa)
  - Classe d'exposition EN 206 (E/L ≤ E/L_max + fc ≥ fc_min de la classe)
  - Bornes physiques par constituant (BOUNDS dans config/constants.py)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple

import numpy as np

from config.constants import (
    BOUNDS,
    CO2_EMISSIONS_KG,
    EXPOSURE_CLASSES,
    MATERIALS_COST_EURO_KG,
)
from config.settings import OPTIMIZER_SETTINGS
from app.core.predictor import predict_concrete_properties

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPES & CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

#: Type union pour les objectifs d'optimisation supportés
Objective = Literal["minimize_cost", "minimize_co2"]

#: Score de pénalité pour un individu non-viable (hors contraintes)
_INFEASIBLE_SCORE: float = -1e9


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OptimizationResult:
    """
    Résultat de l'optimisation génétique.

    Attributs:
        mix            : Composition optimale (kg/m³), clés = noms constituants
        targets        : Propriétés prédites pour la composition optimale
        cost           : Coût matériaux estimé (€/m³)
        co2            : Empreinte carbone estimée (kg CO₂/m³)
        target_strength: Résistance minimale exigée (MPa)
        objective      : Objectif d'optimisation utilisé
        generations    : Nombre de générations exécutées
        required_class : Classe d'exposition contrainte (si spécifiée)
        achieved_class : Classe d'exposition atteinte par la solution
    """

    mix:             Dict[str, float]
    targets:         Dict[str, float]
    cost:            float
    co2:             float
    target_strength: float
    objective:       Objective
    generations:     int
    required_class:  Optional[str] = None
    achieved_class:  Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULS ÉCONOMIQUES & ENVIRONNEMENTAUX
# ═══════════════════════════════════════════════════════════════════════════════

def compute_cost(mix: Dict[str, float]) -> float:
    """
    Calcule le coût total des matériaux (€/m³).

    Utilise les prix unitaires définis dans MATERIALS_COST_EURO_KG.
    Les constituants absents du dictionnaire de prix sont ignorés (coût 0).

    Args:
        mix: Composition béton (kg/m³)

    Returns:
        Coût total en €/m³
    """
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(price)
            for name, price in MATERIALS_COST_EURO_KG.items()
        )
    )


def compute_co2(mix: Dict[str, float]) -> float:
    """
    Calcule l'empreinte carbone totale (kg CO₂/m³).

    Utilise les facteurs d'émission définis dans CO2_EMISSIONS_KG.
    Les constituants absents du dictionnaire sont ignorés.

    Args:
        mix: Composition béton (kg/m³)

    Returns:
        Empreinte carbone en kg CO₂/m³
    """
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(factor)
            for name, factor in CO2_EMISSIONS_KG.items()
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DE COMPOSITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def sample_random_mix(rng: np.random.RandomState) -> Dict[str, float]:
    """
    Génère une composition aléatoire uniforme dans les bornes physiques.

    Chaque constituant est tiré uniformément dans [BOUNDS[name]["min"], BOUNDS[name]["max"]].

    Args:
        rng: Générateur de nombres aléatoires (reproductibilité via random_state)

    Returns:
        Composition béton (kg/m³) respectant les bornes physiques
    """
    return {
        name: float(rng.uniform(
            low=float(bounds["min"]),
            high=float(bounds["max"]),
        ))
        for name, bounds in BOUNDS.items()
    }


# ═══════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION DES CONTRAINTES
# ═══════════════════════════════════════════════════════════════════════════════

def _check_exposure_constraint(
    preds:          Dict[str, float],
    required_class: Optional[str],
) -> bool:
    """
    Vérifie que les prédictions satisfont la classe d'exposition exigée.

    Critères vérifiés (EN 206 — Tableau 4) :
      - E/L ≤ E/L_max de la classe
      - Résistance ≥ fc_min de la classe

    Retourne True (pas de contrainte) si required_class est None
    ou si la classe n'est pas dans EXPOSURE_CLASSES.

    Args:
        preds         : Propriétés prédites (doit contenir Ratio_E_L, Resistance)
        required_class: Code classe EN 206 (ex: "XD2") ou None

    Returns:
        True si la contrainte est satisfaite (ou absente), False sinon
    """
    if not required_class or required_class not in EXPOSURE_CLASSES:
        return True  # Pas de contrainte à vérifier

    specs     = EXPOSURE_CLASSES[required_class]
    ratio_el  = float(preds["Ratio_E_L"])
    resistance = float(preds["Resistance"])

    if ratio_el > specs["E_L_max"]:
        return False

    if resistance < specs["fc_min"]:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# ÉVALUATION D'UN INDIVIDU
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_mix(
    model:          Any,
    feature_list:   list[str],
    mix:            Dict[str, float],
    target_strength: float,
    required_class:  Optional[str],
    objective:       Objective,
) -> Tuple[float, Dict[str, float], float, float]:
    """
    Évalue un individu (composition béton) dans l'algorithme génétique.

    La validation Streamlit est désactivée (validate=False) pour la performance
    lors de l'évaluation de milliers d'individus. Une validation complète
    est effectuée uniquement sur la solution finale.

    Contraintes vérifiées :
      1. Résistance ≥ target_strength  (contrainte dure)
      2. Classe d'exposition EN 206    (si required_class fourni)

    Score (à maximiser) selon l'objectif :
      - "minimize_cost" → score = -coût   (minimiser coût = maximiser -coût)
      - "minimize_co2"  → score = -co2    (minimiser CO₂  = maximiser -co2)

    Args:
        model          : Modèle ML chargé
        feature_list   : Liste ordonnée des features attendues par le modèle
        mix            : Composition béton à évaluer (kg/m³)
        target_strength: Résistance minimale requise (MPa)
        required_class : Classe d'exposition EN 206 exigée (ou None)
        objective      : Critère d'optimisation

    Returns:
        Tuple (score, predictions, coût, co2)
        score = _INFEASIBLE_SCORE si la composition viole une contrainte
    """
    # Prédiction ML (sans validation Streamlit — performance)
    preds = predict_concrete_properties(
        composition=mix,
        model=model,
        feature_list=feature_list,
        validate=False,
    )

    strength = float(preds["Resistance"])

    # ── Contrainte 1 : Résistance minimale ─────────────────────────────────
    if strength < target_strength:
        return _INFEASIBLE_SCORE, preds, 0.0, 0.0

    # ── Contrainte 2 : Classe d'exposition ─────────────────────────────────
    if not _check_exposure_constraint(preds, required_class):
        return _INFEASIBLE_SCORE, preds, 0.0, 0.0

    # ── Calcul du score selon l'objectif ───────────────────────────────────
    cost = compute_cost(mix)
    co2  = compute_co2(mix)

    if objective == "minimize_cost":
        score = -cost
    elif objective == "minimize_co2":
        score = -co2
    else:
        # Fallback : maximiser la résistance
        score = strength

    return score, preds, cost, co2


# ═══════════════════════════════════════════════════════════════════════════════
# OPÉRATEURS GÉNÉTIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def _crossover(
    parent1: Dict[str, float],
    parent2: Dict[str, float],
    rng:     np.random.RandomState,
) -> Dict[str, float]:
    """
    Croisement arithmétique entre deux parents.

    Pour chaque gène (constituant), l'enfant reçoit une combinaison linéaire :
        enfant[k] = α × parent1[k] + (1-α) × parent2[k]
    où α ∈ [0, 1] est tiré aléatoirement par gène.

    Args:
        parent1: Composition du parent 1 (kg/m³)
        parent2: Composition du parent 2 (kg/m³)
        rng    : Générateur aléatoire

    Returns:
        Composition enfant (kg/m³)
    """
    child: Dict[str, float] = {}
    for key in BOUNDS:
        alpha    = float(rng.rand())
        child[key] = alpha * parent1[key] + (1.0 - alpha) * parent2[key]
    return child


def _mutate(
    mix:           Dict[str, float],
    mutation_rate: float,
    rng:           np.random.RandomState,
) -> Dict[str, float]:
    """
    Mutation gaussienne d'une composition béton.

    Chaque gène est muté avec probabilité `mutation_rate`.
    Le bruit gaussien a un écart-type de 5 % de la plage du paramètre.
    Le résultat est clampé dans les bornes physiques.

    Args:
        mix          : Composition à muter (kg/m³)
        mutation_rate: Probabilité de mutation par gène (0–1)
        rng          : Générateur aléatoire

    Returns:
        Composition mutée (kg/m³), bornée dans BOUNDS
    """
    mutated = mix.copy()
    for key, bounds in BOUNDS.items():
        if rng.rand() < mutation_rate:
            span          = float(bounds["max"]) - float(bounds["min"])
            noise         = float(rng.normal(scale=0.05 * span))
            mutated[key]  = float(np.clip(
                mutated[key] + noise,
                float(bounds["min"]),
                float(bounds["max"]),
            ))
    return mutated


def _tournament_select(
    population: list[Dict[str, float]],
    fitness:    np.ndarray,
    size:       int,
    rng:        np.random.RandomState,
) -> Dict[str, float]:
    """
    Sélection par tournoi.

    Tire `size` individus aléatoirement et retourne le meilleur.

    Args:
        population: Liste des compositions
        fitness   : Tableau de scores correspondants
        size      : Taille du tournoi
        rng       : Générateur aléatoire

    Returns:
        Composition gagnante du tournoi
    """
    pop_size = len(population)
    idxs     = rng.randint(0, pop_size, size=size)
    best_idx = int(idxs[np.argmax(fitness[idxs])])
    return population[best_idx]


# ═══════════════════════════════════════════════════════════════════════════════
# ALGORITHME GÉNÉTIQUE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def optimize_mix(
    model:           Any,
    feature_list:    list[str],
    target_strength: float,
    required_class:  Optional[str] = None,
    objective:       Objective = "minimize_cost",
    random_state:    Optional[int] = None,
) -> Optional[OptimizationResult]:
    """
    Optimise une formulation béton par algorithme génétique.

    L'algorithme cherche la composition minimisant le coût ou le CO₂
    tout en satisfaisant les contraintes de résistance et de classe d'exposition.

    Pipeline :
      1. Génération de la population initiale aléatoire
      2. Pour chaque génération :
         a. Évaluation de tous les individus
         b. Mise à jour du meilleur individu global
         c. Sélection par tournoi + croisement arithmétique + mutation gaussienne
         d. Élitisme : conservation des N meilleurs individus
      3. Validation complète (validate=True) sur la solution finale

    Configuration (OPTIMIZER_SETTINGS["genetic_algorithm"]) :
      - population_size : Taille de la population (défaut 80)
      - num_generations : Nombre de générations (défaut 40)
      - mutation_rate   : Probabilité de mutation par gène (défaut 0.1)
      - crossover_rate  : Probabilité de croisement (défaut 0.8)
      - elite_size      : Nombre d'élites conservés (défaut 10)
      - tournament_size : Taille du tournoi de sélection (défaut 5)

    Args:
        model           : Modèle ML de prédiction des propriétés béton
        feature_list    : Liste ordonnée des features du modèle
        target_strength : Résistance minimale requise (MPa)
        required_class  : Classe d'exposition EN 206 exigée (ex: "XD2"), ou None
        objective       : Critère d'optimisation ("minimize_cost" ou "minimize_co2")
        random_state    : Graine aléatoire pour reproductibilité (None = non fixée)

    Returns:
        OptimizationResult avec la meilleure composition trouvée,
        ou None si aucune composition viable n'a été trouvée.
    """
    # ── Paramètres de l'algorithme (depuis config) ──────────────────────────
    algo_cfg       = OPTIMIZER_SETTINGS.get("genetic_algorithm", {})
    pop_size       = int(algo_cfg.get("population_size", 80))
    n_gen          = int(algo_cfg.get("num_generations", 40))
    mutation_rate  = float(algo_cfg.get("mutation_rate", 0.1))
    crossover_rate = float(algo_cfg.get("crossover_rate", 0.8))
    elite_size     = int(algo_cfg.get("elite_size", 10))
    tourn_size     = int(algo_cfg.get("tournament_size", 5))

    logger.info(
        "Optimisation démarrée | objectif=%s | fc_min=%.1f MPa | "
        "classe=%s | pop=%d | gen=%d",
        objective, target_strength, required_class, pop_size, n_gen,
    )

    rng = np.random.RandomState(random_state)

    # ── Initialisation de la population ────────────────────────────────────
    population: list[Dict[str, float]] = [
        sample_random_mix(rng) for _ in range(pop_size)
    ]

    best_result: Optional[OptimizationResult] = None
    best_score: float = _INFEASIBLE_SCORE
    n_feasible_total: int = 0  # Pour les logs de convergence

    # ── Boucle générationnelle ──────────────────────────────────────────────
    for gen in range(n_gen):

        # Évaluation de tous les individus
        fitness: list[float]                    = []
        metas:   list[Tuple[Dict, float, float]] = []

        for mix in population:
            score, preds, cost, co2 = evaluate_mix(
                model=model,
                feature_list=feature_list,
                mix=mix,
                target_strength=target_strength,
                required_class=required_class,
                objective=objective,
            )
            fitness.append(score)
            metas.append((preds, cost, co2))

        fitness_arr = np.asarray(fitness)
        n_feasible  = int(np.sum(fitness_arr > _INFEASIBLE_SCORE))
        n_feasible_total += n_feasible

        # ── Mise à jour du meilleur global ─────────────────────────────────
        gen_best_idx = int(np.argmax(fitness_arr))

        if fitness_arr[gen_best_idx] > best_score:
            best_score = float(fitness_arr[gen_best_idx])
            best_mix   = population[gen_best_idx]
            best_preds, best_cost, best_co2 = metas[gen_best_idx]

            # Ajustement minimal : ciment ≥ 200 kg/m³ (sécurité physique)
            mix_adjusted = best_mix.copy()
            if mix_adjusted.get("Ciment", 0.0) < 200.0:
                mix_adjusted["Ciment"] = 200.0

            # Validation complète sur la solution candidate
            try:
                preds_validated = predict_concrete_properties(
                    composition=mix_adjusted,
                    model=model,
                    feature_list=feature_list,
                    validate=True,
                )

                # Détermination de la classe atteinte
                from app.core.validator import determine_exposure_class
                achieved_class = determine_exposure_class(
                    ratio_el=float(preds_validated["Ratio_E_L"]),
                    resistance=float(preds_validated["Resistance"]),
                    diffusion_cl=float(preds_validated.get("Diffusion_Cl", 99.0)),
                    carbonatation=float(preds_validated.get("Carbonatation", 99.0)),
                )

                best_result = OptimizationResult(
                    mix=mix_adjusted,
                    targets=preds_validated,
                    cost=compute_cost(mix_adjusted),
                    co2=compute_co2(mix_adjusted),
                    target_strength=float(target_strength),
                    objective=objective,
                    generations=n_gen,
                    required_class=required_class,
                    achieved_class=achieved_class,
                )

            except ValueError as ve:
                # La validation complète a échoué → fallback sur preds brutes
                logger.warning(
                    "Validation finale échouée (gen=%d, idx=%d) : %s — fallback sur preds brutes",
                    gen, gen_best_idx, ve,
                )
                best_result = OptimizationResult(
                    mix=best_mix,
                    targets=best_preds,
                    cost=float(best_cost),
                    co2=float(best_co2),
                    target_strength=float(target_strength),
                    objective=objective,
                    generations=n_gen,
                    required_class=required_class,
                    achieved_class=None,  # Indisponible après échec de validation
                )

        # ── Log de progression (toutes les 10 générations) ─────────────────
        if (gen + 1) % 10 == 0:
            logger.debug(
                "Gen %d/%d | Viables=%d/%d | Meilleur score=%.4f",
                gen + 1, n_gen, n_feasible, pop_size, best_score,
            )

        # ── Génération suivante ─────────────────────────────────────────────

        # Ignorer une génération entièrement non-viable
        if np.all(fitness_arr <= _INFEASIBLE_SCORE):
            continue

        # Élitisme : conservation des N meilleurs
        elite_indices  = list(np.argsort(-fitness_arr)[:elite_size])
        new_population = [population[i].copy() for i in elite_indices]

        # Reproduction jusqu'à remplir la population
        while len(new_population) < pop_size:
            parent1 = _tournament_select(population, fitness_arr, tourn_size, rng)
            parent2 = _tournament_select(population, fitness_arr, tourn_size, rng)

            if rng.rand() < crossover_rate:
                child = _crossover(parent1, parent2, rng)
            else:
                child = parent1.copy()

            child = _mutate(child, mutation_rate, rng)
            new_population.append(child)

        population = new_population

    # ── Log final ───────────────────────────────────────────────────────────
    if best_result is not None:
        logger.info(
            "Optimisation terminée | objectif=%s | coût=%.2f €/m³ | CO₂=%.1f kg/m³ | "
            "fc=%.1f MPa | classe_atteinte=%s | viables_total=%d",
            best_result.objective,
            best_result.cost,
            best_result.co2,
            best_result.targets.get("Resistance", 0.0),
            best_result.achieved_class,
            n_feasible_total,
        )
    else:
        logger.warning(
            "Aucune solution viable trouvée après %d générations. "
            "Vérifier les contraintes (target_strength=%.1f MPa, required_class=%s).",
            n_gen, target_strength, required_class,
        )

    return best_result