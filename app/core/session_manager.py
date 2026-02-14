# app/core/session_manager.py
import streamlit as st
from app.models.loader import load_production_assets
import logging

logger = logging.getLogger(__name__)

def initialize_session():
    """
    Initialise les éléments critiques dans session_state (modèle, DB, thème, etc.)
    À appeler au début de CHAQUE page.
    """
    # ─── MODÈLE ML ───
    if 'model' not in st.session_state:
        with st.spinner("🔄 Chargement du modèle XGBoost..."):
            try:
                model, features, metadata = load_production_assets()
                st.session_state['model'] = model
                st.session_state['features'] = features
                st.session_state['metadata'] = metadata
                logger.info("Modèle chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur chargement modèle: {e}", exc_info=True)
                st.error(f"❌ Impossible de charger le modèle ML : {e}")
                st.stop()

    # ─── BASE DE DONNÉES ───
    if 'db_manager' not in st.session_state:
        from database.manager import DatabaseManager
        from config.settings import POSTGRES_SETTINGS
        import os
        from dotenv import load_dotenv
        
        # Force le chargement du .env (sécurité)
        load_dotenv()
        
        try:
            db_url = POSTGRES_SETTINGS['database_url']
            logger.info(f"Tentative connexion DB avec: {db_url}")
            
            db_manager = DatabaseManager(
                db_url=db_url,
                min_connections=2,
                max_connections=10
            )
            st.session_state['db_manager'] = db_manager
            logger.info("Connexion PostgreSQL établie")
        except Exception as e:
            logger.warning(f"Connexion DB échouée: {e}")
            st.session_state['db_manager'] = None

    # ─── THÈME ───
    if 'app_theme' not in st.session_state:
        st.session_state['app_theme'] = "Clair"

    # ─── AUTRES (historique, favoris, etc.) ───
    if 'comparison_formulations' not in st.session_state:
        st.session_state['comparison_formulations'] = []
    
    if 'favorites' not in st.session_state:
        st.session_state['favorites'] = []
    
    if 'last_prediction' not in st.session_state:
        st.session_state['last_prediction'] = None

    # Optionnel : petite vérif silencieuse
    if st.session_state.get('model') is None:
        st.warning("⚠️ Modèle non disponible – certaines fonctionnalités seront limitées")