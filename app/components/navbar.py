"""
═══════════════════════════════════════════════════════════════════════════════
COMPOSANT: Barre de navigation horizontale
Fichier: app/components/navbar.py
Version: 2.0.0 - Design Corrigé
═══════════════════════════════════════════════════════════════════════════════

CORRECTIONS v2.0.0:
✅ Logo et titre intégrés dans la navbar
✅ Alignement vertical parfait
✅ Espacement homogène
✅ Design moderne et professionnel
"""

import streamlit as st
from config.constants import COLOR_PALETTE


def render_navbar(current_page: str = ""):
    """
    Affiche une barre de navigation horizontale moderne.
    
    Args:
        current_page: Nom de la page active (pour highlighting)
    """
    
    # ═══════════════════════════════════════════════════════════
    # CSS NAVBAR MODERNE
    # ═══════════════════════════════════════════════════════════
    
    st.markdown(f"""
    <style>
        /* Container principal */
        .navbar-container {{
            background: linear-gradient(135deg, {COLOR_PALETTE['primary']} 0%, {COLOR_PALETTE['secondary']} 100%);
            padding: 1rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        /* Wrapper flex */
        .navbar-wrapper {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2rem;
            width: 100%;
        }}
        
        /* Section logo + titre */
        .navbar-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            color: white;
            font-size: 1.4rem;
            font-weight: 700;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        
        .navbar-brand .icon {{
            font-size: 2rem;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        }}
        
        .navbar-brand .text {{
            font-size: 1.3rem;
            letter-spacing: 0.5px;
        }}
        
        /* Section navigation */
        .navbar-nav {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            flex-grow: 1;
            justify-content: flex-end;
        }}
        
        /* Style boutons Streamlit (override) */
        .navbar-nav .stButton {{
            margin: 0 !important;
        }}
        
        .navbar-nav .stButton > button {{
            background: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            transition: all 0.3s ease !important;
            white-space: nowrap !important;
            height: 42px !important;
            display: flex !important;
            align-items: center !important;
            gap: 6px !important;
        }}
        
        .navbar-nav .stButton > button:hover {{
            background: rgba(255, 255, 255, 0.2) !important;
            border-color: rgba(255, 255, 255, 0.4) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }}
        
        .navbar-nav .stButton > button:active,
        .navbar-nav .stButton > button:focus {{
            background: rgba(255, 255, 255, 0.25) !important;
            border-color: white !important;
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3) !important;
        }}
        
        /* Style page active */
        .navbar-nav .stButton.active > button {{
            background: rgba(255, 255, 255, 0.3) !important;
            border-color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.5) !important;
        }}
        
        /* Responsive */
        @media (max-width: 1200px) {{
            .navbar-wrapper {{
                flex-direction: column;
                gap: 1rem;
            }}
            
            .navbar-brand {{
                justify-content: center;
                width: 100%;
            }}
            
            .navbar-nav {{
                justify-content: center;
                width: 100%;
            }}
        }}
        
        @media (max-width: 768px) {{
            .navbar-container {{
                padding: 1rem;
            }}
            
            .navbar-brand .text {{
                font-size: 1.1rem;
            }}
            
            .navbar-nav .stButton > button {{
                font-size: 0.85rem !important;
                padding: 0.4rem 0.8rem !important;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════
    # STRUCTURE NAVBAR
    # ═══════════════════════════════════════════════════════════
    
    st.markdown('<div class="navbar-container">', unsafe_allow_html=True)
    st.markdown('<div class="navbar-wrapper">', unsafe_allow_html=True)
    
    # ───────────────────────────────────────────────────────────
    # LOGO + TITRE
    # ───────────────────────────────────────────────────────────
    
    st.markdown("""
    <div class="navbar-brand">
        <span class="icon">🏗️</span>
        <span class="text">Plateforme R&D Béton IA</span>
    </div>
    """, unsafe_allow_html=True)
    
    # ───────────────────────────────────────────────────────────
    # NAVIGATION (dans une seule div)
    # ───────────────────────────────────────────────────────────
    
    st.markdown('<div class="navbar-nav">', unsafe_allow_html=True)
    
    # Définition des pages
    pages = [
        {"name": "Accueil", "icon": "🏠", "path": "app.py"},
        {"name": "Formulateur", "icon": "📊", "path": "pages/1_Formulateur.py"},
        {"name": "Laboratoire", "icon": "🧪", "path": "pages/2_Laboratoire.py"},
        {"name": "Comparateur", "icon": "⚖️", "path": "pages/3_Comparateur.py"},
        {"name": "Optimiseur", "icon": "🎯", "path": "pages/4_Optimiseur.py"},
        #{"name": "Analyse de Données", "icon": "📈", "path": "pages/5_Analyse_Donnees.py"},
        #{"name": "Configuration", "icon": "⚙️", "path": "pages/6_Configuration.py"},
        #{"name": "Carbone", "icon": "🌍", "path": "pages/7_Analyse_Carbone.py"},
    ]
    
    # Créer colonnes pour les boutons (inline)
    cols = st.columns(len(pages))
    
    for i, page in enumerate(pages):
        with cols[i]:
            # Classe active si page courante
            button_class = "active" if current_page == page["name"] else ""
            
            # Créer bouton avec classe CSS custom
            if button_class:
                st.markdown(f'<div class="stButton {button_class}">', unsafe_allow_html=True)
            
            if st.button(
                f"{page['icon']} {page['name']}",
                key=f"nav_{page['name']}",
                use_container_width=True
            ):
                st.switch_page(page["path"])
            
            if button_class:
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin navbar-nav
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin navbar-wrapper
    st.markdown('</div>', unsafe_allow_html=True)  # Fin navbar-container


# ═══════════════════════════════════════════════════════════════
# VERSION ALTERNATIVE : NAVBAR SIMPLE (si problèmes CSS)
# ═══════════════════════════════════════════════════════════════

def render_navbar_simple(current_page: str = ""):
    """
    Version simplifiée de la navbar (fallback).
    Utilise uniquement les composants Streamlit natifs.
    """
    
    # Header avec logo
    col_logo, col_nav = st.columns([2, 5])
    
    with col_logo:
        st.markdown("""
        ### 🏗️ Plateforme R&D Béton IA
        """)
    
    with col_nav:
        # Navigation en colonnes
        pages = [
            ("🏠 Accueil", "app.py"),
            ("📊 Formulateur", "pages/1_Formulateur.py"),
            ("🧪 Laboratoire", "pages/2_Laboratoire.py"),
            ("⚖️ Comparateur", "pages/3_Comparateur.py"),
            ("🎯 Optimiseur", "pages/4_Optimiseur.py"),
            #("📈 Analyse de Données", "pages/5_Analyse_Donnees.py"),
            #("⚙️ Configuration", "pages/6_Configuration.py"),
            #("🌍 Carbone", "pages/7_Analyse_Carbone.py"),

        ]
        
        cols = st.columns(len(pages))
        
        for i, (label, path) in enumerate(pages):
            with cols[i]:
                page_name = label.split()[1] if len(label.split()) > 1 else label
                
                if st.button(
                    label,
                    key=f"nav_simple_{i}",
                    use_container_width=True,
                    type="primary" if current_page == page_name else "secondary"
                ):
                    st.switch_page(path)
    
    st.markdown("---")


__all__ = ['render_navbar', 'render_navbar_simple']