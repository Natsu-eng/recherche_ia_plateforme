#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TESTS AUTOMATIQUES - CORRECTIFS SAUVEGARDE
Version: 1.0.1 - CHEMINS CORRIGÉS
Date: 2024-12-25
═══════════════════════════════════════════════════════════════════════════════

Ce script teste automatiquement :
1. Connexion à la base de données
2. Sauvegarde d'une formulation test
3. Récupération des données
4. Logs et diagnostics

CHEMINS CORRECTS :
- DatabaseManager : database/manager.py
- Pages Streamlit : pages/ (hors de app/)
"""

import sys
import os
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Codes couleur
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title):
    """Affiche un header formaté."""
    print("\n" + "=" * 80)
    print(f"{Colors.BLUE}{Colors.BOLD}{title}{Colors.END}")
    print("=" * 80 + "\n")

def print_success(message):
    """Affiche un message de succès."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Affiche un message d'erreur."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    """Affiche un avertissement."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    """Affiche une info."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 : VÉRIFICATION ENVIRONNEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def test_environment():
    """Vérifie que l'environnement est correct."""
    print_header("TEST 1 : Environnement")
    
    all_ok = True
    
    # Vérifier fichier .env
    if os.path.exists('.env'):
        print_success("Fichier .env trouvé")
        
        with open('.env', 'r') as f:
            content = f.read()
            if 'DATABASE_URL' in content:
                print_success("DATABASE_URL présent")
            else:
                print_error("DATABASE_URL manquant dans .env")
                all_ok = False
    else:
        print_error("Fichier .env non trouvé")
        all_ok = False
    
    # Vérifier modules Python
    try:
        import psycopg2
        print_success("Module psycopg2 installé")
    except ImportError:
        print_error("Module psycopg2 manquant (pip install psycopg2-binary)")
        all_ok = False
    
    try:
        import streamlit
        print_success("Module streamlit installé")
    except ImportError:
        print_error("Module streamlit manquant (pip install streamlit)")
        all_ok = False
    
    # Vérifier structure projet (CHEMINS CORRIGÉS)
    required_paths = {
        'database': 'Répertoire database/',
        'database/manager.py': 'DatabaseManager',
        'pages': 'Répertoire pages/',
        'pages/1_Formulateur.py': 'Page Formulateur'
    }
    
    for path, description in required_paths.items():
        if os.path.exists(path):
            print_success(f"{description} trouvé")
        else:
            print_warning(f"{description} non trouvé ({path})")
            # Ne pas bloquer pour les pages, juste avertir
            if 'database' in path:
                all_ok = False
    
    return all_ok

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 : CONNEXION BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def test_database_connection():
    """Teste la connexion à la base de données."""
    print_header("TEST 2 : Connexion Base de Données")
    
    try:
        # Charger .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print_success("Module dotenv chargé")
        except ImportError:
            print_warning("Module dotenv non trouvé (pip install python-dotenv)")
            print_info("Tentative lecture manuelle .env...")
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            os.environ['DATABASE_URL'] = line.split('=', 1)[1].strip()
        
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print_error("DATABASE_URL non défini")
            return False
        
        print_info("DATABASE_URL trouvé")
        
        # Masquer password pour affichage
        masked_url = db_url
        if '@' in db_url:
            parts = db_url.split('@')
            auth = parts[0].split('://')[-1]
            if ':' in auth:
                user = auth.split(':')[0]
                masked_url = db_url.replace(auth, f"{user}:****")
        
        print_info(f"URL: {masked_url}")
        
        # Importer DatabaseManager (CHEMIN CORRIGÉ)
        sys.path.insert(0, '.')  # Ajouter racine projet
        
        try:
            from database.manager import DatabaseManager
            print_success("DatabaseManager importé depuis database/manager.py")
        except ImportError as e:
            print_error(f"Impossible d'importer DatabaseManager: {e}")
            print_info("Chemins testés :")
            print_info("  - database/manager.py")
            print_info("  - database/__init__.py")
            return False
        
        # Créer instance
        print_info("Création instance DatabaseManager...")
        db = DatabaseManager(db_url)
        
        if db.is_connected:
            print_success("Connexion établie !")
            
            # Afficher diagnostics
            try:
                diag = db.get_diagnostics()
                print_info(f"PostgreSQL: {diag.get('postgresql_version', 'N/A')[:50]}...")
                print_info(f"Database: {diag.get('database', 'N/A')}")
                print_info(f"User: {diag.get('user', 'N/A')}")
                print_info(f"Prédictions: {diag.get('predictions_count', 0)}")
            except AttributeError:
                print_warning("Méthode get_diagnostics() non disponible")
                print_info("(Version ancienne du DatabaseManager)")
            
            db.close()
            return True
        else:
            print_error("Connexion échouée")
            if hasattr(db, 'connection_error') and db.connection_error:
                print_error(f"Erreur: {db.connection_error}")
            return False
    
    except ImportError as e:
        print_error(f"Erreur import: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False
    
    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 : SAUVEGARDE FORMULATION TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_save_prediction():
    """Teste la sauvegarde d'une formulation."""
    print_header("TEST 3 : Sauvegarde Formulation Test")
    
    try:
        # Charger .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            os.environ['DATABASE_URL'] = line.split('=', 1)[1].strip()
        
        db_url = os.getenv('DATABASE_URL')
        
        # Créer DatabaseManager
        sys.path.insert(0, '.')
        from database.manager import DatabaseManager
        
        db = DatabaseManager(db_url)
        
        if not db.is_connected:
            print_error("Base de données non connectée")
            return False
        
        # Formulation test
        test_formulation = {
            'Ciment': 350.0,
            'Eau': 175.0,
            'SableFin': 750.0,
            'GravilonsGros': 1000.0,
            'Laitier': 0.0,
            'CendresVolantes': 0.0,
            'Superplastifiant': 5.0,
            'Age': 28
        }
        
        test_predictions = {
            'Resistance': 45.2,
            'Diffusion_Cl': 6.5,
            'Carbonatation': 12.3,
            'Ratio_E_L': 0.5,
            'Liant_Total': 350.0,
            'Pct_Substitution': 0.0
        }
        
        test_name = f"TEST_AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print_info(f"Sauvegarde de '{test_name}'...")
        print_info(f"Composition: C={test_formulation['Ciment']}, E={test_formulation['Eau']}")
        print_info(f"Prédictions: R={test_predictions['Resistance']:.1f} MPa")
        
        # Tenter sauvegarde
        success = db.save_prediction(
            formulation=test_formulation,
            predictions=test_predictions,
            formulation_name=test_name,
            user_id='test_auto'
        )
        
        if success:
            print_success("Sauvegarde réussie !")
            
            # Vérifier en récupérant
            print_info("Vérification par récupération...")
            recent = db.get_recent_predictions(limit=1)
            
            if recent and len(recent) > 0:
                last = recent[0]
                if last['formulation_name'] == test_name:
                    print_success("Vérification : formulation retrouvée en base")
                    print_info(f"  Nom: {last['formulation_name']}")
                    print_info(f"  Résistance: {last['resistance_predicted']:.1f} MPa")
                else:
                    print_warning(f"Dernière formulation : {last['formulation_name']}")
                    print_warning("(Peut-être une autre sauvegarde entre-temps)")
            else:
                print_warning("Aucune prédiction récupérée")
            
            db.close()
            return True
        else:
            print_error("Sauvegarde échouée")
            print_error("Vérifiez les logs pour plus de détails")
            db.close()
            return False
    
    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 : RÉCUPÉRATION DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def test_retrieve_data():
    """Teste la récupération des données."""
    print_header("TEST 4 : Récupération Données")
    
    try:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            os.environ['DATABASE_URL'] = line.split('=', 1)[1].strip()
        
        db_url = os.getenv('DATABASE_URL')
        
        sys.path.insert(0, '.')
        from database.manager import DatabaseManager
        
        db = DatabaseManager(db_url)
        
        if not db.is_connected:
            print_error("Base de données non connectée")
            return False
        
        # Récupérer dernières prédictions
        print_info("Récupération des 5 dernières prédictions...")
        recent = db.get_recent_predictions(limit=5)
        
        if recent:
            print_success(f"{len(recent)} prédiction(s) récupérée(s)")
            
            for i, pred in enumerate(recent, 1):
                print(f"\n{i}. {pred['formulation_name']}")
                print(f"   Résistance: {pred['resistance_predicted']:.1f} MPa")
                print(f"   Diffusion Cl: {pred['diffusion_cl_predicted']:.2f}")
                print(f"   Carbonatation: {pred['carbonatation_predicted']:.1f} mm")
                print(f"   Date: {pred['created_at']}")
        else:
            print_warning("Aucune prédiction trouvée")
            print_info("(Ceci est normal si la base vient d'être créée)")
        
        # Récupérer statistiques
        print_info("\nRécupération des statistiques...")
        stats = db.get_live_stats()
        
        if stats:
            print_success("Statistiques récupérées")
            print_info(f"Total prédictions: {stats['total_predictions']}")
            print_info(f"Formulations uniques: {stats['formulations_analyzed']}")
            print_info(f"Résistance moyenne: {stats['avg_resistance']:.1f} MPa")
            print_info(f"Diffusion moyenne: {stats['avg_diffusion_cl']:.2f}")
            print_info(f"DB connectée: {stats['db_connected']}")
        else:
            print_warning("Impossible de récupérer les statistiques")
        
        db.close()
        return True
    
    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5 : VÉRIFICATION STRUCTURE PROJET
# ═══════════════════════════════════════════════════════════════════════════════

def test_project_structure():
    """Vérifie la structure complète du projet."""
    print_header("TEST 5 : Structure Projet")
    
    all_ok = True
    
    # Structure attendue
    structure = {
        'database/': 'Module database',
        'database/manager.py': 'DatabaseManager',
        'pages/': 'Pages Streamlit',
        'pages/1_Formulateur.py': 'Page Formulateur',
        'config/': 'Configuration',
        'app/': 'Application'
    }
    
    for path, description in structure.items():
        if os.path.exists(path):
            if os.path.isdir(path):
                files = os.listdir(path)
                print_success(f"{description} → {len(files)} fichier(s)")
            else:
                size = os.path.getsize(path)
                print_success(f"{description} → {size} bytes")
        else:
            print_warning(f"{description} non trouvé ({path})")
    
    return all_ok

# ═══════════════════════════════════════════════════════════════════════════════
# EXÉCUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 80)
    print(f"{Colors.BOLD}TESTS AUTOMATIQUES - CORRECTIFS SAUVEGARDE{Colors.END}")
    print(f"{Colors.BOLD}Version 1.0.1 - Chemins Corrigés{Colors.END}")
    print("=" * 80)
    
    results = {
        'Environnement': False,
        'Connexion DB': False,
        'Sauvegarde': False,
        'Récupération': False,
        'Structure': False
    }
    
    # Test 1
    results['Environnement'] = test_environment()
    
    # Test 2
    if results['Environnement']:
        results['Connexion DB'] = test_database_connection()
    else:
        print_warning("Test 2 ignoré (environnement invalide)")
    
    # Test 3
    if results['Connexion DB']:
        results['Sauvegarde'] = test_save_prediction()
    else:
        print_warning("Test 3 ignoré (DB non connectée)")
    
    # Test 4
    if results['Connexion DB']:
        results['Récupération'] = test_retrieve_data()
    else:
        print_warning("Test 4 ignoré (DB non connectée)")
    
    # Test 5
    results['Structure'] = test_project_structure()
    
    # Récapitulatif
    print_header("RÉCAPITULATIF")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print(f"\n{Colors.BOLD}Résultat : {passed}/{total} tests réussis{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓✓✓ TOUS LES TESTS RÉUSSIS ✓✓✓{Colors.END}\n")
        print_info("Votre environnement est correctement configuré")
        print_info("Vous pouvez maintenant appliquer les correctifs")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗✗✗ CERTAINS TESTS ONT ÉCHOUÉ ✗✗✗{Colors.END}\n")
        print_info("Consultez les erreurs ci-dessus pour résoudre les problèmes")
        
        if not results['Environnement']:
            print_info("→ Vérifiez votre fichier .env et les modules Python")
        if not results['Connexion DB']:
            print_info("→ Vérifiez que PostgreSQL est démarré et accessible")
        
        return 1

if __name__ == '__main__':
    sys.exit(main())