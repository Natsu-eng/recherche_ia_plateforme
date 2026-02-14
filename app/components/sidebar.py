"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/sidebar.py
Description: Sidebar avec navigation, stats temps réel et sélecteur thème
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
from typing import Dict, Optional
from datetime import datetime
import logging

from config.settings import APP_SETTINGS, UI_SETTINGS
from config.constants import STATUS_EMOJI

logger = logging.getLogger(__name__)


def render_sidebar(db_manager: Optional[object] = None) -> Dict:
    """
    Affiche la sidebar avec logo, navigation, stats et thème.
    
    Args:
        db_manager: Instance DatabaseManager (optionnel)
    
    Returns:
        Dict avec choix utilisateur (page, thème, etc.)
    """
    
    with st.sidebar:
        # ═══════════════════════════════════════════════════════════════
        # 🏛️ HEADER : Logo + Titre
        # ═══════════════════════════════════════════════════════════════
        
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem 0;">
                <h1 style="color: {UI_SETTINGS['colors']['primary']}; 
                           font-size: 1.8rem; 
                           margin: 0;">
                    {APP_SETTINGS['app_icon']} {APP_SETTINGS['app_name']}
                </h1>
                <p style="color: {UI_SETTINGS['colors']['secondary']}; 
                          font-size: 0.9rem; 
                          margin-top: 0.5rem;">
                    {APP_SETTINGS['institution']}<br>
                    <small>{APP_SETTINGS['department']}</small>
                </p>
            </div>
            <hr style="margin: 1rem 0; 
                       border: none; 
                       border-top: 2px solid {UI_SETTINGS['colors']['accent']};">
            """,
            unsafe_allow_html=True
        )
        
        # ═══════════════════════════════════════════════════════════════
        # 📊 QUICK STATS (Temps Réel)
        # ═══════════════════════════════════════════════════════════════
        
        st.markdown("### 📊 Statistiques Live")
        
        if db_manager:
            try:
                stats = db_manager.get_live_stats()
                
                # Layout 2 colonnes pour compacité
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        label="Prédictions",
                        value=f"{stats.get('total_predictions', 0):,}",
                        delta=None
                    )
                    
                    st.metric(
                        label="Formulations",
                        value=f"{stats.get('formulations_analyzed', 0):,}",
                        delta=None
                    )
                
                with col2:
                    st.metric(
                        label="Résistance Moy.",
                        value=f"{stats.get('avg_resistance', 0):.1f}",
                        delta=None,
                        help="MPa"
                    )
                    
                    # Statut connexion DB
                    db_status = "🟢 Connecté" if stats.get('db_connected', False) else "🔴 Hors ligne"
                    st.caption(db_status)
                
                # Dernière mise à jour
                last_update = stats.get('last_update', datetime.now())
                st.caption(f"🕐 MAJ: {last_update.strftime('%H:%M:%S')}")
                
            except Exception as e:
                logger.error(f"Erreur stats sidebar: {e}")
                st.warning("⚠️ Stats indisponibles")
        else:
            st.info("💡 Base de données non connectée")
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # 🎨 SÉLECTEUR DE THÈME
        # ═══════════════════════════════════════════════════════════════
        
        st.markdown("### 🎨 Apparence")
        
        theme = st.selectbox(
            label="Thème",
            options=["Clair", "Sombre", "Auto"],
            index=0,
            key="theme_selector",
            help="Modifie l'apparence de l'interface"
        )
        
        # Stocker dans session state
        st.session_state['app_theme'] = theme
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # ℹ️ INFORMATIONS APPLICATION
        # ═══════════════════════════════════════════════════════════════
        
        with st.expander("ℹ️ À propos", expanded=False):
            st.markdown(
                f"""
                **Version**: {APP_SETTINGS['version']}  
                **Release**: {APP_SETTINGS['release_date']}  
                
                **Campus**: {APP_SETTINGS['campus']}  
                **Contact**: {APP_SETTINGS['email']}  
                
                ---
                
                **Modules actifs** :
                - ✅ Prédictions Multi-Cibles
                - ✅ Optimisation Génétique
                - ✅ Analyse de Sensibilité
                - ✅ Validation EN 206
                - ✅ Export PDF/CSV/Excel
                
                [🌐 Site Web]({APP_SETTINGS['website']})
                """
            )
        
        # ═══════════════════════════════════════════════════════════════
        # 🔧 ACTIONS RAPIDES (Optionnel)
        # ═══════════════════════════════════════════════════════════════
        
        st.markdown("---")
        
        st.markdown("### ⚡ Actions Rapides")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.rerun()
        
        with col_b:
            if st.button("💾 Backup DB", use_container_width=True, disabled=True):
                st.toast("Fonctionnalité à venir", icon="ℹ️")
        
        # ═══════════════════════════════════════════════════════════════
        # 📌 FOOTER
        # ═══════════════════════════════════════════════════════════════
        
        st.markdown("---")
        st.caption(
            f"© 2026 {APP_SETTINGS['institution']}  \n"
            f"Powered by Streamlit & XGBoost"
        )
    
    # Retourner état sidebar
    return {
        'theme': theme,
        'stats_loaded': db_manager is not None
    }


def render_compact_stats(db_manager: Optional[object] = None) -> None:
    """
    Version compacte des stats (pour header de page par exemple).
    
    Args:
        db_manager: Instance DatabaseManager
    """
    
    if not db_manager:
        return
    
    try:
        stats = db_manager.get_live_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📊 Prédictions",
                value=f"{stats.get('total_predictions', 0):,}"
            )
        
        with col2:
            st.metric(
                label="🧪 Formulations",
                value=f"{stats.get('formulations_analyzed', 0):,}"
            )
        
        with col3:
            st.metric(
                label="💪 Résistance Moy.",
                value=f"{stats.get('avg_resistance', 0):.1f} MPa"
            )
        
        with col4:
            db_icon = "🟢" if stats.get('db_connected', False) else "🔴"
            st.metric(
                label=f"{db_icon} Base de Données",
                value="Connectée" if stats.get('db_connected', False) else "Hors ligne"
            )
    
    except Exception as e:
        logger.error(f"Erreur stats compactes: {e}")
        st.caption("⚠️ Stats indisponibles")


__all__ = ['render_sidebar', 'render_compact_stats']