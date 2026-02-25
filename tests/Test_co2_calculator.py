"""
tests/test_co2_calculator.py
═════════════════════════════
Tests unitaires — CO2Calculator & co2_database

Couvre :
  - Calcul correct pour chaque type de ciment
  - Cohérence des facteurs CO₂ (ordre de grandeur physique)
  - Validation des formulations invalides
  - get_breakdown_percentages() → somme à 100 %
  - get_environmental_grade() → mapping cohérent
  - suggest_reduction() → suggestions pertinentes
  - Cas limites (additions à zéro, superplastifiant nul)
"""

import pytest
import math
from app.core.co2_calculator import CO2Calculator, quick_calculate_co2, get_environmental_grade
from config.co2_database import (
    CEMENT_CO2_KG_PER_TONNE,
    CO2_FACTORS_KG_PER_TONNE,
    get_cement_co2,
    get_co2_class,
    CO2Result,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS CALCUL DE BASE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCO2CalculatorBase:

    def test_calcul_cem1_valeur_attendue(self, composition_standard):
        """CEM I + 350 kg ciment → CO₂ total dans la plage attendue (300-500 kg)."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")

        assert result.co2_total_kg_m3 > 0
        assert 300 < result.co2_total_kg_m3 < 500, (
            f"CO₂ CEM I hors plage : {result.co2_total_kg_m3:.1f} kg/m³"
        )

    def test_calcul_cem3b_inferieur_cem1(self, composition_standard):
        """CEM III/B doit produire significativement moins de CO₂ que CEM I (~60%)."""
        calc      = CO2Calculator()
        res_cem1  = calc.calculate(composition_standard, "CEM I")
        res_cem3b = calc.calculate(composition_standard, "CEM III/B")

        ratio = res_cem3b.co2_total_kg_m3 / res_cem1.co2_total_kg_m3
        assert ratio < 0.60, (
            f"CEM III/B devrait réduire > 40 %, ratio obtenu : {ratio:.2%}"
        )

    def test_contribution_ciment_dominante(self, composition_standard):
        """Le ciment doit représenter > 70 % de l'empreinte totale (CEM I)."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")

        pct_ciment = result.co2_ciment / result.co2_total_kg_m3
        assert pct_ciment > 0.70, (
            f"Part ciment trop faible : {pct_ciment:.2%}"
        )

    def test_additions_minerales_reduisent_co2(self, composition_standard, composition_hpc):
        """HPC avec laitier doit avoir un CO₂ inférieur pour même ciment total."""
        calc     = CO2Calculator()
        res_std  = calc.calculate(composition_standard, "CEM I")
        res_hpc  = calc.calculate(composition_hpc, "CEM I")

        # Le HPC a plus de liant mais moins de clinker → CO₂/liant plus faible
        co2_par_liant_std = res_std.co2_total_kg_m3 / composition_standard["Ciment"]
        co2_par_liant_hpc = res_hpc.co2_total_kg_m3 / (
            composition_hpc["Ciment"] + composition_hpc["Laitier"]
        )
        assert co2_par_liant_hpc < co2_par_liant_std

    def test_co2_result_champs_positifs(self, composition_standard):
        """Tous les champs CO₂ doivent être >= 0."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")

        for field in [
            result.co2_ciment, result.co2_laitier, result.co2_cendres,
            result.co2_sable, result.co2_gravier, result.co2_eau, result.co2_adjuvants,
        ]:
            assert field >= 0, f"Champ CO₂ négatif : {field}"

    def test_somme_constituants_egale_total(self, composition_standard):
        """Somme des CO₂ par constituant = CO₂ total (tolérance arrondi)."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")

        somme = (
            result.co2_ciment + result.co2_laitier + result.co2_cendres
            + result.co2_sable + result.co2_gravier
            + result.co2_eau + result.co2_adjuvants
        )
        assert math.isclose(somme, result.co2_total_kg_m3, rel_tol=0.01), (
            f"Somme {somme:.2f} ≠ total {result.co2_total_kg_m3:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS TYPES DE CIMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypesCiment:

    def test_tous_les_types_calculent(self, composition_standard, all_cement_types):
        """Chaque type de ciment doit produire un résultat valide."""
        calc = CO2Calculator()
        for cement_type in all_cement_types:
            result = calc.calculate(composition_standard, cement_type)
            assert result.co2_total_kg_m3 > 0, f"CO₂ nul pour {cement_type}"

    def test_ordre_co2_croissant_logique(self, composition_standard):
        """CEM III/C < CEM III/B < CEM III/A < CEM I (ordre physique attendu)."""
        calc = CO2Calculator()
        co2 = {
            ct: calc.calculate(composition_standard, ct).co2_total_kg_m3
            for ct in ["CEM III/C", "CEM III/B", "CEM III/A", "CEM I"]
        }
        assert co2["CEM III/C"] < co2["CEM III/B"] < co2["CEM III/A"] < co2["CEM I"], (
            f"Ordre CO₂ incohérent : {co2}"
        )

    def test_facteur_cem1_dans_plage(self):
        """Facteur CO₂ du CEM I doit être entre 700 et 900 kg CO₂/t (ATILH 2024)."""
        factor = CEMENT_CO2_KG_PER_TONNE["CEM I"]
        assert 700 < factor < 900, f"Facteur CEM I hors plage : {factor}"

    def test_facteur_cem3b_inferieur_300(self):
        """Facteur CO₂ du CEM III/B doit être < 300 kg CO₂/t."""
        factor = CEMENT_CO2_KG_PER_TONNE["CEM III/B"]
        assert factor < 300, f"Facteur CEM III/B trop élevé : {factor}"

    def test_type_inconnu_fallback_cem1(self, composition_standard):
        """Un type inconnu doit utiliser le facteur CEM I (fallback)."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM_INCONNU")
        # Doit calculer sans lever d'exception
        assert result.co2_total_kg_m3 > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS VALIDATION FORMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationFormulation:

    def test_ciment_negatif_leve_valueerror(self, composition_invalid_negative):
        """Dosage ciment négatif → ValueError."""
        calc = CO2Calculator()
        with pytest.raises(ValueError, match="négatif|invalide"):
            calc.calculate(composition_invalid_negative, "CEM I")

    def test_cle_manquante_leve_valueerror(self, composition_missing_key):
        """Clé obligatoire manquante → ValueError."""
        calc = CO2Calculator()
        with pytest.raises(ValueError, match="manquant|obligatoire"):
            calc.calculate(composition_missing_key, "CEM I")

    def test_ciment_zero_leve_valueerror(self, composition_standard):
        """Dosage ciment = 0 → ValueError."""
        calc = CO2Calculator()
        comp = dict(composition_standard)
        comp["Ciment"] = 0.0
        with pytest.raises(ValueError):
            calc.calculate(comp, "CEM I")

    def test_additions_zero_acceptees(self, composition_standard):
        """Laitier = CendresVolantes = Metakaolin = 0 → calcul valide."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")
        assert result.co2_laitier == 0.0
        assert result.co2_cendres == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS BREAKDOWN PERCENTAGES
# ═══════════════════════════════════════════════════════════════════════════════

class TestBreakdownPercentages:

    def test_somme_percentages_100(self, composition_standard):
        """Somme des pourcentages doit être ≈ 100 %."""
        calc      = CO2Calculator()
        result    = calc.calculate(composition_standard, "CEM I")
        breakdown = calc.get_breakdown_percentages(result)

        total_pct = sum(breakdown.values())
        assert math.isclose(total_pct, 100.0, rel_tol=0.02), (
            f"Somme des % : {total_pct:.2f}"
        )

    def test_cles_attendues_presentes(self, composition_standard):
        """Toutes les clés attendues doivent être présentes."""
        calc      = CO2Calculator()
        result    = calc.calculate(composition_standard, "CEM I")
        breakdown = calc.get_breakdown_percentages(result)

        expected = {"Ciment", "Laitier", "Cendres", "Sable", "Gravier", "Eau", "Adjuvants"}
        assert expected == set(breakdown.keys())

    def test_percentages_positifs(self, composition_standard):
        """Tous les pourcentages doivent être >= 0."""
        calc      = CO2Calculator()
        result    = calc.calculate(composition_standard, "CEM I")
        breakdown = calc.get_breakdown_percentages(result)

        for k, v in breakdown.items():
            assert v >= 0, f"Pourcentage négatif pour {k} : {v}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS GRADE ENVIRONNEMENTAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnvironmentalGrade:

    @pytest.mark.parametrize("co2,expected_classe", [
        (150.0, "Très Faible"),
        (240.0, "Faible"),
        (310.0, "Moyen"),
        (380.0, "Élevé"),
        (500.0, "Très Élevé"),
    ])
    def test_classes_correctes(self, co2, expected_classe):
        classe, emoji, color = get_environmental_grade(co2)
        assert classe == expected_classe, (
            f"CO₂={co2} → attendu '{expected_classe}', obtenu '{classe}'"
        )

    def test_retour_3_elements(self):
        result = get_environmental_grade(350.0)
        assert len(result) == 3

    def test_emoji_non_vide(self):
        _, emoji, _ = get_environmental_grade(350.0)
        assert emoji  # non vide

    def test_couleur_hex_format(self):
        _, _, color = get_environmental_grade(350.0)
        assert color.startswith("#"), f"Couleur invalide : {color}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS SUGGEST REDUCTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuggestReduction:

    def test_structure_retour(self, composition_standard):
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")
        sugg   = calc.suggest_reduction(result, target_reduction_percent=30.0)

        assert "current_co2"      in sugg
        assert "target_co2"       in sugg
        assert "reduction_needed" in sugg
        assert "suggestions"      in sugg
        assert isinstance(sugg["suggestions"], list)

    def test_target_co2_inferieur_current(self, composition_standard):
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")
        sugg   = calc.suggest_reduction(result, target_reduction_percent=30.0)

        assert sugg["target_co2"] < sugg["current_co2"]

    def test_suggestions_non_vides_cem1(self, composition_standard):
        """CEM I avec peu de laitier → au moins 2 suggestions."""
        calc   = CO2Calculator()
        result = calc.calculate(composition_standard, "CEM I")
        sugg   = calc.suggest_reduction(result)

        assert len(sugg["suggestions"]) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS QUICK_CALCULATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuickCalculate:

    def test_retourne_float(self, composition_standard):
        result = quick_calculate_co2(composition_standard, "CEM I")
        assert isinstance(result, float)

    def test_coherent_avec_calculateur(self, composition_standard):
        calc      = CO2Calculator()
        ref       = calc.calculate(composition_standard, "CEM I").co2_total_kg_m3
        quick_val = quick_calculate_co2(composition_standard, "CEM I")
        assert math.isclose(ref, quick_val, rel_tol=0.001)