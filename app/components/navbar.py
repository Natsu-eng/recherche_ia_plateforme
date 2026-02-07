"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/navbar.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Navigation Horizontale Moderne & Interactive
Version: 2.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

Barre de navigation fluide avec :
  - Pills animées au hover
  - Indicateur page active
  - Icons + labels clairs
  - Responsive design
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import streamlit as st  # type: ignore


@dataclass
class NavItem:
    """Item de navigation avec métadonnées."""
    
    key: str
    """Identifiant unique"""
    
    label: str
    """Label affiché (avec emoji)"""
    
    target: str
    """Chemin fichier Streamlit"""
    
    description: str
    """Description courte pour tooltip"""


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

NAV_ITEMS: List[NavItem] = [
    NavItem(
        key="home",
        label="🏠 Accueil",
        target="main.py",
        description="Vue d'ensemble de la plateforme"
    ),
    NavItem(
        key="formulateur",
        label="🧪 Formulateur",
        target="pages/2_Formulateur.py",
        description="Prédiction interactive de performances"
    ),
    NavItem(
        key="comparateur",
        label="📊 Comparateur",
        target="pages/3_Comparateur.py",
        description="Comparaison multi-formulations"
    ),
    NavItem(
        key="laboratoire",
        label="🔬 Laboratoire",
        target="pages/4_Laboratoire.py",
        description="Analyse de sensibilité paramétrique"
    ),
    NavItem(
        key="optimiseur",
        label="🎯 Optimiseur",
        target="pages/5_Optimiseur.py",
        description="Optimisation inverse coût/CO₂"
    ),
    NavItem(
        key="analyse",
        label="📈 Analyses",
        target="pages/6_Analyse_Donnees.py",
        description="Import & analyse de données"
    ),
    NavItem(
        key="config",
        label="⚙️ Config",
        target="pages/7_Configuration.py",
        description="Paramètres & diagnostic système"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# RENDU NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════


def render_top_nav(active_page: str) -> None:
    """
    Affiche une barre de navigation horizontale moderne.
    
    Features:
      - Pills avec effet hover
      - Highlight page active
      - Tooltips descriptifs
      - Responsive (wrap sur mobile)
    
    Args:
        active_page: Clé de la page actuellement affichée
    
    Example:
        >>> from app.components.navbar import render_top_nav
        >>> render_top_nav(active_page="formulateur")
    """
    # CSS Navigation moderne
    st.markdown("""
    <style>
        /* Container navigation */
        .imt-navbar {
            background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
            padding: 1rem 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            position: sticky;
            top: 0;
            z-index: 1000;
            margin-bottom: 2rem;
        }
        
        /* Pills conteneur */
        .imt-nav-pills {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            justify-content: center;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 1rem;
        }
        
        /* Pill individuelle */
        .imt-nav-pill {
            background: rgba(255, 255, 255, 0.15);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            backdrop-filter: blur(10px);
            position: relative;
            overflow: hidden;
        }
        
        /* Effet hover */
        .imt-nav-pill:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }
        
        /* Page active */
        .imt-nav-pill-active {
            background: white;
            color: #1976D2;
            border-color: white;
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
            font-weight: 700;
        }
        
        .imt-nav-pill-active:hover {
            transform: translateY(-3px);
        }
        
        /* Animation d'apparition */
        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .imt-navbar {
            animation: slideDown 0.5s ease-out;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Rendu HTML
    st.markdown('<div class="imt-navbar"><div class="imt-nav-pills">', unsafe_allow_html=True)
    
    # Colonnes Streamlit pour boutons
    cols = st.columns(len(NAV_ITEMS))
    
    for idx, item in enumerate(NAV_ITEMS):
        with cols[idx]:
            # Classe CSS selon état
            css_class = "imt-nav-pill"
            if item.key == active_page:
                css_class += " imt-nav-pill-active"
            
            # Bouton avec tooltip
            if st.button(
                item.label,
                key=f"nav_{item.key}",
                help=item.description,
                use_container_width=True
            ):
                # Navigation
                try:
                    st.switch_page(item.target)
                except Exception as e:
                    st.error(
                        f"⚠️ Navigation impossible vers {item.target}. "
                        f"Vérifiez que le fichier existe.\n\nErreur : {e}"
                    )
    
    st.markdown('</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BADGE STATUT (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════════


def render_status_badge(model_loaded: bool, db_connected: bool) -> None:
    """
    Affiche des badges de statut système dans la navbar.
    
    Args:
        model_loaded: True si modèle ML chargé
        db_connected: True si DB connectée
    """
    st.markdown("""
    <div style='text-align: center; margin-top: 0.5rem;'>
        <span style='background: #4CAF50; color: white; padding: 4px 12px; 
                     border-radius: 12px; font-size: 0.75rem; margin: 0 4px;'>
            🤖 Modèle {status_model}
        </span>
        <span style='background: #2196F3; color: white; padding: 4px 12px; 
                     border-radius: 12px; font-size: 0.75rem; margin: 0 4px;'>
            💾 DB {status_db}
        </span>
    </div>
    """.format(
        status_model="OK" if model_loaded else "KO",
        status_db="OK" if db_connected else "KO"
    ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BREADCRUMB (FIL D'ARIANE)
# ═══════════════════════════════════════════════════════════════════════════════


def render_breadcrumb(current_page: str) -> None:
    """
    Affiche un fil d'Ariane sous la navbar.
    
    Args:
        current_page: Nom de la page actuelle
    """
    # Trouver l'item actif
    active_item = next((item for item in NAV_ITEMS if item.key == current_page), None)
    
    if active_item:
        st.markdown(f"""
        <div style='padding: 0.5rem 0; color: #666; font-size: 0.9rem; 
                    text-align: center; margin-bottom: 1rem;'>
            🏠 Accueil / <strong>{active_item.label}</strong>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════


__all__ = [
    "render_top_nav",
    "render_status_badge",
    "render_breadcrumb",
    "NAV_ITEMS"
]