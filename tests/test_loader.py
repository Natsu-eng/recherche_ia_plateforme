# test/test_loader.py
import pytest
from pathlib import Path
from app.models.loader import load_production_assets, assets_exist

# Chemin attendu (adapte selon ton projet)
MODELS_DIR = Path(__file__).parent.parent / "ml_models" / "production"


def test_assets_exist():
    assert assets_exist(MODELS_DIR), "Les assets de production doivent exister"


def test_load_production_assets():
    model, features, metadata = load_production_assets(MODELS_DIR)
    
    assert model is not None
    assert len(features) == 15
    assert isinstance(metadata, dict)
    assert "model_name" in metadata
    assert "features_hash" in metadata
    
    # Vérifie que l'ordre est cohérent avec la config
    from app.models.model_config import MODEL_FEATURES_ORDER
    assert features == MODEL_FEATURES_ORDER, "Ordre des features incohérent"


def test_model_can_predict():
    model, features, _ = load_production_assets(MODELS_DIR)
    
    # Test rapide avec données minimales
    import numpy as np
    X_dummy = np.zeros((1, 15))
    pred = model.predict(X_dummy)
    assert pred.shape == (1, 3)  # 3 sorties
    assert not np.any(np.isnan(pred)), "Prédiction contient des NaN"