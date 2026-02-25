"""
tests/conftest.py
═════════════════
Fixtures pytest partagées par toute la suite de tests.

Contient :
  - Compositions béton de référence (normales, limites, invalides)
  - Mock du modèle ML (XGBoost simulé)
  - Mock du DatabaseManager
  - Résultats de prédiction de référence
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, List, Any


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITIONS DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def composition_standard():
    """Béton C30/37 standard — tous paramètres valides."""
    return {
        "Ciment":           350.0,
        "Laitier":            0.0,
        "CendresVolantes":    0.0,
        "Eau":              175.0,
        "SableFin":         800.0,
        "GravilonsGros":   1000.0,
        "Superplastifiant":   5.0,
        "Age":               28.0,
        "Metakaolin":         0.0,
    }


@pytest.fixture
def composition_hpc():
    """Béton Hautes Performances — laitier + superplastifiant élevé."""
    return {
        "Ciment":           300.0,
        "Laitier":          150.0,
        "CendresVolantes":    0.0,
        "Eau":              140.0,
        "SableFin":         750.0,
        "GravilonsGros":    950.0,
        "Superplastifiant":  10.0,
        "Age":               28.0,
        "Metakaolin":         0.0,
    }


@pytest.fixture
def composition_mk():
    """Béton avec Métakaolin 15 % de substitution."""
    return {
        "Ciment":           300.0,
        "Laitier":            0.0,
        "CendresVolantes":    0.0,
        "Eau":              160.0,
        "SableFin":         800.0,
        "GravilonsGros":   1000.0,
        "Superplastifiant":   7.0,
        "Age":               28.0,
        "Metakaolin":        50.0,
    }


@pytest.fixture
def composition_cem3():
    """Béton CEM III/B — fort taux de laitier."""
    return {
        "Ciment":            80.0,
        "Laitier":          252.0,
        "CendresVolantes":    0.0,
        "Eau":              165.0,
        "SableFin":         810.0,
        "GravilonsGros":   1010.0,
        "Superplastifiant":   6.0,
        "Age":               56.0,
        "Metakaolin":         0.0,
    }


@pytest.fixture
def composition_invalid_negative():
    """Composition invalide — dosage négatif."""
    return {
        "Ciment":          -50.0,
        "Eau":             175.0,
        "SableFin":        800.0,
        "GravilonsGros":  1000.0,
    }


@pytest.fixture
def composition_missing_key():
    """Composition invalide — clé obligatoire manquante (SableFin)."""
    return {
        "Ciment": 350.0,
        "Eau":    175.0,
        "GravilonsGros": 1000.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRÉDICTIONS DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def predictions_standard():
    """Prédictions ML de référence pour composition_standard."""
    return {
        "Resistance":      38.5,
        "Diffusion_Cl":     6.2,
        "Carbonatation":   12.0,
        "Ratio_E_L":        0.50,
        "Liant_Total":    350.0,
        "Pct_Substitution": 0.0,
    }


@pytest.fixture
def predictions_hpc():
    """Prédictions ML de référence pour composition HPC."""
    return {
        "Resistance":      58.0,
        "Diffusion_Cl":     3.1,
        "Carbonatation":    7.0,
        "Ratio_E_L":        0.31,
        "Liant_Total":    450.0,
        "Pct_Substitution": 0.33,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK MODÈLE ML
# ═══════════════════════════════════════════════════════════════════════════════

class MockModel:
    """
    Simulacre de modèle XGBoost multi-output.
    predict() retourne un tableau numpy cohérent
    avec les colonnes [Resistance, Diffusion_Cl, Carbonatation].
    """

    def predict(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        return np.column_stack([
            np.full(n, 38.5),   # Resistance (MPa)
            np.full(n,  6.2),   # Diffusion_Cl (×10⁻¹²)
            np.full(n, 12.0),   # Carbonatation (mm)
        ])

    def predict_proba(self, X):
        raise NotImplementedError

    @property
    def feature_importances_(self):
        return np.ones(9) / 9


@pytest.fixture
def mock_model():
    return MockModel()


@pytest.fixture
def feature_list():
    """Noms de features dans l'ordre attendu par le modèle."""
    return [
        "Ciment", "Laitier", "CendresVolantes", "Eau",
        "SableFin", "GravilonsGros", "Superplastifiant",
        "Age", "Metakaolin",
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_db_manager():
    """DatabaseManager simulé — toutes les méthodes retournent des valeurs valides."""
    db = MagicMock()
    db.is_connected = True

    db.save_prediction.return_value = True

    db.get_recent_predictions.return_value = [
        {
            "id":                   1,
            "formulation_name":     "Test_XC1",
            "resistance_predicted": 38.5,
            "ratio_e_l":            0.50,
            "created_at":           datetime(2025, 1, 15, 10, 0, 0),
            "ciment":               350.0,
            "eau":                  175.0,
            "sable":                800.0,
            "gravier":             1000.0,
            "adjuvants":             5.0,
            "age":                  28.0,
            "laitier":               0.0,
            "cendres":               0.0,
        }
    ]

    db.execute_query.return_value = [
        {
            "id":                    1,
            "nom_formulation":       "Test",
            "resistance_predite":    38.5,
            "diffusion_cl_predite":   6.2,
            "carbonatation_predite": 12.0,
            "ratio_eau_liaison":      0.50,
            "ciment":               350.0,
            "laitier":                0.0,
            "cendres":                0.0,
            "eau":                  175.0,
            "sable":                800.0,
            "gravier":             1000.0,
            "adjuvants":              5.0,
            "age":                   28.0,
            "created_at":            datetime(2025, 1, 15, 10, 0, 0),
        }
    ]

    return db


@pytest.fixture
def mock_db_disconnected():
    """DatabaseManager simulé — hors ligne."""
    db = MagicMock()
    db.is_connected = False
    db.save_prediction.return_value = False
    return db


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS PARTAGÉS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def all_cement_types():
    """Liste des types de ciment disponibles dans la base CO₂."""
    return [
        "CEM I", "CEM II/A-LL", "CEM II/B-LL",
        "CEM II/A-S", "CEM II/B-S",
        "CEM III/A", "CEM III/B", "CEM III/C",
        "CEM IV/A", "CEM V/A", "LC3-50",
    ]


@pytest.fixture
def all_exposure_classes():
    """Classes d'exposition EN 206 standard."""
    return ["XC1", "XC2", "XC3", "XC4", "XD1", "XD2", "XD3", "XS1", "XS2", "XS3"]