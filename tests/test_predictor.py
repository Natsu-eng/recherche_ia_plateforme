# test/test_predictor.py
import pytest
from app.core.predictor import (
    predict_concrete_properties,
    validate_composition,
    engineer_features,
    verify_features_alignment,
    MODEL_FEATURES_ORDER
)
import pandas as pd
import numpy as np

# Données de test C25/30
C25_30 = {
    "Ciment": 280.0,
    "Laitier": 0.0,
    "CendresVolantes": 0.0,
    "Eau": 180.0,
    "Superplastifiant": 0.0,
    "GravilonsGros": 1100.0,
    "SableFin": 750.0,
    "Age": 28.0
}


def test_validate_composition_valid():
    valid, msg = validate_composition(C25_30)
    assert valid
    assert msg == "Composition valide"


def test_validate_composition_invalid():
    invalid = C25_30.copy()
    invalid["Ciment"] = -100
    valid, msg = validate_composition(invalid)
    assert not valid
    assert "négative" in msg


def test_engineer_features():
    df = pd.DataFrame([C25_30])
    df_eng = engineer_features(df)
    
    assert "Ratio_E_L" in df_eng.columns
    assert "Liant_Total" in df_eng.columns
    assert "Ciment_x_LogAge" in df_eng.columns
    assert df_eng["Ratio_E_L"].iloc[0] == pytest.approx(0.642857, 0.001)
    assert df_eng["Liant_Total"].iloc[0] == 280.0


def test_verify_features_alignment():
    is_ok, msg = verify_features_alignment(MODEL_FEATURES_ORDER, verbose=False)
    assert is_ok
    assert "Alignement parfait" in msg


def test_predict_concrete_properties(mock_model):  # suppose que tu as un fixture mock_model
    # Si tu as un vrai modèle chargé dans les tests
    result = predict_concrete_properties(
        C25_30,
        model=mock_model,
        feature_list=MODEL_FEATURES_ORDER
    )
    
    assert "Resistance" in result
    assert "Diffusion_Cl" in result
    assert "Carbonatation" in result
    assert result["Resistance"] > 0
    assert result["Liant_Total"] == 280.0