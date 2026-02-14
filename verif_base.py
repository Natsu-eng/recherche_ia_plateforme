"""
═══════════════════════════════════════════════════════════════════════════════
🎯 VÉRIFICATION FINALE - Bouton Sauvegarder
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   VÉRIFICATION FINALE - ÉTAPE PAR ÉTAPE                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. VÉRIFIER QUE database/manager.py A LE FIX
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("ÉTAPE 1: Vérifier database/manager.py")
print("="*80)

manager_path = Path("database/manager.py")

if not manager_path.exists():
    print("❌ ERREUR: database/manager.py introuvable!")
    print("   Chemin attendu:", manager_path.absolute())
    sys.exit(1)

with open(manager_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Vérifier import uuid
if "import uuid" in content:
    print("✅ Import uuid présent")
else:
    print("❌ MANQUANT: import uuid")
    print("\n🔧 ACTION REQUISE:")
    print("   1. Remplacer database/manager.py par database_manager_FIXED.py")
    print("   2. Redémarrer Streamlit")
    sys.exit(1)

# Vérifier génération hash avec UUID
if "str(uuid.uuid4())" in content and "strftime('%Y%m%d%H%M%S%f')" in content:
    print("✅ Génération hash corrigée (UUID + microsecondes)")
else:
    print("⚠️ Hash peut ne pas être unique")
    print("\n🔧 ACTION RECOMMANDÉE:")
    print("   Remplacer database/manager.py par database_manager_FIXED.py")

# Vérifier gestion IntegrityError
if "IntegrityError" in content:
    print("✅ Gestion IntegrityError présente")
else:
    print("⚠️ Gestion IntegrityError absente (non critique)")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TESTER CONNEXION DB
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("ÉTAPE 2: Tester connexion base de données")
print("="*80)

try:
    sys.path.insert(0, str(Path.cwd()))
    from database.manager import DatabaseManager
    
    DB_URL = "postgresql://app_beton:Passer123@localhost:5432/concrete_ai_platform"
    db = DatabaseManager(DB_URL)
    
    if db.is_connected:
        print("✅ Connexion DB établie")
    else:
        print("❌ Connexion DB échouée")
        sys.exit(1)
    
    db.close()
    
except Exception as e:
    print(f"❌ ERREUR: {e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TEST SAUVEGARDE RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("ÉTAPE 3: Test sauvegarde rapide")
print("="*80)

try:
    db = DatabaseManager(DB_URL)
    
    test_formulation = {
        'Ciment': 350.0,
        'Eau': 175.0,
        'Laitier': 0.0,
        'CendresVolantes': 0.0,
        'Superplastifiant': 3.5,
        'GravilonsGros': 1100.0,
        'SableFin': 750.0,
        'Age': 28
    }
    
    test_predictions = {
        'Resistance': 35.0,
        'Diffusion_Cl': 8.0,
        'Carbonatation': 14.0,
        'Ratio_E_L': 0.5,
        'Liant_Total': 350.0
    }
    
    print("\n📝 Test 1/2: Première sauvegarde...")
    success1 = db.save_prediction(
        formulation=test_formulation,
        predictions=test_predictions,
        formulation_name="VERIFICATION_FINALE_1"
    )
    
    if success1:
        print("   ✅ Première sauvegarde réussie")
    else:
        print("   ❌ Première sauvegarde échouée")
    
    print("\n📝 Test 2/2: Sauvegarde immédiate (test hash unique)...")
    success2 = db.save_prediction(
        formulation=test_formulation,
        predictions=test_predictions,
        formulation_name="VERIFICATION_FINALE_2"
    )
    
    if success2:
        print("   ✅ Deuxième sauvegarde réussie")
    else:
        print("   ❌ Deuxième sauvegarde échouée (hash dupliqué ?)")
    
    db.close()
    
    # Vérifier dans la base
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM predictions
        WHERE nom_formulation LIKE 'VERIFICATION_FINALE_%'
    """)
    
    count = cursor.fetchone()['count']
    
    print(f"\n📊 Résultat: {count}/2 formulations trouvées dans la base")
    
    if count == 2:
        print("✅ PARFAIT: Les 2 sauvegardes sont dans la base")
    elif count == 1:
        print("⚠️ PROBLÈME: Une seule sauvegarde présente (hash dupliqué ?)")
    else:
        print("❌ PROBLÈME: Aucune sauvegarde trouvée")
    
    # Nettoyage
    cursor.execute("DELETE FROM predictions WHERE nom_formulation LIKE 'VERIFICATION_FINALE_%'")
    conn.commit()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
# RÉSULTAT FINAL
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("RÉSULTAT FINAL")
print("="*80)

print("""
✅ Si toutes les vérifications sont passées:
   → Votre bouton "Sauvegarder" fonctionne !
   
🧪 Test UI final:
   1. Démarrer Streamlit: streamlit run app.py
   2. Aller sur Formulateur
   3. Choisir "Norme C25/30"
   4. Lancer Prédiction
   5. Cliquer "💾 Sauvegarder"
   
   ✅ Attendu: "Formulation sauvegardée !" + Ballons 🎈

❌ Si une vérification a échoué:
   → Suivez les actions recommandées ci-dessus
   → Re-exécutez ce script
""")

print("\n" + "="*80)
print("Vérification terminée")
print("="*80)