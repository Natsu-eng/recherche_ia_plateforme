"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/styles/theme.py
Description: Thème personnalisé avec charte IMT Nord Europe
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
from typing import Dict, Literal
import logging

from config.settings import UI_SETTINGS
from config.constants import COLOR_PALETTE

logger = logging.getLogger(__name__)


def get_theme_colors(theme: Literal["Clair", "Sombre", "Auto"] = "Clair") -> Dict[str, str]:
    """
    Retourne la palette de couleurs selon le thème sélectionné.
    
    Args:
        theme: Thème ("Clair", "Sombre", "Auto")
    
    Returns:
        Dict avec couleurs adaptées
    """
    
    # Détecter thème auto (utilise préférence système si disponible)
    if theme == "Auto":
        # Streamlit n'a pas d'API native pour détecter le thème système
        # On utilise "Clair" par défaut
        theme = "Clair"
    
    if theme == "Sombre":
        return {
            'background': '#0e1117',
            'background_secondary': '#1a1d24',
            'text_primary': '#fafafa',
            'text_secondary': '#b8bdc4',
            'border': '#31333F',
            'card_bg': '#1a1d24',
            'primary': COLOR_PALETTE['primary'],
            'accent': COLOR_PALETTE['accent']
        }
    else:  # Clair
        return {
            'background': '#ffffff',
            'background_secondary': '#f0f2f6',
            'text_primary': '#262730',
            'text_secondary': '#6c757d',
            'border': '#e0e0e0',
            'card_bg': '#ffffff',
            'primary': COLOR_PALETTE['primary'],
            'accent': COLOR_PALETTE['accent']
        }


def apply_custom_theme(theme: Literal["Clair", "Sombre", "Auto"] = "Clair") -> None:
    """
    Applique le thème personnalisé IMT via CSS injecté.
    
    Args:
        theme: Thème sélectionné
    
    Note:
        Doit être appelé au début de chaque page Streamlit
    """
    
    colors = get_theme_colors(theme)
    
    # CSS personnalisé
    custom_css = f"""
    <style>
    /* ═══════════════════════════════════════════════════════════════ */
    /* THÈME PERSONNALISÉ IMT NORD EUROPE                                */
    /* ═══════════════════════════════════════════════════════════════ */
    
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* ─── VARIABLES CSS ─── */
    :root {{
        --primary-color: {colors['primary']};
        --accent-color: {colors['accent']};
        --background-color: {colors['background']};
        --text-color: {colors['text_primary']};
        --border-color: {colors['border']};
        --card-background: {colors['card_bg']};
        
        --font-main: 'Inter', sans-serif;
        --font-heading: 'Poppins', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
        
        --border-radius: 10px;
        --transition: all 0.3s ease;
    }}
    
    /* ─── BODY & CONTAINERS ─── */
    body {{
        font-family: var(--font-main);
        color: var(--text-color);
        background-color: var(--background-color);
    }}
    
    .main {{
        background-color: var(--background-color);
    }}
    
    /* ─── HEADINGS ─── */
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--font-heading);
        color: {colors['primary']};
        font-weight: 600;
    }}
    
    h1 {{
        font-size: 2.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 3px solid {colors['primary']};
        padding-bottom: 0.5rem;
    }}
    
    h2 {{
        font-size: 2rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }}
    
    h3 {{
        font-size: 1.5rem;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }}
    
    /* ─── CARDS & CONTAINERS ─── */
    /* .stMarkdown {{
        background-color: var(--card-background);
    }} */

    /* Version précise : fond uniquement sur les markdown "simples" */
    # type: ignore[attr-defined]   ← ajoute cette ligne
    div[data-testid="stMarkdownContainer"]:not(:has(h2, div[style*="linear-gradient"])) {{
        background-color: var(--card-background);
        border-radius: var(--border-radius);
        padding: 1rem;
    }}
    
    div[data-testid="stVerticalBlock"] > div:has(div.element-container) {{
        background-color: var(--card-background);
        border-radius: var(--border-radius);
        padding: 1rem;
        border: 1px solid var(--border-color);
        transition: var(--transition);
    }}
    
    div[data-testid="stVerticalBlock"] > div:has(div.element-container):hover {{
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
    }}
    
    /* ─── BUTTONS ─── */
    .stButton button {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['accent']} 100%);
        color: white;
        border: none;
        border-radius: var(--border-radius);
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-family: var(--font-main);
        transition: var(--transition);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    .stButton button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}
    
    .stButton button:active {{
        transform: translateY(0);
    }}
    
    /* Bouton secondaire */
    .stButton button[kind="secondary"] {{
        background: transparent;
        border: 2px solid {colors['primary']};
        color: {colors['primary']};
    }}
    
    /* ─── INPUTS & FORMS ─── */
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox select,
    .stTextArea textarea {{
        border-radius: var(--border-radius);
        border: 2px solid var(--border-color);
        padding: 0.75rem;
        font-family: var(--font-main);
        transition: var(--transition);
    }}
    
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stSelectbox select:focus,
    .stTextArea textarea:focus {{
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px {colors['primary']}20;
    }}
    
    /* ─── SLIDERS ─── */
    .stSlider {{
        padding: 1rem 0;
    }}
    
    .stSlider > div > div > div > div {{
        background-color: {colors['primary']};
    }}
    
    /* Thumb (poignée) */
    .stSlider > div > div > div > div > div {{
        background-color: {colors['primary']};
        border: 3px solid white;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
    }}
    
    /* ─── METRICS ─── */
    div[data-testid="stMetricValue"] {{
        font-size: 2rem;
        font-weight: 700;
        color: {colors['primary']};
        font-family: var(--font-heading);
    }}
    
    div[data-testid="stMetricDelta"] {{
        font-size: 1rem;
    }}
    
    /* ─── TABS ─── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 1rem;
        background-color: transparent;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        background-color: transparent;
        border-radius: var(--border-radius) var(--border-radius) 0 0;
        color: {colors['text_secondary']};
        padding: 0 1.5rem;
        font-weight: 600;
        transition: var(--transition);
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {colors['primary']}10;
        color: {colors['primary']};
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {colors['primary']};
        color: white !important;
    }}
    
    /* ─── EXPANDERS ─── */
    .streamlit-expanderHeader {{
        background-color: {colors['background_secondary']};
        border-radius: var(--border-radius);
        padding: 0.75rem 1rem;
        font-weight: 600;
        transition: var(--transition);
    }}
    
    .streamlit-expanderHeader:hover {{
        background-color: {colors['primary']}15;
        color: {colors['primary']};
    }}
    
    /* ─── ALERTS (info, success, warning, error) ─── */
    .stAlert {{
        border-radius: var(--border-radius);
        border-left-width: 4px;
        padding: 1rem 1.5rem;
    }}
    
    /* ─── DATAFRAME / TABLES ─── */
    .dataframe {{
        border-radius: var(--border-radius);
        overflow: hidden;
        border: 1px solid var(--border-color);
    }}
    
    .dataframe th {{
        background-color: {colors['primary']};
        color: white;
        font-weight: 600;
        padding: 0.75rem;
    }}
    
    .dataframe td {{
        padding: 0.5rem 0.75rem;
    }}
    
    .dataframe tr:nth-child(even) {{
        background-color: {colors['background_secondary']};
    }}
    
    /* ─── SIDEBAR ─── */
    section[data-testid="stSidebar"] {{
        background-color: {colors['background_secondary']};
        border-right: 2px solid {colors['border']};
    }}
    
    section[data-testid="stSidebar"] .stMarkdown {{
        color: {colors['text_primary']};
    }}
    
    /* ─── PROGRESS BAR ─── */
    .stProgress > div > div > div {{
        background-color: {colors['primary']};
        border-radius: 10px;
    }}
    
    /* ─── SPINNER ─── */
    .stSpinner > div {{
        border-top-color: {colors['primary']};
    }}
    
    /* ─── CODE BLOCKS ─── */
    code {{
        font-family: var(--font-mono);
        background-color: {colors['background_secondary']};
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
        font-size: 0.9em;
    }}
    
    pre {{
        font-family: var(--font-mono);
        background-color: {colors['background_secondary']};
        padding: 1rem;
        border-radius: var(--border-radius);
        border-left: 4px solid {colors['primary']};
        overflow-x: auto;
    }}
    
    /* ─── SCROLLBAR ─── */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {colors['background_secondary']};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {colors['primary']};
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {colors['accent']};
    }}
    
    /* ─── ANIMATIONS ─── */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .element-container {{
        animation: fadeIn 0.3s ease;
    }}
    
    /* ─── RESPONSIVE ─── */
    @media (max-width: 768px) {{
        h1 {{ font-size: 2rem; }}
        h2 {{ font-size: 1.5rem; }}
        
        .stButton button {{
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }}
    }}
    
    /* ═══════════════════════════════════════════════════════════════ */
    /* FIN DU THÈME                                                      */
    /* ═══════════════════════════════════════════════════════════════ */
    </style>
    """
    
    # Injecter CSS
    st.markdown(custom_css, unsafe_allow_html=True)
    
    logger.debug(f"Thème '{theme}' appliqué avec succès")


__all__ = ['apply_custom_theme', 'get_theme_colors']