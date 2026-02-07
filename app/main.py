"""
═══════════════════════════════════════════════════════════════════════════════
FICHIER: app/main.py - PAGE D'ACCUEIL PRODUCTION
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - PostgreSQL Ready + Optimized Queries
═══════════════════════════════════════════════════════════════════════════════

CHANGEMENTS CRITIQUES v1.0 :
1. Support PostgreSQL + SQLite (basculement automatique)
2. Requêtes optimisées (CTE, 1 seule query pour stats)
3. Recherche fuzzy (Levenshtein distance)
4. Gestion d'erreurs granulaire
5. Cache intelligent stratifié
6. Monitoring système temps réel
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime, timedelta
import sqlite3
import json
from typing import Dict, List, Optional, Tuple
import logging

# Ajout du path parent
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import APP_SETTINGS, DATABASE_SETTINGS
from app.styles.theme import apply_custom_theme
from app.components.navbar import render_top_nav
from app.components.cards import render_kpi_card

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION PAGE
# =============================================================================

st.set_page_config(
    page_title=APP_SETTINGS["app_name"],
    page_icon=APP_SETTINGS["app_icon"],
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://imt-nord-europe.fr/support',
        'About': f"# {APP_SETTINGS['app_name']}\nVersion {APP_SETTINGS['version']}\nIMT Nord Europe"
    }
)

apply_custom_theme()


# =============================================================================
# DÉTECTION TYPE DATABASE
# =============================================================================

# =============================================================================
# DÉTECTION TYPE DATABASE - VERSION CORRIGÉE
# =============================================================================

def detect_database_type() -> Tuple[str, any]:
    """
    Détecte et connecte à la base de données (PostgreSQL ou SQLite).
    """
    import os
    from dotenv import load_dotenv # type: ignore
    
    # CHARGEZ .env AVANT TOUTE CHOSE
    load_dotenv(override=True)
    
    # 1. Tentative PostgreSQL
    database_url = os.getenv("DATABASE_URL")
    logger.info(f"DEBUG - DATABASE_URL trouvé : {database_url is not None}")
    
    if database_url:
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            logger.info("✅ Connexion PostgreSQL établie")
            return "postgresql", conn
        except ImportError:
            logger.warning("⚠️ psycopg2 non installé")
        except Exception as e:
            logger.error(f"❌ Erreur PostgreSQL : {e}")
            # NE PAS continuer à SQLite si PostgreSQL échoue
            return "none", None
    
    # 2. Tentative SQLite (seulement si chemin valide)
    db_path = DATABASE_SETTINGS.get("database_path")
    if db_path and Path(db_path).exists():
        try:
            conn = sqlite3.connect(str(db_path))
            logger.info(f"✅ Connexion SQLite établie : {db_path}")
            return "sqlite", conn
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur SQLite : {e}")
    
    # 3. Aucune DB disponible
    logger.warning("⚠️ Aucune base de données disponible. Mode démo activé.")
    return "none", None


# Initialisation connexion DB
DB_TYPE, DB_CONN = detect_database_type()


# =============================================================================
# REQUÊTES DATABASE OPTIMISÉES
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_live_stats_optimized() -> Dict:
    """
    Récupère statistiques en 1 SEULE requête optimisée.
    
    Optimisations v4.0 :
    - CTE (Common Table Expression) pour SQLite 3.8.3+
    - Subquery optimisée pour PostgreSQL
    - Gestion erreurs granulaire
    - Cache stratifié (5 min)
    
    Returns:
        Dict avec stats ou valeurs par défaut si erreur
    """
    default_stats = {
        'total_predictions': 0,
        'formulations_analyzed': 0,
        'model_accuracy': 95.5,
        'active_users': 1,
        'avg_resistance': 35.0,
        'last_update': datetime.now(),
        'db_status': 'unavailable'
    }
    
    if DB_TYPE == "none":
        return default_stats
    
    try:
        cursor = DB_CONN.cursor()
        
        # Timestamp 24h
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        # ─────────────────────────────────────────────────────
        # REQUÊTE OPTIMISÉE (1 seule query via CTE)
        # ─────────────────────────────────────────────────────
        if DB_TYPE == "sqlite":
            query = """
            WITH stats_data AS (
                SELECT 
                    COUNT(*) as total_preds,
                    COUNT(DISTINCT formulation_hash) as unique_forms,
                    COUNT(DISTINCT CASE WHEN timestamp > ? THEN user_id END) as active_users_24h,
                    AVG(predicted_resistance) as avg_resistance
                FROM predictions
            )
            SELECT 
                total_preds,
                unique_forms,
                active_users_24h,
                avg_resistance
            FROM stats_data;
            """
            cursor.execute(query, (yesterday,))
        
        elif DB_TYPE == "postgresql":
            query = """
                SELECT 
                    COUNT(*) as total_preds,
                    COUNT(DISTINCT hash_formulation) as unique_forms,
                    COUNT(DISTINCT CASE WHEN horodatage > %s THEN id_utilisateur END) as active_users_24h,
                    AVG(resistance_predite) as avg_resistance
                FROM predictions;
                """
            cursor.execute(query, (yesterday,))
        
        # Extraction résultats
        row = cursor.fetchone()
        
        if row:
            stats = {
                'total_predictions': int(row[0] or 0),
                'formulations_analyzed': int(row[1] or 0),
                'active_users': int(row[2] or 1),
                'avg_resistance': float(row[3] or 35.0),
                'model_accuracy': 95.5,  # Calcul séparé si nécessaire
                'last_update': datetime.now(),
                'db_status': 'connected'
            }
            
            logger.info(f"✅ Stats récupérées : {stats['total_predictions']} prédictions")
            return stats
        else:
            logger.warning("⚠️ Aucune donnée dans la table predictions")
            return default_stats
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur SQLite : {e}")
        return {**default_stats, 'db_status': 'sqlite_error'}
    except Exception as e:
        logger.error(f"❌ Erreur DB inattendue : {e}", exc_info=True)
        return {**default_stats, 'db_status': 'error'}


@st.cache_data(ttl=600, show_spinner=False)
def get_recent_predictions_optimized(limit: int = 5) -> List[Dict]:
    """
    Récupère dernières prédictions avec ORDER BY optimisé.
    """
    if DB_TYPE == "none":
        # Données démo
        return [
            {"name": "Béton C25/30 Standard", "resistance": 28.5, "time": "10:30", "ratio_el": 0.64},
            {"name": "Béton Haute Performance", "resistance": 52.3, "time": "11:15", "ratio_el": 0.38},
            {"name": "Béton Écologique", "resistance": 31.2, "time": "11:45", "ratio_el": 0.58}
        ]
    
    try:
        cursor = DB_CONN.cursor()
        
        param_placeholder = "?" if DB_TYPE == "sqlite" else "%s"
        
        query = f"""
        SELECT 
            nom_formulation, 
            resistance_predite, 
            horodatage,
            ratio_eau_liaison
        FROM predictions 
        ORDER BY horodatage DESC 
        LIMIT {param_placeholder}
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("ℹ️ Table predictions vide, utilisation données démo")
            return get_recent_predictions_optimized.__wrapped__(limit)
        
        predictions = []
        for row in rows:
            name, resistance, horodatage, ratio_eau_liaison = row 
            
            # Parse timestamp (gestion robuste)
            time_str = "N/A"
            try:
                # Si horodatage est déjà un datetime
                if isinstance(horodatage, datetime):
                    time_obj = horodatage
                # Si c'est un string
                elif isinstance(horodatage, str):
                    # Essayer plusieurs formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
                        try:
                            time_obj = datetime.strptime(horodatage, fmt)
                            break
                        except:
                            continue
                    else:
                        # Dernier essai avec fromisoformat
                        time_obj = datetime.fromisoformat(horodatage.replace('Z', '+00:00'))
                else:
                    # Type inconnu
                    time_obj = datetime.now()
                
                time_str = time_obj.strftime("%H:%M")
            except Exception as time_err:
                logger.warning(f"⚠️ Erreur parsing horodatage {horodatage}: {time_err}")
                time_str = "N/A"
            
            predictions.append({
                "name": name or "Formulation Personnalisée",
                "resistance": float(resistance or 0),
                "time": time_str,
                "ratio_el": float(ratio_eau_liaison or 0.5)  
            })
        
        return predictions
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération prédictions : {e}", exc_info=True)
        # Fallback
        return [
            {"name": "Béton Standard", "resistance": 30.0, "time": "N/A", "ratio_el": 0.60}
        ]


# =============================================================================
# RECHERCHE FUZZY (LEVENSHTEIN)
# =============================================================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcule la distance de Levenshtein (édition) entre 2 chaînes.
    
    Utilisée pour recherche "approximative" (fuzzy search).
    
    Example:
        >>> levenshtein_distance("optimiser", "optimis")
        2  # 2 caractères de différence
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def fuzzy_search_modules(query: str, modules: List[Dict], threshold: int = 3) -> List[Dict]:
    """
    Recherche fuzzy dans les modules.
    
    Args:
        query: Requête utilisateur
        modules: Liste modules
        threshold: Distance Levenshtein max acceptée (défaut: 3)
    
    Returns:
        Modules correspondants triés par pertinence
    """
    if not query:
        return modules
    
    query_lower = query.lower()
    results = []
    
    for module in modules:
        # Recherche exacte d'abord
        exact_match = (
            query_lower in module['title'].lower() or
            query_lower in module['description'].lower() or
            any(query_lower in kw.lower() for kw in module['keywords'])
        )
        
        if exact_match:
            results.append((module, 0))  # Score 0 = meilleur match
            continue
        
        # Recherche fuzzy
        min_distance = min(
            levenshtein_distance(query_lower, kw.lower()) 
            for kw in module['keywords']
        )
        
        if min_distance <= threshold:
            results.append((module, min_distance))
    
    # Tri par pertinence (score croissant)
    results.sort(key=lambda x: x[1])
    
    return [module for module, score in results]


# =============================================================================
# UTILS
# =============================================================================

def calculate_uptime() -> str:
    """Calcule uptime session."""
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = datetime.now()
    
    uptime = datetime.now() - st.session_state.session_start_time
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    else:
        return f"{minutes}m"


def get_system_status() -> Dict:
    """Récupère statut système (modèle, DB, etc.)."""
    status = {
        'model_loaded': False,
        'db_connected': False,
        'db_type': DB_TYPE
    }
    
    # Vérifier modèle
    try:
        from app.models.loader import assets_exist
        status['model_loaded'] = assets_exist()
    except:
        pass
    
    # Vérifier DB
    status['db_connected'] = (DB_TYPE != "none")
    
    return status


# =============================================================================
# INITIALISATION SESSION
# =============================================================================

def init_home_session():
    """Initialise session state."""
    if 'home_initialized' not in st.session_state:
        st.session_state.home_initialized = True
        st.session_state.session_start_time = datetime.now()
        st.session_state.page_views = 1
        logger.info("🚀 Session initialisée")
    else:
        st.session_state.page_views += 1


init_home_session()


# =============================================================================
# NAVIGATION
# =============================================================================

render_top_nav(active_page="home")


# =============================================================================
# HERO SECTION DYNAMIQUE
# =============================================================================

current_hour = datetime.now().hour
greeting = "Bonsoir"
if current_hour < 12:
    greeting = "Bonjour"
elif current_hour < 18:
    greeting = "Bon après-midi"

# Statut système
sys_status = get_system_status()
model_icon = "✅" if sys_status['model_loaded'] else "⚠️"
db_icon = "✅" if sys_status['db_connected'] else "⚠️"

st.markdown(f"""
<div style='background: linear-gradient(135deg, #1976D2 0%, #1565C0 50%, #0D47A1 100%); 
            padding: 4rem 2rem; border-radius: 20px; margin-bottom: 3rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);'>
    <h1 style='color: white; text-align: center; margin: 0; font-size: 3em;
               text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
        {greeting} ! 🏗️ Plateforme R&D Béton IA
    </h1>
    <p style='color: rgba(255,255,255,0.95); text-align: center; 
              font-size: 1.4em; margin-top: 1rem; font-weight: 300;'>
        Intelligence Artificielle pour la Formulation & l'Optimisation du Béton
    </p>
    <p style='color: rgba(255,255,255,0.85); text-align: center; 
              font-size: 1.1em; margin-top: 0.5rem;'>
        {APP_SETTINGS['institution']} - {APP_SETTINGS['department']}
    </p>
    <div style='text-align: center; margin-top: 2rem;'>
        <span style='background: rgba(255,255,255,0.2); color: white; 
                     padding: 0.5rem 1.5rem; border-radius: 25px; 
                     font-size: 0.9em; margin: 0 0.5rem;'>
            🕐 {datetime.now().strftime("%H:%M")}
        </span>
        <span style='background: rgba(255,255,255,0.2); color: white; 
                     padding: 0.5rem 1.5rem; border-radius: 25px; 
                     font-size: 0.9em; margin: 0 0.5rem;'>
            📅 {datetime.now().strftime("%d/%m/%Y")}
        </span>
        <span style='background: rgba(255,255,255,0.2); color: white; 
                     padding: 0.5rem 1.5rem; border-radius: 25px; 
                     font-size: 0.9em; margin: 0 0.5rem;'>
            🚀 v{APP_SETTINGS['version']}
        </span>
        <span style='background: rgba(255,255,255,0.2); color: white; 
                     padding: 0.5rem 1.5rem; border-radius: 25px; 
                     font-size: 0.9em; margin: 0 0.5rem;'>
            {model_icon} Modèle • {db_icon} DB ({sys_status['db_type'].upper()})
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# KPI CARDS - DONNÉES RÉELLES OPTIMISÉES
# =============================================================================

st.markdown("### 📊 Statistiques en Temps Réel")

with st.spinner("Chargement statistiques..."):
    stats = get_live_stats_optimized()

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_kpi_card(
        title="Prédictions Totales",
        value=stats['total_predictions'],
        color="blue",
        icon="🎯"
    )

with col2:
    render_kpi_card(
        title="Formulations Analysées",
        value=stats['formulations_analyzed'],
        color="green",
        icon="🧪"
    )

with col3:
    render_kpi_card(
        title="Résistance Moyenne",
        value=f"{stats['avg_resistance']:.1f}",
        unit=" MPa",
        color="purple",
        icon="💪"
    )

with col4:
    render_kpi_card(
        title="Utilisateurs Actifs (24h)",
        value=stats['active_users'],
        color="orange",
        icon="👥"
    )

# Indicateur statut DB
if stats['db_status'] != 'connected':
    st.warning(
        f"⚠️ Base de données non connectée (statut: {stats['db_status']}). "
        "Affichage de données de démonstration."
    )

st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# DERNIÈRES PRÉDICTIONS
# =============================================================================

st.markdown("### 📈 Dernières Prédictions")

recent_predictions = get_recent_predictions_optimized(limit=5)

if recent_predictions:
    cols = st.columns(len(recent_predictions))
    
    for idx, pred in enumerate(recent_predictions):
        with cols[idx]:
            resistance = pred["resistance"]
            ratio_el = pred.get("ratio_el", 0.5)
            
            # Classification
            if resistance >= 50:
                color = "#388E3C"
                perf = "HP"
            elif resistance >= 35:
                color = "#1976D2"
                perf = "Standard"
            else:
                color = "#FF6F00"
                perf = "Faible"
            
            st.markdown(f"""
            <div style='background: white; border: 2px solid {color}; 
                        border-radius: 10px; padding: 1rem; text-align: center;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.05); height: 200px;
                        display: flex; flex-direction: column; justify-content: space-between;'>
                <div>
                    <h4 style='margin: 0 0 0.5rem 0; color: #333; font-size: 0.9rem;'>
                        {pred["name"][:30]}...
                    </h4>
                    <div style='font-size: 1.8rem; font-weight: 700; color: {color};'>
                        {resistance:.1f} MPa
                    </div>
                    <div style='color: #666; font-size: 0.8rem; margin-top: 0.3rem;'>
                        E/L: {ratio_el:.2f}
                    </div>
                    <div style='color: #999; font-size: 0.75rem; margin-top: 0.3rem;'>
                        🕐 {pred["time"]}
                    </div>
                </div>
                <div style='background: {color}; color: white; 
                            padding: 0.3rem; border-radius: 8px; font-size: 0.7rem;'>
                    {perf}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)


# =============================================================================
# RECHERCHE FUZZY
# =============================================================================

st.markdown("### 🔍 Recherche Intelligente")

search_query = st.text_input(
    "",
    placeholder="Ex: optimiser, comparer, analyser, sensibilité...",
    help="Recherche intelligente avec tolérance aux fautes de frappe",
    label_visibility="collapsed"
)


# =============================================================================
# MODULES
# =============================================================================

st.markdown("### 🚀 Modules Disponibles")

modules = [
    {
        "title": "Formulateur",
        "description": "Prédisez instantanément les performances de votre béton",
        "icon": "🧪",
        "color": "#1976D2",
        "page": "pages/2_Formulateur.py",
        "features": ["Résistance", "Durabilité", "Validation EN 206"],
        "keywords": ["formuler", "prédire", "calculer", "composition", "béton"]
    },
    {
        "title": "Comparateur",
        "description": "Comparez jusqu'à 10 formulations simultanément",
        "icon": "📊",
        "color": "#388E3C",
        "page": "pages/3_Comparateur.py",
        "features": ["Tableaux comparatifs", "Graphiques radar", "Export CSV/Excel"],
        "keywords": ["comparer", "tableau", "export", "visualiser", "comparaison"]
    },
    {
        "title": "Laboratoire",
        "description": "Sandbox d'analyse paramétrique avancée",
        "icon": "🔬",
        "color": "#FF6F00",
        "page": "pages/4_Laboratoire.py",
        "features": ["Analyse de sensibilité", "Courbes d'impact", "Simulations"],
        "keywords": ["analyser", "sensibilité", "paramètres", "courbes", "laboratoire"]
    },
    {
        "title": "Optimiseur",
        "description": "Trouvez la formulation optimale pour vos critères",
        "icon": "🎯",
        "color": "#7B1FA2",
        "page": "pages/5_Optimiseur.py",
        "features": ["Minimiser coût", "Minimiser CO₂", "Algorithme génétique"],
        "keywords": ["optimiser", "minimiser", "coût", "co2", "génétique", "optimisation"]
    },
    {
        "title": "Analyses",
        "description": "Import & analyse avancée de données",
        "icon": "📈",
        "color": "#0277BD",
        "page": "pages/6_Analyse_Donnees.py",
        "features": ["Upload CSV/Excel", "Statistiques", "Corrélations"],
        "keywords": ["importer", "csv", "excel", "statistiques", "corrélation", "données"]
    },
    {
        "title": "Configuration",
        "description": "Paramètres & diagnostic système",
        "icon": "⚙️",
        "color": "#455A64",
        "page": "pages/7_Configuration.py",
        "features": ["Statut système", "Configuration", "Logs & monitoring"],
        "keywords": ["config", "paramètres", "diagnostic", "système", "configuration"]
    }
]

# Recherche fuzzy
if search_query:
    filtered_modules = fuzzy_search_modules(search_query, modules, threshold=3)
    if not filtered_modules:
        st.warning(f"❌ Aucun module trouvé pour '{search_query}'. Essayez : optimiser, comparer, analyser...")
else:
    filtered_modules = modules

# Affichage modules
for i in range(0, len(filtered_modules), 3):
    cols = st.columns(3)
    for j in range(3):
        if i + j < len(filtered_modules):
            module = filtered_modules[i + j]
            with cols[j]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, {module['color']}20 0%, white 100%); 
                            padding: 1.5rem; border-radius: 15px; 
                            border-left: 6px solid {module['color']}; height: 280px;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            transition: transform 0.3s ease;'
                onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 12px rgba(0,0,0,0.15)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';">
                    <h3 style='color: {module['color']}; margin-top: 0; display: flex; align-items: center; gap: 10px;'>
                        {module['icon']} {module['title']}
                    </h3>
                    <p style='color: #555; line-height: 1.5; font-size: 0.95rem; margin: 1rem 0;'>
                        {module['description']}
                    </p>
                    <div style='color: #666; font-size: 0.85rem;'>
                        <strong>Fonctionnalités :</strong>
                        <ul style='margin: 0.5rem 0 0 0; padding-left: 1.2rem;'>
                """, unsafe_allow_html=True)
                
                for feature in module['features']:
                    st.markdown(f"<li>{feature}</li>", unsafe_allow_html=True)
                
                st.markdown("""
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(
                    f"Accéder →", 
                    key=f"btn_{module['title'].replace(' ', '_')}", 
                    use_container_width=True
                ):
                    st.switch_page(module['page'])


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")

current_year = datetime.now().year
uptime = calculate_uptime()

st.markdown(f"""
<div style='text-align: center; padding: 2rem 0;'>
    <p style='color: #1976D2; font-size: 1.2em; font-weight: 600; margin-bottom: 0.5rem;'>
        🏗️ {APP_SETTINGS['app_name']} - Version {APP_SETTINGS['version']}
    </p>
    <p style='color: #666; font-size: 0.95em; margin: 0.5rem 0;'>
        Développée par le <strong>{APP_SETTINGS['department']}</strong>
    </p>
    <p style='color: #888; font-size: 0.9em; margin: 0.5rem 0;'>
        <strong>{APP_SETTINGS['institution']}</strong> - {APP_SETTINGS['campus']}
    </p>
    <div style='display: flex; justify-content: center; gap: 1rem; margin: 1rem 0;'>
        <span style='color: #999; font-size: 0.8em;'>
            📊 {stats['total_predictions']:,} prédictions
        </span>
        <span style='color: #999; font-size: 0.8em;'>
            ⏱️ {uptime} session
        </span>
        <span style='color: #999; font-size: 0.8em;'>
            💾 DB: {sys_status['db_type'].upper()}
        </span>
    </div>
    <p style='color: #AAA; font-size: 0.85em; margin-top: 0.5rem;'>
        © {current_year} {APP_SETTINGS['institution']}. Tous droits réservés.
    </p>
    <p style='color: #BBB; font-size: 0.8em; margin-top: 0.5rem;'>
        Propulsé par Streamlit | 🤖 ML avec XGBoost/LightGBM | 📊 Visualisation Plotly
    </p>
</div>
""", unsafe_allow_html=True)