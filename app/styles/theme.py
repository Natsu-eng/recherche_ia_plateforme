"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/styles/theme.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Chargement & Application du Thème CSS Personnalisé
Version: 2.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

Ce module gère :
  - Chargement du fichier custom.css
  - Application du thème global Streamlit
  - Configuration couleurs / polices / layout
"""

from pathlib import Path
import streamlit as st  # type: ignore


def apply_custom_theme() -> None:
    """
    Applique le thème CSS personnalisé à l'application Streamlit.
    
    Charge le fichier app/styles/custom.css et l'injecte via st.markdown.
    Doit être appelé au début de chaque page Streamlit.
    
    Usage:
        >>> from app.styles.theme import apply_custom_theme
        >>> apply_custom_theme()
    """
    # Chemin du fichier CSS
    css_file = Path(__file__).parent / "custom.css"
    
    if css_file.exists():
        with open(css_file, "r", encoding="utf-8") as f:
            css_content = f.read()
        
        # Injection CSS via st.markdown
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Fichier CSS introuvable : {css_file}")


def configure_page_theme() -> None:
    """
    Configure le thème global de la page Streamlit.
    
    Définit la palette de couleurs, polices et options d'affichage.
    À appeler dans st.set_page_config() ou au début de l'app.
    """
    st.markdown("""
    <style>
        /* Configuration générale Streamlit */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        /* Sidebar */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #1976D2;
            font-weight: 700;
        }
        
        /* Métriques Streamlit */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
            color: #1976D2;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #E3F2FD;
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "apply_custom_theme",
    "configure_page_theme"
]