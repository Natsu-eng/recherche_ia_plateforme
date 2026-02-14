"""
═══════════════════════════════════════════════════════════════════════════════
SCRIPT DE TEST: Base de données PostgreSQL
Fichier: test_database.py
═══════════════════════════════════════════════════════════════════════════════
Tests complets pour valider sauvegarde, récupération, et stats
"""

import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import hashlib
import uuid

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_URL = "postgresql://app_beton:Passer123@localhost:5432/concrete_ai_platform"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def test_1_connection():
    """Test 1: Connexion à la base de données."""
    print("\n" + "="*80)
    print("TEST 1: CONNEXION DATABASE")
    print("="*80)
    
    try:
        db = DatabaseManager(DB_URL)
        
        if db.is_connected:
            print("✅ SUCCÈS: Connexion établie")
            db.close()
            return True
        else:
            print("❌ ÉCHEC: Impossible de se connecter")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False


def test_2_schema_verification():
    """Test 2: Vérification du schéma de la table predictions."""
    print("\n" + "="*80)
    print("TEST 2: VÉRIFICATION SCHÉMA")
    print("="*80)
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Lister colonnes
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print(f"\nTable 'predictions' contient {len(columns)} colonnes:")
        print("-" * 80)
        
        required_cols = [
            'nom_formulation', 'resistance_predite', 'hash_formulation',
            'ciment', 'eau', 'sable', 'gravier', 'laitier', 'cendres',
            'adjuvants', 'diffusion_cl_predite', 'carbonatation_predite'
        ]
        
        found_cols = [col['column_name'] for col in columns]
        
        for col_name in required_cols:
            if col_name in found_cols:
                print(f"✅ {col_name}")
            else:
                print(f"❌ MANQUANT: {col_name}")
        
        cursor.close()
        conn.close()
        
        missing = set(required_cols) - set(found_cols)
        if missing:
            print(f"\n❌ Colonnes manquantes: {missing}")
            return False
        else:
            print("\n✅ SUCCÈS: Toutes les colonnes requises présentes")
            return True
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False


def test_3_insert_simple():
    """Test 3: Insertion simple d'une prédiction."""
    print("\n" + "="*80)
    print("TEST 3: INSERTION SIMPLE")
    print("="*80)
    
    try:
        db = DatabaseManager(DB_URL)
        
        # Composition test
        formulation = {
            'Ciment': 350.0,
            'Eau': 175.0,
            'Laitier': 0.0,
            'CendresVolantes': 0.0,
            'Superplastifiant': 3.5,
            'GravilonsGros': 1100.0,
            'SableFin': 750.0,
            'Age': 28
        }
        
        predictions = {
            'Resistance': 35.4,
            'Diffusion_Cl': 8.2,
            'Carbonatation': 14.5,
            'Ratio_E_L': 0.5,
            'Liant_Total': 350.0
        }
        
        print("\n📝 Tentative sauvegarde:")
        print(f"  - Nom: TEST_INSERTION_SIMPLE")
        print(f"  - Résistance: {predictions['Resistance']} MPa")
        print(f"  - Ciment: {formulation['Ciment']} kg/m³")
        
        success = db.save_prediction(
            formulation=formulation,
            predictions=predictions,
            formulation_name="TEST_INSERTION_SIMPLE"
        )
        
        if success:
            print("\n✅ SUCCÈS: Insertion réussie")
            
            # Vérifier dans la base
            conn = psycopg2.connect(DB_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM predictions 
                WHERE nom_formulation = 'TEST_INSERTION_SIMPLE'
                ORDER BY horodatage DESC LIMIT 1
            """)
            
            row = cursor.fetchone()
            
            if row:
                print(f"✅ Donnée retrouvée: ID={row['id']}, R={row['resistance_predite']} MPa")
            else:
                print("⚠️ Donnée non retrouvée dans la table")
            
            cursor.close()
            conn.close()
            db.close()
            return True
        else:
            print("❌ ÉCHEC: save_prediction() a retourné False")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_hash_uniqueness():
    """Test 4: Vérifier que les hash sont uniques (5 sauvegardes rapides)."""
    print("\n" + "="*80)
    print("TEST 4: UNICITÉ DES HASH")
    print("="*80)
    
    try:
        db = DatabaseManager(DB_URL)
        
        formulation = {
            'Ciment': 300.0,
            'Eau': 180.0,
            'Laitier': 0.0,
            'CendresVolantes': 0.0,
            'Superplastifiant': 2.0,
            'GravilonsGros': 1050.0,
            'SableFin': 800.0,
            'Age': 28
        }
        
        predictions = {
            'Resistance': 30.0,
            'Diffusion_Cl': 9.0,
            'Carbonatation': 15.0,
            'Ratio_E_L': 0.6,
            'Liant_Total': 300.0
        }
        
        print("\n📝 Sauvegarde de la même formulation 5 fois rapidement...")
        
        success_count = 0
        for i in range(5):
            success = db.save_prediction(
                formulation=formulation,
                predictions=predictions,
                formulation_name=f"TEST_HASH_{i+1}"
            )
            
            if success:
                success_count += 1
                print(f"  ✅ Sauvegarde {i+1}/5 réussie")
            else:
                print(f"  ❌ Sauvegarde {i+1}/5 échouée")
        
        print(f"\n📊 Résultat: {success_count}/5 sauvegardes réussies")
        
        # Vérifier hash uniques
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT hash_formulation, COUNT(*) as count
            FROM predictions
            WHERE nom_formulation LIKE 'TEST_HASH_%'
            GROUP BY hash_formulation
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"\n❌ ÉCHEC: {len(duplicates)} hash dupliqués détectés")
            for dup in duplicates:
                print(f"  - Hash: {dup[0][:16]}... (x{dup[1]})")
            cursor.close()
            conn.close()
            db.close()
            return False
        else:
            print("\n✅ SUCCÈS: Tous les hash sont uniques")
            cursor.close()
            conn.close()
            db.close()
            return success_count == 5
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_get_recent_predictions():
    """Test 5: Récupération des prédictions récentes."""
    print("\n" + "="*80)
    print("TEST 5: RÉCUPÉRATION PRÉDICTIONS RÉCENTES")
    print("="*80)
    
    try:
        db = DatabaseManager(DB_URL)
        
        print("\n📝 Récupération des 5 dernières prédictions...")
        
        predictions = db.get_recent_predictions(limit=5)
        
        if predictions:
            print(f"\n✅ {len(predictions)} prédictions récupérées:")
            print("-" * 80)
            
            for i, pred in enumerate(predictions, 1):
                print(f"\n{i}. {pred['formulation_name']}")
                print(f"   - Résistance: {pred['resistance_predicted']:.2f} MPa")
                print(f"   - Ciment: {pred['ciment']:.1f} kg/m³")
                print(f"   - Date: {pred['created_at']}")
            
            db.close()
            return True
        else:
            print("⚠️ Aucune prédiction trouvée")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_live_stats():
    """Test 6: Statistiques en temps réel."""
    print("\n" + "="*80)
    print("TEST 6: STATISTIQUES LIVE")
    print("="*80)
    
    try:
        db = DatabaseManager(DB_URL)
        
        print("\n📊 Récupération des stats...")
        
        stats = db.get_live_stats()
        
        print("\nRésultats:")
        print(f"  - Total prédictions: {stats['total_predictions']}")
        print(f"  - Formulations uniques: {stats['formulations_analyzed']}")
        print(f"  - Résistance moyenne: {stats['avg_resistance']:.2f} MPa")
        print(f"  - DB connectée: {stats['db_connected']}")
        
        db.close()
        
        if stats['db_connected']:
            print("\n✅ SUCCÈS: Stats récupérées")
            return True
        else:
            print("\n❌ ÉCHEC: DB non connectée")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_cleanup():
    """Test 7: Nettoyage des données de test."""
    print("\n" + "="*80)
    print("TEST 7: NETTOYAGE DONNÉES TEST")
    print("="*80)
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Supprimer données test
        cursor.execute("""
            DELETE FROM predictions
            WHERE nom_formulation LIKE 'TEST_%'
        """)
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n🗑️ {deleted_count} enregistrements de test supprimés")
        print("✅ SUCCÈS: Nettoyage terminé")
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# EXÉCUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_tests():
    """Exécute tous les tests."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SUITE DE TESTS - BASE DE DONNÉES POSTGRESQL                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    tests = [
        ("Connexion DB", test_1_connection),
        ("Vérification schéma", test_2_schema_verification),
        ("Insertion simple", test_3_insert_simple),
        ("Unicité hash", test_4_hash_uniqueness),
        ("Récupération récentes", test_5_get_recent_predictions),
        ("Statistiques live", test_6_live_stats),
        ("Nettoyage", test_7_cleanup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERREUR CRITIQUE dans {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ DES TESTS")
    print("="*80)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*80)
    print(f"SCORE FINAL: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ La base de données fonctionne correctement")
    else:
        print(f"\n⚠️ {total - passed} test(s) échoué(s)")
        print("Consultez les détails ci-dessus pour diagnostiquer")


if __name__ == "__main__":
    run_all_tests()