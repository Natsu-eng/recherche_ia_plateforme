"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/optimizer.py
Auteur : Stage R&D - IMT Nord Europe
Objet  : Algorithme d'optimisation de formulation béton (coût / CO₂ / résistance)
═══════════════════════════════════════════════════════════════════════════════

Ce module implémente un optimiseur à base d'algorithme génétique léger, adapté
à une utilisation en temps réel dans Streamlit. Il s'appuie sur :
  - `config.constants.BOUNDS`, `MATERIALS_COST_EURO_KG`, `CO2_EMISSIONS_KG`
  - `app.core.predictor.predict_concrete_properties`

Toutes les grandeurs manipulation sont cohérentes avec le dataset :
  Ciment, Laitier, CendresVolantes, Eau, Superplastifiant, GravilonsGros,
  SableFin, Age.
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
    """
    Conteneur structuré pour les résultats de l'optimisation.

    Attributs principaux :
        mix:      composition optimale (kg/m³)
        targets:  prédictions ML pour cette composition
        cost:     coût matériaux (€/m³)
        co2:      empreinte carbone (kg CO₂/m³)
    """

    mix: Dict[str, float]
    targets: Dict[str, float]
    cost: float
    co2: float
    target_strength: float
    objective: Objective
    generations: int


# ═════════════════════════════════════════════════════════════════════════════
# FONCTIONS MÉTIERS : COÛT, CO₂, CONTRAINTES PHYSIQUES
# ═════════════════════════════════════════════════════════════════════════════

def compute_cost(mix: Dict[str, float]) -> float:
    """Calcule le coût matériaux (€/m³) à partir de la composition."""
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(MATERIALS_COST_EURO_KG.get(name, 0.0))
            for name in MATERIALS_COST_EURO_KG
        )
    )


def compute_co2(mix: Dict[str, float]) -> float:
    """Calcule l'empreinte CO₂ (kg CO₂/m³) à partir de la composition."""
    return float(
        sum(
            float(mix.get(name, 0.0)) * float(CO2_EMISSIONS_KG.get(name, 0.0))
            for name in CO2_EMISSIONS_KG
        )
    )


def sample_random_mix(rng: np.random.RandomState) -> Dict[str, float]:
    """
    Génère une composition aléatoire dans les bornes ingénieurs définies.

    Les noms de variables sont STRICTEMENT alignés avec le dataset et
    `config.constants.BOUNDS`.
    """
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
    Évalue une composition :
      - fait appel au modèle ML
      - calcule coût / CO₂
      - renvoie un score selon l'objectif choisi

    Le score est **maximisé** (on travaille en "fitness" positive).
    """
    preds = predict_concrete_properties(
        composition=mix,
        model=model,
        feature_list=feature_list
    )
    strength = float(preds["Resistance"])

    # Contrainte dure : ne garder que les mélanges atteignant la résistance cible
    if strength < target_strength:
        return -1e9, preds, 0.0, 0.0

    cost = compute_cost(mix)
    co2 = compute_co2(mix)

    if objective == "minimize_cost":
        score = -cost  # plus petit coût -> score plus grand
    elif objective == "minimize_co2":
        score = -co2
    else:  # garde porte de sortie raisonnable
        score = strength

    return score, preds, cost, co2


# ═════════════════════════════════════════════════════════════════════════════
# ALGORITHME GÉNÉTIQUE SIMPLE
# ═════════════════════════════════════════════════════════════════════════════

def _crossover(parent1: Dict[str, float], parent2: Dict[str, float], rng) -> Dict[str, float]:
    """Croisement arithmétique simple entre deux parents."""
    child = {}
    for key in BOUNDS.keys():
        alpha = rng.rand()
        child[key] = float(alpha * parent1[key] + (1 - alpha) * parent2[key])
    return child


def _mutate(mix: Dict[str, float], mutation_rate: float, rng) -> Dict[str, float]:
    """Mutation gaussienne bornée sur chaque variable."""
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
    Optimise une formulation béton pour une résistance cible.

    Args:
        model: Modèle ML entraîné (XGBoost / RandomForest / autre).
        feature_list: Liste ordonnée des features attendus par le modèle.
        target_strength: Résistance minimale requise (MPa).
        objective: `"minimize_cost"` ou `"minimize_co2"`.
        random_state: graine pour reproductibilité (optionnel).

    Returns:
        `OptimizationResult` si une solution valide est trouvée, sinon `None`.
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

        # Mise à jour du meilleur
        gen_best_idx = int(np.argmax(fitness))
        if fitness[gen_best_idx] > best_score:
            best_score = float(fitness[gen_best_idx])
            mix = population[gen_best_idx]
            preds, cost, co2 = metas[gen_best_idx]
            best_result = OptimizationResult(
                mix=mix,
                targets=preds,
                cost=float(cost),
                co2=float(co2),
                target_strength=float(target_strength),
                objective=objective,
                generations=n_gen,
            )

        # Si tout est invalide (aucun mélange n'atteint la résistance cible)
        if np.all(fitness < -1e8):
            continue

        # Sélection par tournoi
        def tournament_select() -> Dict[str, float]:
            idxs = rng.randint(0, pop_size, size=tournament_size)
            best_idx = idxs[np.argmax(fitness[idxs])]
            return population[best_idx]

        # Élites (meilleurs individus recopiés)
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