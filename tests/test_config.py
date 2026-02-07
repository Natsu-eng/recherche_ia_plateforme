# test/test_config.py
import pytest
from app.models.model_config import (
    MODEL_FEATURES_ORDER,
    CANONICAL_FEATURES_ORDER,
    normalize_feature_name
)

def test_model_features_order():
    assert len(MODEL_FEATURES_ORDER) == 15
    assert isinstance(MODEL_FEATURES_ORDER, list)
    assert all(isinstance(f, str) for f in MODEL_FEATURES_ORDER)
    # Vérifie que l'ordre commence bien par 'Eau' (comme dans ton modèle réel)
    assert MODEL_FEATURES_ORDER[0] == 'Eau'


def test_canonical_features_order():
    assert len(CANONICAL_FEATURES_ORDER) == 15
    assert set(CANONICAL_FEATURES_ORDER) == set(MODEL_FEATURES_ORDER)


def test_normalize_feature_name():
    assert normalize_feature_name("GravillosGros") == "GravilonsGros"
    assert normalize_feature_name("Sable Fin") == "SableFin"
    assert normalize_feature_name("Log_Age") == "Log_Age"
    assert normalize_feature_name("Cendres Volantes") == "CendresVolantes"