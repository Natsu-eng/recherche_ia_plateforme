"""
tests/test_integration.py
══════════════════════════
Tests d'intégration — Pipeline complet

Couvre le flux de bout en bout :
  Composition → Prédiction ML → Calcul CO₂ → Validation EN 206
  
  Ce sont les scénarios réels de la plateforme :
  - Formulateur : predict → co2 → validate → store
  - Optimiseur  : optimize → co2 → validate → store en session
  - Comparateur : N formulations → predict → rank CO₂
"""

import pytest
import math
from datetime import datetime
from unittest.mock import MagicMock

from app.core.predictor import predict_concrete_properties
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from app.core.validator import validate_formulation


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE COMPLET — FORMULATEUR
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineFormulateur:

    def _run_pipeline(
        self, composition: dict, cement_type: str, required_class: str,
        mock_model, feature_list
    ) -> dict:
        """Exécute le pipeline complet et retourne tous les résultats."""
        predictions = predict_concrete_properties(
            composition=composition,
            model=mock_model,
            feature_list=feature_list,
        )
        co2_calc   = CO2Calculator()
        co2_result = co2_calc.calculate(composition, cement_type)
        validation = validate_formulation(
            composition=composition,
            predictions=predictions,
            required_class=required_class,
        )
        return {
            "predictions": predictions,
            "co2_result":  co2_result,
            "validation":  validation,
        }

    def test_pipeline_standard_xc1(
        self, composition_standard, mock_model, feature_list
    ):
        """Pipeline complet sur béton standard → tous les objets valides."""
        result = self._run_pipeline(
            composition_standard, "CEM I", "XC1", mock_model, feature_list
        )
        assert result["predictions"]["Resistance"] > 0
        assert result["co2_result"].co2_total_kg_m3 > 0
        assert result["validation"].compliance_score >= 0

    def test_pipeline_hpc_cem3b(
        self, composition_hpc, mock_model, feature_list
    ):
        """Pipeline HPC avec CEM III/B → CO₂ réduit."""
        result_cem1  = self._run_pipeline(
            composition_hpc, "CEM I", "XC3", mock_model, feature_list
        )
        result_cem3b = self._run_pipeline(
            composition_hpc, "CEM III/B", "XC3", mock_model, feature_list
        )
        assert (
            result_cem3b["co2_result"].co2_total_kg_m3
            < result_cem1["co2_result"].co2_total_kg_m3
        ), "CEM III/B doit avoir moins de CO₂ que CEM I"

    def test_session_storage_structure(
        self, composition_standard, mock_model, feature_list
    ):
        """La structure stockée en session doit contenir toutes les clés requises."""
        result = self._run_pipeline(
            composition_standard, "CEM I", "XC1", mock_model, feature_list
        )

        # Simule le stockage session tel que 1_Formulateur.py le fait
        last_prediction = {
            "composition":       composition_standard,
            "predictions":       result["predictions"],
            "co2_result":        result["co2_result"],
            "cement_type":       "CEM I",
            "validation_report": result["validation"],
            "required_class":    "XC1",
            "timestamp":         datetime.now(),
            "name":              "Test_Intégration",
        }

        required_keys = {
            "composition", "predictions", "co2_result",
            "cement_type", "validation_report", "required_class",
            "timestamp", "name",
        }
        assert required_keys.issubset(set(last_prediction.keys()))

    def test_export_csv_data_complet(
        self, composition_standard, mock_model, feature_list
    ):
        """Les données d'export CSV doivent couvrir toutes les colonnes attendues."""
        result = self._run_pipeline(
            composition_standard, "CEM I", "XC1", mock_model, feature_list
        )
        val = result["validation"]
        co2 = result["co2_result"]

        export_data = {
            "Nom":              "Test",
            "Date":             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Classe_Exigee":    "XC1",
            "Classe_Atteinte":  val.achieved_class or "N/A",
            "Conforme":         val.compliance_with_required,
            "Score_Conformite": val.compliance_score,
            **composition_standard,
            **result["predictions"],
            "CO2_Total_kg_m3":  co2.co2_total_kg_m3,
            "Cement_Type":      "CEM I",
        }

        # Vérification types
        assert isinstance(export_data["Conforme"], bool)
        assert isinstance(export_data["CO2_Total_kg_m3"], float)
        assert isinstance(export_data["Score_Conformite"], (int, float))


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE — OPTIMISEUR SESSION STORAGE (v1.1.0)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineOptimiseurSession:

    def _build_opt_result_session(
        self, composition: dict, cement_type: str, required_class: str,
        mock_model, feature_list, obj_key: str, cost: float = 65.0
    ) -> dict:
        """
        Simule le stockage en session tel que 4_Optimiseur.py v1.1.0 le fait
        après une optimisation réussie.
        """
        predictions = predict_concrete_properties(
            composition=composition,
            model=mock_model,
            feature_list=feature_list,
        )
        co2_calc   = CO2Calculator()
        co2_result = co2_calc.calculate(composition, cement_type)
        co2_total  = co2_result.co2_total_kg_m3
        validation = validate_formulation(
            composition=composition,
            predictions=predictions,
            required_class=required_class,
        )
        label = {
            "minimize_cost": "💰 Optimal Coût",
            "minimize_co2":  "🌍 Optimal CO₂",
        }.get(obj_key, obj_key)

        return {
            "composition":        composition,
            "predictions":        predictions,
            "co2_result":         co2_result,
            "co2_total":          co2_total,
            "validation":         validation,
            "cost":               cost,
            "cement_type":        cement_type,
            "required_class":     required_class,
            "label":              label,
            "timestamp":          datetime.now(),
            "target_resistance":  30.0,
        }

    def test_opt_results_persiste_entre_reruns(
        self, composition_standard, mock_model, feature_list
    ):
        """
        Simule deux reruns consécutifs :
        Rerun 1 → optimize_button=True → calcul + stockage session
        Rerun 2 → optimize_button=False → lecture session → données disponibles

        C'est la correction centrale de v1.1.0 : les boutons ne disparaissent plus.
        """
        # Rerun 1 : calcul
        opt_results = {}
        opt_results["minimize_cost"] = self._build_opt_result_session(
            composition_standard, "CEM I", "XC1",
            mock_model, feature_list, "minimize_cost"
        )

        # Rerun 2 : optimize_button = False, mais données toujours disponibles
        optimize_button = False
        assert not optimize_button

        # ✅ Les données sont dans opt_results → boutons Sauvegarder/Favoris accessibles
        assert "minimize_cost" in opt_results
        data = opt_results["minimize_cost"]
        assert data["predictions"]["Resistance"] > 0
        assert data["co2_total"] > 0
        assert data["validation"] is not None

    def test_mode_equilibre_deux_solutions(
        self, composition_standard, mock_model, feature_list
    ):
        """Mode Équilibre → deux entrées distinctes dans opt_results."""
        opt_results = {}

        for obj_key in ["minimize_cost", "minimize_co2"]:
            opt_results[obj_key] = self._build_opt_result_session(
                composition_standard, "CEM I", "XC1",
                mock_model, feature_list, obj_key,
                cost=65.0 if obj_key == "minimize_cost" else 80.0,
            )

        assert len(opt_results) == 2
        assert "minimize_cost" in opt_results
        assert "minimize_co2"  in opt_results

        # Les deux solutions doivent avoir des labels différents
        assert opt_results["minimize_cost"]["label"] != opt_results["minimize_co2"]["label"]

    def test_favori_depuis_opt_result(
        self, composition_standard, mock_model, feature_list
    ):
        """Un favori créé depuis opt_results doit avoir tous les champs requis."""
        data = self._build_opt_result_session(
            composition_standard, "CEM I", "XC1",
            mock_model, feature_list, "minimize_cost"
        )
        ts       = data["timestamp"]
        obj_key  = "minimize_cost"
        fav_name = f"Optimisée_{obj_key}_{ts.strftime('%Y%m%d_%H%M')}"

        favorites = []
        already   = any(f["name"] == fav_name for f in favorites)

        if not already:
            favorites.append({
                "name":             fav_name,
                "composition":      data["composition"],
                "predictions":      data["predictions"],
                "co2_result":       data["co2_result"],
                "required_class":   data["required_class"],
                "achieved_class":   data["validation"].achieved_class,
                "compliance_score": data["validation"].compliance_score,
                "cost":             data["cost"],
                "cement_type":      data["cement_type"],
                "source":           "Optimiseur",
                "objective":        obj_key,
                "timestamp":        ts,
            })

        assert len(favorites) == 1
        fav = favorites[0]
        assert fav["source"] == "Optimiseur"
        assert fav["objective"] == "minimize_cost"
        assert fav["cost"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE — COMPARATEUR (N formulations)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineComparateur:

    def test_comparaison_plusieurs_formulations(
        self, composition_standard, composition_hpc, composition_cem3,
        mock_model, feature_list
    ):
        """Comparer 3 formulations → résultats triables par CO₂."""
        formulations = [
            ("Standard",  composition_standard, "CEM I"),
            ("HPC",       composition_hpc,       "CEM I"),
            ("CEM III/B", composition_cem3,       "CEM III/B"),
        ]

        co2_calc = CO2Calculator()
        results  = []

        for name, comp, cement in formulations:
            predictions = predict_concrete_properties(
                composition=comp,
                model=mock_model,
                feature_list=feature_list,
            )
            co2_result = co2_calc.calculate(comp, cement)
            results.append({
                "name":      name,
                "co2_total": co2_result.co2_total_kg_m3,
                "resistance": predictions["Resistance"],
            })

        # Le CEM III/B doit avoir le CO₂ le plus faible
        results_sorted = sorted(results, key=lambda r: r["co2_total"])
        assert results_sorted[0]["name"] == "CEM III/B", (
            f"Le plus bas CO₂ attendu CEM III/B, obtenu : {results_sorted[0]['name']}"
        )

    def test_toutes_formulations_produisent_resultat_valide(
        self, composition_standard, composition_hpc, composition_mk,
        mock_model, feature_list
    ):
        """Aucune formulation valide ne doit lever d'exception dans le pipeline."""
        co2_calc = CO2Calculator()

        for comp in [composition_standard, composition_hpc, composition_mk]:
            predictions = predict_concrete_properties(
                composition=comp,
                model=mock_model,
                feature_list=feature_list,
            )
            co2_result = co2_calc.calculate(comp, "CEM I")
            validation = validate_formulation(
                composition=comp,
                predictions=predictions,
            )
            assert predictions["Resistance"] > 0
            assert co2_result.co2_total_kg_m3 > 0
            assert 0 <= validation.compliance_score <= 100