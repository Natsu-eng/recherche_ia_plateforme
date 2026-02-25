"""
tests/test_validator.py
═══════════════════════
Tests unitaires — validate_formulation() & ValidationReport

Couvre :
  - Conformité correcte pour formulations valides vs invalides
  - Détection des violations E/L, résistance, classe exposition
  - compliance_with_required (classe exigée vs atteinte)
  - Alertes : sévérité, catégorie, norm_ref renseigné
  - Score de conformité : borné [0, 100]
  - achieved_class : format XC/XD/XS suivi d'un chiffre
  - resistance_class : format C{n}/{m}
"""

import pytest
import re
from app.core.validator import validate_formulation, ValidationReport, ValidationAlert, Severity


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS STRUCTURE RETOUR
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationReportStructure:

    def test_retourne_validation_report(self, composition_standard, predictions_standard):
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XC1",
        )
        assert isinstance(report, ValidationReport)

    def test_champs_obligatoires_presents(self, composition_standard, predictions_standard):
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        assert hasattr(report, "compliance_score")
        assert hasattr(report, "alerts")
        assert hasattr(report, "achieved_class")
        assert hasattr(report, "resistance_class")
        assert hasattr(report, "compliance_with_required")

    def test_score_borne_0_100(self, composition_standard, predictions_standard):
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        assert 0 <= report.compliance_score <= 100, (
            f"Score hors bornes : {report.compliance_score}"
        )

    def test_alerts_est_liste(self, composition_standard, predictions_standard):
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        assert isinstance(report.alerts, list)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS CONFORMITÉ BASIQUE
# ═══════════════════════════════════════════════════════════════════════════════

class TestConformiteBasique:

    def test_formulation_standard_conforme_xc1(
        self, composition_standard, predictions_standard
    ):
        """Béton C30/37 standard doit être conforme à XC1 (exigences faibles)."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XC1",
        )
        assert report.compliance_score >= 70, (
            f"Score trop faible pour XC1 : {report.compliance_score}"
        )
        assert report.compliance_with_required, "Standard devrait être conforme à XC1"

    def test_hpc_conforme_xc4(self, composition_hpc, predictions_hpc):
        """HPC (R=58 MPa, E/L=0.31) doit être conforme aux classes sévères XC4."""
        report = validate_formulation(
            composition=composition_hpc,
            predictions=predictions_hpc,
            required_class="XC4",
        )
        assert report.compliance_with_required, "HPC devrait être conforme à XC4"

    def test_formulation_el_eleve_non_conforme_xd3(
        self, composition_standard, predictions_standard
    ):
        """E/L=0.50 ne respecte pas XD3 (E/L_max ≤ 0.40)."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XD3",
        )
        assert not report.compliance_with_required, (
            "E/L=0.50 ne devrait pas être conforme à XD3"
        )

    def test_sans_required_class_pas_crash(self, composition_standard, predictions_standard):
        """validate_formulation sans required_class ne doit pas lever d'exception."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        assert report is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS CLASSES D'EXPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassesExposition:

    def test_achieved_class_format_valide(self, composition_standard, predictions_standard):
        """achieved_class doit être du format XC1, XD2, XS3... ou None."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        if report.achieved_class is not None:
            assert re.match(r"^X[CDSA]\d$", report.achieved_class), (
                f"Format achieved_class invalide : {report.achieved_class}"
            )

    def test_resistance_class_format_valide(self, composition_standard, predictions_standard):
        """resistance_class doit être du format C20/25, C30/37..."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        if report.resistance_class is not None:
            assert re.match(r"^C\d+/\d+$", report.resistance_class), (
                f"Format resistance_class invalide : {report.resistance_class}"
            )

    @pytest.mark.parametrize("required_class", ["XC1", "XC2", "XC3", "XC4"])
    def test_classes_xc_traitees(
        self, composition_standard, predictions_standard, required_class
    ):
        """Toutes les classes XC doivent être traitées sans exception."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class=required_class,
        )
        assert isinstance(report.compliance_with_required, bool)

    @pytest.mark.parametrize("required_class", ["XD1", "XD2", "XD3"])
    def test_classes_xd_traitees(
        self, composition_hpc, predictions_hpc, required_class
    ):
        """Toutes les classes XD doivent être traitées sans exception."""
        report = validate_formulation(
            composition=composition_hpc,
            predictions=predictions_hpc,
            required_class=required_class,
        )
        assert isinstance(report.compliance_with_required, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ALERTES
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertes:

    def test_alerte_el_eleve(self, composition_standard):
        """E/L > 0.65 doit générer une alerte WARNING ou ERROR."""
        predictions = {
            "Resistance":      25.0,
            "Diffusion_Cl":     9.0,
            "Carbonatation":   18.0,
            "Ratio_E_L":        0.70,    # E/L trop élevé
            "Liant_Total":    250.0,
            "Pct_Substitution": 0.0,
        }
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions,
        )
        el_alerts = [
            a for a in report.alerts
            if "E/L" in a.message or "eau" in a.message.lower() or "ratio" in a.message.lower()
        ]
        assert len(el_alerts) > 0, "Aucune alerte pour E/L=0.70"
        assert any(
            a.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL)
            for a in el_alerts
        )

    def test_alerte_resistance_faible(self, composition_standard):
        """Résistance < 20 MPa doit générer une alerte."""
        predictions_faibles = {
            "Resistance":      15.0,    # très faible
            "Diffusion_Cl":    10.0,
            "Carbonatation":   20.0,
            "Ratio_E_L":        0.70,
            "Liant_Total":    220.0,
            "Pct_Substitution": 0.0,
        }
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_faibles,
        )
        r_alerts = [
            a for a in report.alerts
            if "résistance" in a.message.lower() or "resistance" in a.message.lower()
            or "MPa" in a.message
        ]
        assert len(r_alerts) > 0, "Aucune alerte pour résistance=15 MPa"

    def test_alertes_ont_message_non_vide(self, composition_standard, predictions_standard):
        """Chaque alerte doit avoir message et recommendation non vides."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        for alert in report.alerts:
            assert alert.message.strip(),        f"Message vide sur alerte {alert}"
            assert alert.recommendation.strip(), f"Recommandation vide sur alerte {alert}"

    def test_alertes_severite_valide(self, composition_standard, predictions_standard):
        """Chaque alerte doit avoir une sévérité valide."""
        report = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
        )
        valid_severities = set(Severity)
        for alert in report.alerts:
            assert alert.severity in valid_severities, (
                f"Sévérité invalide : {alert.severity}"
            )

    def test_formulation_excellente_peu_alertes(self, composition_hpc, predictions_hpc):
        """HPC doit générer peu d'alertes CRITICAL/ERROR."""
        report = validate_formulation(
            composition=composition_hpc,
            predictions=predictions_hpc,
            required_class="XC3",
        )
        critiques = [
            a for a in report.alerts
            if a.severity in (Severity.CRITICAL, Severity.ERROR)
        ]
        assert len(critiques) <= 1, (
            f"Trop d'alertes critiques pour HPC : {len(critiques)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS SCORE CONFORMITÉ
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreConformite:

    def test_hpc_score_superieur_standard(
        self, composition_standard, predictions_standard,
        composition_hpc, predictions_hpc
    ):
        """HPC doit avoir un score de conformité supérieur au béton standard."""
        report_std = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XC3",
        )
        report_hpc = validate_formulation(
            composition=composition_hpc,
            predictions=predictions_hpc,
            required_class="XC3",
        )
        assert report_hpc.compliance_score >= report_std.compliance_score, (
            f"HPC ({report_hpc.compliance_score}) < Standard ({report_std.compliance_score})"
        )

    def test_score_diminue_avec_contrainte_severe(
        self, composition_standard, predictions_standard
    ):
        """Score pour XC4 doit être ≤ score pour XC1 (contrainte plus sévère)."""
        report_xc1 = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XC1",
        )
        report_xc4 = validate_formulation(
            composition=composition_standard,
            predictions=predictions_standard,
            required_class="XC4",
        )
        assert report_xc4.compliance_score <= report_xc1.compliance_score, (
            "XC4 ne devrait pas avoir un score supérieur à XC1 pour même formulation"
        )