"""
tests/test_predictor.py
════════════════════════
Tests unitaires — predict_concrete_properties() & predict_with_mk()

Couvre :
  - Retour dict avec toutes les clés attendues
  - Valeurs numériques dans les plages physiques
  - predict_with_mk() : correction positive ajoutée à la résistance
  - Gestion MK=0 via predict_with_mk → identique à predict_concrete_properties
  - Cohérence Ratio_E_L calculé vs composition
  - Liant_Total = ciment + additions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.core.predictor import predict_concrete_properties, predict_with_mk


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS predict_concrete_properties
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictConcreteProperties:

    def test_retourne_dict(self, composition_standard, mock_model, feature_list):
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        assert isinstance(result, dict)

    def test_cles_obligatoires_presentes(self, composition_standard, mock_model, feature_list):
        """Le dict retourné doit contenir toutes les cibles."""
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        required = {"Resistance", "Diffusion_Cl", "Carbonatation", "Ratio_E_L", "Liant_Total"}
        assert required.issubset(set(result.keys())), (
            f"Clés manquantes : {required - set(result.keys())}"
        )

    def test_resistance_dans_plage(self, composition_standard, mock_model, feature_list):
        """Résistance prédite doit être dans [5, 120] MPa."""
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        assert 5 <= result["Resistance"] <= 120, (
            f"Résistance hors plage : {result['Resistance']}"
        )

    def test_diffusion_dans_plage(self, composition_standard, mock_model, feature_list):
        """Diffusion Cl⁻ doit être > 0."""
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        assert result["Diffusion_Cl"] > 0

    def test_ratio_el_dans_plage(self, composition_standard, mock_model, feature_list):
        """Ratio E/L doit être dans [0.1, 1.5]."""
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        assert 0.1 <= result["Ratio_E_L"] <= 1.5, (
            f"Ratio E/L hors plage : {result['Ratio_E_L']}"
        )

    def test_liant_total_positif(self, composition_standard, mock_model, feature_list):
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        assert result["Liant_Total"] > 0

    def test_liant_total_coherent_avec_composition(
        self, composition_standard, mock_model, feature_list
    ):
        """Liant_Total ≥ Ciment (au minimum)."""
        result = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        ciment = composition_standard["Ciment"]
        assert result["Liant_Total"] >= ciment, (
            f"Liant_Total ({result['Liant_Total']}) < Ciment ({ciment})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS predict_with_mk
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictWithMk:

    @pytest.fixture
    def mk_corrector(self):
        from app.core.mk_corrector import MKCorrector
        return MKCorrector()

    def test_mk_zero_resultat_identique(
        self, composition_standard, mock_model, feature_list, mk_corrector
    ):
        """MK=0 : predict_with_mk doit donner le même résultat que predict_concrete_properties."""
        composition_standard["Metakaolin"] = 0.0

        res_base = predict_concrete_properties(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
        )
        res_mk = predict_with_mk(
            composition=composition_standard,
            model=mock_model,
            feature_list=feature_list,
            mk_corrector=mk_corrector,
        )
        assert abs(res_base["Resistance"] - res_mk["Resistance"]) < 0.01, (
            f"MK=0 → Δ résistance inattendu : {res_base['Resistance']} vs {res_mk['Resistance']}"
        )

    def test_mk_positif_augmente_resistance(
        self, composition_mk, mock_model, feature_list, mk_corrector
    ):
        """MK > 0 : résistance via predict_with_mk > résistance de base."""
        res_base = predict_concrete_properties(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
        )
        res_mk = predict_with_mk(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
            mk_corrector=mk_corrector,
        )
        assert res_mk["Resistance"] > res_base["Resistance"], (
            f"MK devrait augmenter la résistance : base={res_base['Resistance']:.1f}, "
            f"mk={res_mk['Resistance']:.1f}"
        )

    def test_mk_retourne_memes_cles(
        self, composition_mk, mock_model, feature_list, mk_corrector
    ):
        """predict_with_mk doit retourner les mêmes clés que predict_concrete_properties."""
        res_base = predict_concrete_properties(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
        )
        res_mk = predict_with_mk(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
            mk_corrector=mk_corrector,
        )
        assert set(res_base.keys()) == set(res_mk.keys()), (
            f"Clés différentes : {set(res_base.keys()) ^ set(res_mk.keys())}"
        )

    def test_correction_bornee(
        self, composition_mk, mock_model, feature_list, mk_corrector
    ):
        """La correction MK ne doit pas dépasser 25 MPa."""
        res_base = predict_concrete_properties(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
        )
        res_mk = predict_with_mk(
            composition=composition_mk,
            model=mock_model,
            feature_list=feature_list,
            mk_corrector=mk_corrector,
        )
        delta = res_mk["Resistance"] - res_base["Resistance"]
        assert delta <= 25.0, f"Correction MK trop élevée : {delta:.1f} MPa"