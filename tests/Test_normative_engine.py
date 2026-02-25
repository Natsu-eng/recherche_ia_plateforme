"""
tests/test_normative_engine.py
══════════════════════════════
Tests unitaires — EN206ExposureEngine, ExposureCategory, ExposureAdvisor

Couvre :
  - ExposureCategory.from_class_name() — le bug corrigé (XC, XD, XS, XA, XF)
  - EN206ExposureEngine.analyze() — résultat structuré
  - Règles E/L et fc selon chaque classe
  - IndustrialEN206Engine — façade unifiée
  - ExposureAdvisor — recommandations non vides
  - Cas limites : classe inconnue, liste vide
"""

import pytest
from app.core.normative_engines import (
    EN206ExposureEngine,
    ExposureCategory,
    ExposureAdvisor,
    IndustrialEN206Engine,
    ExposureResult,
    get_exposure_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ExposureCategory.from_class_name()
# BUG CORRIGÉ : comparaison category.value vs prefix → cls[prefix]
# ═══════════════════════════════════════════════════════════════════════════════

class TestExposureCategoryFromClassName:

    @pytest.mark.parametrize("class_name,expected_category", [
        ("XC1", ExposureCategory.XC),
        ("XC4", ExposureCategory.XC),
        ("XD1", ExposureCategory.XD),
        ("XD3", ExposureCategory.XD),
        ("XS1", ExposureCategory.XS),
        ("XS3", ExposureCategory.XS),
        ("XF1", ExposureCategory.XF),
        ("XA1", ExposureCategory.XA),
    ])
    def test_mapping_correct(self, class_name, expected_category):
        """from_class_name doit retourner la bonne catégorie pour chaque préfixe."""
        result = ExposureCategory.from_class_name(class_name)
        assert result == expected_category, (
            f"{class_name} → attendu {expected_category}, obtenu {result}"
        )

    def test_classe_inconnue_retourne_none_ou_leve(self):
        """Classe inconnue (ex: 'XX1') → None ou KeyError selon implémentation."""
        try:
            result = ExposureCategory.from_class_name("XX1")
            assert result is None, "Classe inconnue devrait retourner None"
        except (KeyError, ValueError):
            pass   # comportement acceptable

    def test_prefix_2_chars_correct(self):
        """Le prefix doit être les 2 premiers caractères (pas plus)."""
        assert ExposureCategory.from_class_name("XC1") == ExposureCategory.XC
        assert ExposureCategory.from_class_name("XD2") == ExposureCategory.XD


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS EN206ExposureEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestEN206ExposureEngine:

    @pytest.fixture
    def engine(self):
        return EN206ExposureEngine()

    def test_analyze_retourne_exposure_result(
        self, engine, composition_standard, predictions_standard
    ):
        result = engine.analyze(composition_standard, predictions_standard)
        assert isinstance(result, ExposureResult)

    def test_achieved_class_format(
        self, engine, composition_standard, predictions_standard
    ):
        result = engine.analyze(composition_standard, predictions_standard)
        if result.achieved_class:
            import re
            assert re.match(r"^X[CDSAF]\d$", result.achieved_class), (
                f"Format invalide : {result.achieved_class}"
            )

    def test_hpc_atteint_classe_plus_haute(
        self, engine, composition_hpc, predictions_hpc,
        composition_standard, predictions_standard
    ):
        """HPC (E/L=0.31, R=58) doit atteindre une classe >= standard (E/L=0.50, R=38)."""
        res_std = engine.analyze(composition_standard, predictions_standard)
        res_hpc = engine.analyze(composition_hpc, predictions_hpc)

        def class_level(cls):
            if cls is None:
                return 0
            return int(cls[-1]) if cls[-1].isdigit() else 0

        assert class_level(res_hpc.achieved_class) >= class_level(res_std.achieved_class), (
            f"HPC ({res_hpc.achieved_class}) devrait être ≥ standard ({res_std.achieved_class})"
        )

    def test_el_trop_eleve_bloque_classe_haute(self, engine, composition_standard):
        """E/L=0.75 ne peut pas atteindre XD3 (E/L_max=0.40)."""
        predictions_mauvaises = {
            "Resistance":      22.0,
            "Diffusion_Cl":    14.0,
            "Carbonatation":   22.0,
            "Ratio_E_L":        0.75,
            "Liant_Total":    230.0,
            "Pct_Substitution": 0.0,
        }
        result = engine.analyze(composition_standard, predictions_mauvaises)

        # La classe atteinte ne devrait pas être XD2 ou XD3
        if result.achieved_class:
            assert not result.achieved_class.startswith("XD") or result.achieved_class == "XD1"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ExposureAdvisor
# ═══════════════════════════════════════════════════════════════════════════════

class TestExposureAdvisor:

    @pytest.fixture
    def advisor(self):
        return ExposureAdvisor()

    def test_recommandations_non_vides(
        self, advisor, composition_standard, predictions_standard
    ):
        """recommend() doit retourner au moins une recommandation."""
        recs = advisor.recommend(composition_standard, predictions_standard)
        assert len(recs) > 0, "Aucune recommandation générée"

    def test_recommandations_ont_attributs(
        self, advisor, composition_standard, predictions_standard
    ):
        """Chaque recommandation doit avoir action et impact."""
        recs = advisor.recommend(composition_standard, predictions_standard)
        for rec in recs:
            assert hasattr(rec, "action") or isinstance(rec, dict), (
                f"Recommandation sans attribut 'action' : {rec}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS IndustrialEN206Engine (façade)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIndustrialEngine:

    @pytest.fixture
    def industrial(self):
        return IndustrialEN206Engine()

    def test_analyze_ne_crash_pas(
        self, industrial, composition_standard, predictions_standard
    ):
        """La façade unifiée ne doit pas lever d'exception sur formulation valide."""
        result = industrial.analyze(composition_standard, predictions_standard)
        assert result is not None

    def test_analyze_hpc_ne_crash_pas(
        self, industrial, composition_hpc, predictions_hpc
    ):
        result = industrial.analyze(composition_hpc, predictions_hpc)
        assert result is not None

    def test_get_exposure_engine_retourne_instance(self):
        engine = get_exposure_engine()
        assert engine is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS CAS LIMITES
# ═══════════════════════════════════════════════════════════════════════════════

class TestCasLimites:

    def test_predictions_vides_ne_crash_pas(self, composition_standard):
        """Prédictions partielles ne doivent pas faire crasher l'engine."""
        engine       = EN206ExposureEngine()
        predictions  = {"Resistance": 30.0}   # autres clés manquantes
        try:
            result = engine.analyze(composition_standard, predictions)
            # Si pas d'exception → OK
        except (KeyError, AttributeError):
            pytest.fail("L'engine crashe sur prédictions partielles")

    def test_toutes_classes_xc_analysees(
        self, composition_standard, predictions_standard
    ):
        """L'engine doit traiter XC1-XC4 sans exception."""
        engine = EN206ExposureEngine()
        for classe in ["XC1", "XC2", "XC3", "XC4"]:
            result = engine.analyze(
                composition_standard,
                predictions_standard,
                target_class=classe,
            )
            assert result is not None, f"Résultat None pour {classe}"