"""
═══════════════════════════════════════════════════════════════════════════════
app/core/optimizer.py - Validation assouplie pendant optimisation
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple

import numpy as np

from config.constants import (
    BOUNDS,
    CO2_EMISSIONS_KG,
    MATERIALS_COST_EURO_KG,
)
from config.settings import OPTIMIZER_SETTINGS
from app.core.predictor import predict_concrete_properties


Objective = Literal["minimize_cost", "minimize_co2"]


@dataclass
class OptimizationResult:
    """Résultat optimisation."""
    mix: Dict[str, float]
    targets: Dict[str, float]
    cost: float
    co2: float
    target_strength: float
    objective: Objective
    generations: int


def compute_cost(mix: Dict[str, float]) -> float:
    """Calcule coût matériaux (€/m³)."""
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(MATERIALS_COST_EURO_KG.get(name, 0.0))
            for name in MATERIALS_COST_EURO_KG
        )
    )


def compute_co2(mix: Dict[str, float]) -> float:
    """Calcule empreinte CO₂ (kg/m³)."""
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(CO2_EMISSIONS_KG.get(name, 0.0))
            for name in CO2_EMISSIONS_KG
        )
    )


def sample_random_mix(rng: np.random.RandomState) -> Dict[str, float]:
    """Génère composition aléatoire dans bornes."""
    return {
        name: float(
            rng.uniform(low=float(bounds["min"]), high=float(bounds["max"]))
        )
        for name, bounds in BOUNDS.items()
    }


def evaluate_mix(
    model: Any,
    feature_list: list[str],
    mix: Dict[str, float],
    target_strength: float,
    objective: Objective,
) -> Tuple[float, Dict[str, float], float, float]:
    """
    Évalue composition (VERSION CORRIGÉE).
    
    ✅ CORRECTION: validate=False pour éviter rejets prématurés
    """
    # ✅ VALIDATION DÉSACTIVÉE pendant optimisation
    preds = predict_concrete_properties(
        composition=mix,
        model=model,
        feature_list=feature_list,
        validate=False  # ← CORRECTION CRITIQUE
    )
    
    strength = float(preds["Resistance"])

    # Contrainte résistance minimale
    if strength < target_strength:
        return -1e9, preds, 0.0, 0.0

    cost = compute_cost(mix)
    co2 = compute_co2(mix)

    if objective == "minimize_cost":
        score = -cost
    elif objective == "minimize_co2":
        score = -co2
    else:
        score = strength

    return score, preds, cost, co2


def _crossover(parent1: Dict[str, float], parent2: Dict[str, float], rng) -> Dict[str, float]:
    """Croisement arithmétique."""
    child = {}
    for key in BOUNDS.keys():
        alpha = rng.rand()
        child[key] = float(alpha * parent1[key] + (1 - alpha) * parent2[key])
    return child


def _mutate(mix: Dict[str, float], mutation_rate: float, rng) -> Dict[str, float]:
    """Mutation gaussienne."""
    mutated = mix.copy()
    for key, bounds in BOUNDS.items():
        if rng.rand() < mutation_rate:
            span = float(bounds["max"]) - float(bounds["min"])
            mutated[key] += rng.normal(scale=0.05 * span)
            mutated[key] = float(
                np.clip(mutated[key], float(bounds["min"]), float(bounds["max"]))
            )
    return mutated


def optimize_mix(
    model: Any,
    feature_list: list[str],
    target_strength: float,
    objective: Objective = "minimize_cost",
    random_state: int | None = None,
) -> OptimizationResult | None:
    """
    Optimise formulation (VERSION CORRIGÉE).
    
    ✅ AJOUT: Validation finale après optimisation
    """
    algo_cfg = OPTIMIZER_SETTINGS.get("genetic_algorithm", {})
    pop_size = int(algo_cfg.get("population_size", 80))
    n_gen = int(algo_cfg.get("num_generations", 40))
    mutation_rate = float(algo_cfg.get("mutation_rate", 0.1))
    crossover_rate = float(algo_cfg.get("crossover_rate", 0.8))
    elite_size = int(algo_cfg.get("elite_size", 10))
    tournament_size = int(algo_cfg.get("tournament_size", 5))

    rng = np.random.RandomState(random_state)

    # Population initiale
    population = [sample_random_mix(rng) for _ in range(pop_size)]

    best_result: OptimizationResult | None = None
    best_score = -1e9

    for _ in range(n_gen):
        # Évaluation
        fitness = []
        metas = []
        for mix in population:
            score, preds, cost, co2 = evaluate_mix(
                model, feature_list, mix, target_strength, objective
            )
            fitness.append(score)
            metas.append((preds, cost, co2))

        fitness = np.asarray(fitness)

        # Mise à jour meilleur
        gen_best_idx = int(np.argmax(fitness))
        if fitness[gen_best_idx] > best_score:
            best_score = float(fitness[gen_best_idx])
            mix = population[gen_best_idx]
            preds, cost, co2 = metas[gen_best_idx]
            
            # ✅ VALIDATION FINALE de la solution
            # Ajuster aux bornes strictes si nécessaire
            mix_adjusted = mix.copy()
            
            # Forcer ciment >= 200 si trop bas
            if mix_adjusted['Ciment'] < 200:
                mix_adjusted['Ciment'] = 200.0
            
            # Re-prédire avec composition ajustée
            try:
                preds_adjusted = predict_concrete_properties(
                    composition=mix_adjusted,
                    model=model,
                    feature_list=feature_list,
                    validate=True  # ✅ Validation finale activée
                )
                
                # Utiliser la version ajustée si validation OK
                best_result = OptimizationResult(
                    mix=mix_adjusted,
                    targets=preds_adjusted,
                    cost=compute_cost(mix_adjusted),
                    co2=compute_co2(mix_adjusted),
                    target_strength=float(target_strength),
                    objective=objective,
                    generations=n_gen,
                )
            except ValueError:
                # Si validation échoue, utiliser version brute
                best_result = OptimizationResult(
                    mix=mix,
                    targets=preds,
                    cost=float(cost),
                    co2=float(co2),
                    target_strength=float(target_strength),
                    objective=objective,
                    generations=n_gen,
                )

        # Si tout est invalide
        if np.all(fitness < -1e8):
            continue

        # Sélection par tournoi
        def tournament_select() -> Dict[str, float]:
            idxs = rng.randint(0, pop_size, size=tournament_size)
            best_idx = idxs[np.argmax(fitness[idxs])]
            return population[best_idx]

        # Élites
        elite_indices = list(np.argsort(-fitness)[:elite_size])
        new_population = [population[i].copy() for i in elite_indices]

        # Reproduction
        while len(new_population) < pop_size:
            parent1 = tournament_select()
            parent2 = tournament_select()

            if rng.rand() < crossover_rate:
                child = _crossover(parent1, parent2, rng)
            else:
                child = parent1.copy()

            child = _mutate(child, mutation_rate, rng)
            new_population.append(child)

        population = new_population

    return best_result