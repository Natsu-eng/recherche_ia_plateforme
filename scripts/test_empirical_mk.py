# scripts/test_empirical_mk.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.mk_corrector import get_mk_corrector

corrector = get_mk_corrector()

print("="*60)
print("🧪 TEST CORRECTEUR EMPIRIQUE MK")
print("="*60)

# Composition de base
comp_base = {
    'Ciment': 350,
    'Laitier': 0,
    'CendresVolantes': 0,
    'Eau': 175,
    'Superplastifiant': 0,
    'GravilonsGros': 1000,
    'SableFin': 800,
    'Age': 28
}

# Tester différentes doses
print("\n📈 EFFET DE LA DOSE MK:")
print("-" * 40)
for mk in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    comp = comp_base.copy()
    comp['Metakaolin'] = mk
    corr = corrector.predict_correction(comp)
    print(f"MK={mk:3d} kg → correction={corr:6.2f} MPa")

# Tester influence de l'âge
print("\n📈 INFLUENCE DE L'ÂGE (MK=35kg):")
print("-" * 40)
comp = comp_base.copy()
comp['Metakaolin'] = 35
for age in [7, 14, 28, 56, 90, 180]:
    comp['Age'] = age
    corr = corrector.predict_correction(comp)
    print(f"Age={age:3d} jours → correction={corr:.2f} MPa")

# Tester influence du ratio E/L
print("\n📈 INFLUENCE DU RATIO E/L (MK=35kg):")
print("-" * 40)
comp = comp_base.copy()
comp['Metakaolin'] = 35
comp['Age'] = 28
for eau in [150, 160, 170, 180, 190, 200]:
    comp['Eau'] = eau
    comp['Ciment'] = 350
    corr = corrector.predict_correction(comp)
    ratio = eau / (350 + 35)
    print(f"E/L={ratio:.3f} → correction={corr:.2f} MPa")