"""
═══════════════════════════════════════════════════════════════════════════════
APPLICATION: Plateforme R&D Béton IA
Point d'entrée: app.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════

Lancement:
    streamlit run app.py --server.port=8501
"""

import streamlit as st
import logging
from pathlib import Path
import sys

# Ajouter le répertoire racine au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import APP_SETTINGS, POSTGRES_SETTINGS, MODEL_SETTINGS
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.models.loader import load_production_assets
from database.manager import DatabaseManager

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title=APP_SETTINGS['app_name'],
    page_icon=APP_SETTINGS['app_icon'],
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': APP_SETTINGS['website'],
        'Report a bug': APP_SETTINGS['email'],
        'About': f"""
        # {APP_SETTINGS['app_name']}
        
        **Version**: {APP_SETTINGS['version']}  
        **Institution**: {APP_SETTINGS['institution']}  
        
        Plateforme d'aide à la décision pour la formulation du béton 
        utilisant l'Intelligence Artificielle.
        
        © 2026 IMT Nord Europe
        """
    }
)

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
from app.core.session_manager import initialize_session

initialize_session()

# ═══════════════════════════════════════════════════════════════════════════════
# APPLIQUER THÈME
# ═══════════════════════════════════════════════════════════════════════════════

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

sidebar_state = render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ACCUEIL (CONTENU PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════════════════

# Header
st.markdown(
    f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem; color: {COLOR_PALETTE['primary']}; margin: 0;">
            {APP_SETTINGS['app_icon']} {APP_SETTINGS['app_name']}
        </h1>
        <p style="font-size: 1.2rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
            Intelligence Artificielle pour la Formulation du Béton
        </p>
        <hr style="width: 50%; margin: 1.5rem auto; border: none; border-top: 3px solid {COLOR_PALETTE['accent']};">
    </div>
    """,
    unsafe_allow_html=True
)

# ─── PRÉSENTATION ───
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        """
        ### 🎯 Bienvenue sur la Plateforme R&D
        
        Cette application utilise des **modèles d'apprentissage automatique avancés** 
        (XGBoost) pour prédire les propriétés du béton et optimiser les formulations 
        selon vos objectifs (coût, empreinte carbone, performance).
        
        #### ✨ Fonctionnalités
        
        - **📊 Formulateur** : Prédiction instantanée de 3 cibles (Résistance, Diffusion Cl⁻, Carbonatation)
        - **🧪 Laboratoire** : Analyse de sensibilité paramétrique
        - **⚖️ Comparateur** : Benchmark de formulations
        - **🎯 Optimiseur** : Algorithme génétique pour optimisation multi-objectifs
        - **📈 Analyse de Données** : Historique et tendances
        - **⚙️ Configuration** : Diagnostics et paramètres
        
        ---
        """
    )

# ─── STATISTIQUES RAPIDES ───
st.markdown("### 📊 Aperçu des Performances")

if st.session_state.get('db_manager'):
    try:
        stats = st.session_state['db_manager'].get_live_stats()
        
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            st.metric(
                label="🔮 Prédictions Totales",
                value=f"{stats.get('total_predictions', 0):,}"
            )
        
        with col_s2:
            st.metric(
                label="🧪 Formulations Analysées",
                value=f"{stats.get('formulations_analyzed', 0):,}"
            )
        
        with col_s3:
            st.metric(
                label="💪 Résistance Moyenne",
                value=f"{stats.get('avg_resistance', 0):.1f} MPa"
            )
        
        with col_s4:
            db_status = "🟢 Opérationnelle" if stats.get('db_connected', False) else "🔴 Hors ligne"
            st.metric(
                label="🗄️ Base de Données",
                value=db_status
            )
    
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        st.warning("⚠️ Statistiques temporairement indisponibles")
else:
    st.info("💡 Base de données non connectée. Les statistiques ne sont pas disponibles.")

st.markdown("---")

# ─── DÉMARRAGE RAPIDE ───
st.markdown("### 🚀 Démarrage Rapide")

col_q1, col_q2, col_q3 = st.columns(3)

with col_q1:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e3c7215 0%, #1e3c7205 100%); 
                    border-left: 4px solid #1e3c72; 
                    padding: 1.5rem; 
                    border-radius: 8px;">
            <h4 style="margin-top: 0;">📊 Formulateur</h4>
            <p>Saisissez votre composition et obtenez instantanément les prédictions 
            de résistance, diffusion des chlorures et carbonatation.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("➡️ Accéder au Formulateur", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Formulateur.py")

with col_q2:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #9c27b015 0%, #9c27b005 100%); 
                    border-left: 4px solid #9c27b0; 
                    padding: 1.5rem; 
                    border-radius: 8px;">
            <h4 style="margin-top: 0;">🧪 Laboratoire</h4>
            <p>Analysez la sensibilité paramétrique et étudiez l'impact 
            de chaque composant sur les propriétés du béton.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("➡️ Lancer l'Analyse", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Laboratoire.py")

with col_q3:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #ff7f0e15 0%, #ff7f0e05 100%); 
                    border-left: 4px solid #ff7f0e; 
                    padding: 1.5rem; 
                    border-radius: 8px;">
            <h4 style="margin-top: 0;">⚖️ Comparateur</h4>
            <p>Comparez jusqu'à 10 formulations côte à côte pour 
            identifier la plus adaptée à vos besoins.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("➡️ Comparer", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Comparateur.py")

st.markdown("---")

# ─── DERNIÈRES PRÉDICTIONS ───
st.markdown("### 🕐 Dernières Prédictions")

if st.session_state.get('db_manager'):
    try:
        recent = st.session_state['db_manager'].get_recent_predictions(limit=5)
        
        if recent:
            # Créer DataFrame
            import pandas as pd
            df_recent = pd.DataFrame(recent)
            
            # Colonnes à afficher
            display_cols = [
                'formulation_name',
                'resistance_predicted',
                'diffusion_cl_predicted',
                'carbonatation_predicted',
                'ratio_e_l',
                'created_at'
            ]
            
            # Renommer pour affichage
            df_display = df_recent[display_cols].copy()
            df_display.columns = [
                'Formulation',
                'Résistance (MPa)',
                'Diffusion Cl⁻',
                'Carbonatation (mm)',
                'Ratio E/L',
                'Date'
            ]
            
            st.dataframe(
                df_display,
                width="stretch",
                hide_index=True
            )
        else:
            st.info("Aucune prédiction récente. Commencez par utiliser le Formulateur !")
    
    except Exception as e:
        logger.error(f"Erreur affichage historique: {e}")
        st.warning("⚠️ Impossible de charger l'historique")
else:
    st.info("💡 Connectez la base de données pour voir l'historique")

st.markdown("---")

# ─── FOOTER ───
st.markdown(
    f"""
    <div style="text-align: center; padding: 2rem 0; color: #6c757d;">
        <p>
            <strong>{APP_SETTINGS['institution']}</strong> | {APP_SETTINGS['campus']}  <br>
            {APP_SETTINGS['department']}
        </p>
        <p style="font-size: 0.9rem;">
            📧 {APP_SETTINGS['email']} | 📞 {APP_SETTINGS['phone']}  <br>
            🌐 <a href="{APP_SETTINGS['website']}" target="_blank" style="color: {COLOR_PALETTE['primary']};">
                {APP_SETTINGS['website']}
            </a>
        </p>
        <hr style="width: 30%; margin: 1rem auto; border: none; border-top: 1px solid #e0e0e0;">
        <p style="font-size: 0.85rem;">
            © 2026 IMT Nord Europe - Tous droits réservés  <br>
            Version {APP_SETTINGS['version']} | Powered by Streamlit & XGBoost
        </p>
    </div>
    """,
    unsafe_allow_html=True
)