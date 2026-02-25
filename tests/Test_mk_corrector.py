"""
tests/test_mk_corrector.py
══════════════════════════
Tests unitaires — MKCorrector v4.0 (modèle empirique)

Couvre :
  - predict_correction() retourne 0 si MK=0
  - Correction positive pour MK > 0
  - Forme en cloche : pic entre 40-60 kg/m³
  - Facteur âge : correction plus élevée à 90j qu'à 7j
  - Facteur E/L : correction diminue pour E/L > 0.50
  - Clip physique : [1, 25] MPa
  - Synergie superplastifiant
  - save() / load() round-trip
"""

import pytest
import os
import tempfile
import numpy as np
from app.core.mk_corrector import MKCorrector, get_mk_corrector


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES LOCALES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def corrector():
    return MKCorrector()


@pytest.fixture
def base_composition():
    """Composition de base sans MK."""
    return {
        "Ciment":           300.0,
        "Laitier":            0.0,
        "CendresVolantes":    0.0,
        "Eau":              160.0,
        "SableFin":         800.0,
        "GravilonsGros":   1000.0,
        "Superplastifiant":   5.0,
        "Age":               28.0,
        "Metakaolin":         0.0,
    }


def with_mk(base: dict, mk: float, age: float = 28.0, sp: float = 5.0, eau: float = 160.0) -> dict:
    """Helper : copie la composition avec les valeurs MK/âge/SP/eau spécifiées."""
    c = dict(base)
    c["Metakaolin"] = mk
    c["Age"]        = age
    c["Superplastifiant"] = sp
    c["Eau"]        = eau
    return c


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS VALEURS DE BASE
# ═══════════════════════════════════════════════════════════════════════════════

class TestValeurBase:

    def test_correction_zero_sans_mk(self, corrector, base_composition):
        """MK=0 → correction = 0.0 MPa."""
        correction = corrector.predict_correction(base_composition)
        assert correction == 0.0

    def test_correction_positive_avec_mk(self, corrector, base_composition):
        """MK > 0 → correction strictement positive."""
        comp       = with_mk(base_composition, mk=40.0)
        correction = corrector.predict_correction(comp)
        assert correction > 0.0, f"Correction attendue > 0, obtenu {correction}"

    def test_correction_dans_plage_physique(self, corrector, base_composition):
        """Correction bornée dans [1, 25] MPa pour tout MK valide."""
        for mk in [5, 10, 20, 40, 50, 60, 80, 100]:
            comp       = with_mk(base_composition, mk=float(mk))
            correction = corrector.predict_correction(comp)
            assert 1.0 <= correction <= 25.0, (
                f"MK={mk} → correction={correction:.2f} hors [1, 25]"
            )

    def test_correction_retourne_float(self, corrector, base_composition):
        comp = with_mk(base_composition, mk=40.0)
        result = corrector.predict_correction(comp)
        assert isinstance(result, float)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS FORME EN CLOCHE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormeCloche:

    def test_pic_entre_30_et_70kg(self, corrector, base_composition):
        """
        La correction doit être maximale entre 30 et 70 kg/m³ de MK
        (correspondant à 10-15% de substitution avec 300 kg de ciment).
        """
        corrections = {
            mk: corrector.predict_correction(with_mk(base_composition, mk=float(mk)))
            for mk in [5, 15, 30, 45, 60, 80, 120]
        }
        peak_mk     = max(corrections, key=corrections.get)
        assert 20 <= peak_mk <= 70, (
            f"Pic attendu entre 20-70 kg, obtenu à {peak_mk} kg\n"
            f"Corrections : {corrections}"
        )

    def test_faible_dose_inferieur_dose_optimale(self, corrector, base_composition):
        """Correction à 5 kg doit être inférieure à la correction optimale."""
        corr_5  = corrector.predict_correction(with_mk(base_composition, mk=5.0))
        corr_45 = corrector.predict_correction(with_mk(base_composition, mk=45.0))
        assert corr_5 < corr_45, (
            f"Correction 5 kg ({corr_5:.2f}) >= optimal 45 kg ({corr_45:.2f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS FACTEUR ÂGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFacteurAge:

    def test_correction_augmente_avec_age(self, corrector, base_composition):
        """Correction à 90j > correction à 7j (réaction pouzzolanique lente)."""
        corr_7j  = corrector.predict_correction(with_mk(base_composition, mk=45.0, age=7.0))
        corr_28j = corrector.predict_correction(with_mk(base_composition, mk=45.0, age=28.0))
        corr_90j = corrector.predict_correction(with_mk(base_composition, mk=45.0, age=90.0))

        assert corr_7j <= corr_28j, (
            f"7j ({corr_7j:.2f}) devrait être ≤ 28j ({corr_28j:.2f})"
        )
        assert corr_28j <= corr_90j, (
            f"28j ({corr_28j:.2f}) devrait être ≤ 90j ({corr_90j:.2f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS FACTEUR E/L
# ═══════════════════════════════════════════════════════════════════════════════

class TestFacteurEL:

    def test_correction_diminue_haut_el(self, corrector, base_composition):
        """
        E/L élevé (0.65) doit donner correction ≤ E/L compact (0.35).
        MK plus efficace dans béton compact.
        """
        # E/L ≈ 0.35 → eau 105 pour ciment+mk ≈ 300+45 = 345
        corr_compact = corrector.predict_correction(
            with_mk(base_composition, mk=45.0, eau=120.0)
        )
        # E/L ≈ 0.60 → eau 207
        corr_fluide = corrector.predict_correction(
            with_mk(base_composition, mk=45.0, eau=210.0)
        )
        assert corr_fluide <= corr_compact, (
            f"E/L élevé ({corr_fluide:.2f}) devrait être ≤ compact ({corr_compact:.2f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS SYNERGIE SUPERPLASTIFIANT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSynergieSuper:

    def test_sp_augmente_correction(self, corrector, base_composition):
        """Superplastifiant > 0 doit légèrement augmenter la correction MK."""
        corr_sans_sp = corrector.predict_correction(with_mk(base_composition, mk=45.0, sp=0.0))
        corr_avec_sp = corrector.predict_correction(with_mk(base_composition, mk=45.0, sp=8.0))
        # La correction avec SP doit être ≥ sans SP
        assert corr_avec_sp >= corr_sans_sp, (
            f"SP=8 ({corr_avec_sp:.2f}) devrait être ≥ SP=0 ({corr_sans_sp:.2f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS SAVE / LOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestSaveLoad:

    def test_save_load_roundtrip(self, corrector, base_composition, tmp_path):
        """Les paramètres sauvegardés et rechargés donnent les mêmes corrections."""
        path  = str(tmp_path / "mk_test.pkl")
        comp  = with_mk(base_composition, mk=45.0)

        corr_avant = corrector.predict_correction(comp)
        corrector.save(path)

        corrector2 = MKCorrector(model_path=path)
        corr_apres = corrector2.predict_correction(comp)

        assert abs(corr_avant - corr_apres) < 0.01, (
            f"Round-trip échoué : {corr_avant:.4f} → {corr_apres:.4f}"
        )

    def test_save_retourne_true_succes(self, corrector, tmp_path):
        path    = str(tmp_path / "mk_save_test.pkl")
        success = corrector.save(path)
        assert success is True
        assert os.path.exists(path)

    def test_load_fichier_inexistant_ne_crash_pas(self):
        """Charger un fichier inexistant ne doit pas lever d'exception."""
        corrector = MKCorrector(model_path="/chemin/inexistant/model.pkl")
        # L'instance doit être opérationnelle avec les paramètres par défaut
        assert corrector.params["A"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS SINGLETON get_mk_corrector
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:

    def test_get_mk_corrector_retourne_instance(self):
        corrector = get_mk_corrector()
        assert isinstance(corrector, MKCorrector)

    def test_get_mk_corrector_meme_instance(self):
        """Deux appels doivent retourner la même instance (singleton)."""
        c1 = get_mk_corrector()
        c2 = get_mk_corrector()
        assert c1 is c2