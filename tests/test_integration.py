# test/test_integration.py
import pytest
from app.core.predictor import predict_concrete_properties
from app.models.loader import load_production_assets
from app.models.model_config import MODEL_FEATURES_ORDER
import pandas as pd


def test_full_pipeline():
    # Charge le modèle une seule fois
    model, features, _ = load_production_assets()
    
    # Vérifie cohérence ordre
    assert features == MODEL_FEATURES_ORDER
    
    # Formulation standard
    comp = {
        "Ciment": 280.0,
        "Laitier": 0.0,
        "CendresVolantes": 0.0,
        "Eau": 180.0,
        "Superplastifiant": 0.0,
        "GravilonsGros": 1100.0,
        "SableFin": 750.0,
        "Age": 28.0
    }
    
    result = predict_concrete_properties(
        comp,
        model=model,
        feature_list=features
    )
    
    # Vérifications R&D
    assert 20 < result["Resistance"] < 40, "Résistance hors plage réaliste"
    assert 5 < result["Diffusion_Cl"] < 12, "Diffusion Cl hors plage typique"
    assert 10 < result["Carbonatation"] < 25, "Carbonatation hors plage"
    assert result["Ratio_E_L"] == pytest.approx(0.643, 0.01)
    assert result["Liant_Total"] == 280.0