"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/cards.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Cartes UI stylisées (KPI, Formations, Info)
Version: 2.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st  # type: ignore
from typing import Optional, Dict, Any


def render_kpi_card(
    title: str,
    value: Any,
    delta: Optional[float] = None,
    delta_label: str = "",
    color: str = "blue",
    icon: str = "",
    unit: str = ""
) -> None:
    """
    Affiche une carte KPI moderne avec tendance.
    
    Args:
        title: Titre de la métrique
        value: Valeur principale
        delta: Variation (positif = vert, négatif = rouge)
        delta_label: Libellé delta (ex: "cette semaine")
        color: Couleur thème (blue, green, purple, orange)
        icon: Emoji ou icône
        unit: Unité (%, €, kg, etc.)
    """
    # Palette de couleurs
    color_palette = {
        "blue": {
            "border": "#1976D2",
            "bg": "#E3F2FD",
            "delta_positive": "#1565C0",
            "delta_negative": "#D32F2F"
        },
        "green": {
            "border": "#388E3C",
            "bg": "#E8F5E9",
            "delta_positive": "#2E7D32",
            "delta_negative": "#D32F2F"
        },
        "purple": {
            "border": "#7B1FA2",
            "bg": "#F3E5F5",
            "delta_positive": "#6A1B9A",
            "delta_negative": "#D32F2F"
        },
        "orange": {
            "border": "#FF6F00",
            "bg": "#FFF3E0",
            "delta_positive": "#E65100",
            "delta_negative": "#D32F2F"
        }
    }
    
    # Déterminer couleurs
    colors = color_palette.get(color, color_palette["blue"])
    
    # Format valeur
    if isinstance(value, (int, float)):
        display_value = f"{value:,.0f}"
    else:
        display_value = str(value)
    
    if unit:
        display_value = f"{display_value}{unit}"
    
    # Format delta
    delta_html = ""
    if delta is not None:
        delta_color = colors["delta_positive"] if delta >= 0 else colors["delta_negative"]
        delta_symbol = "↗" if delta >= 0 else "↘"
        delta_html = f"""
        <div style="margin-top: 8px; color: {delta_color}; font-weight: 600;">
            {delta_symbol} {abs(delta):.1f} {delta_label}
        </div>
        """
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {colors['bg']} 0%, white 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid {colors['border']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.3s ease;
    ">
        <div>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 2em;">{icon}</span>
                <h3 style="margin: 0; color: {colors['border']}; font-size: 1.1rem;">
                    {title}
                </h3>
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #333;">
                {display_value}
            </div>
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_info_card(
    title: str,
    content: str,
    icon: str = "ℹ️",
    color: str = "blue",
    width: str = "100%"
) -> None:
    """
    Carte d'information avec icône et contenu.
    
    Args:
        title: Titre de la carte
        content: Contenu HTML/Markdown
        icon: Emoji icône
        color: Couleur (blue, green, yellow, red)
        width: Largeur CSS
    """
    colors = {
        "blue": {"border": "#1976D2", "bg": "#E3F2FD"},
        "green": {"border": "#388E3C", "bg": "#E8F5E9"},
        "yellow": {"border": "#F57C00", "bg": "#FFF3E0"},
        "red": {"border": "#D32F2F", "bg": "#FFEBEE"}
    }
    
    color_scheme = colors.get(color, colors["blue"])
    
    st.markdown(f"""
    <div style="
        background: white;
        border: 2px solid {color_scheme['border']};
        border-left: 6px solid {color_scheme['border']};
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        width: {width};
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
            <span style="font-size: 1.5em;">{icon}</span>
            <h4 style="margin: 0; color: {color_scheme['border']};">{title}</h4>
        </div>
        <div style="color: #444; line-height: 1.6;">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_formulation_card(
    formulation: Dict[str, float],
    name: str,
    index: int,
    on_select=None
) -> None:
    """
    Carte pour afficher une formulation béton.
    
    Args:
        formulation: Dictionnaire composition
        name: Nom de la formulation
        index: Index unique
        on_select: Fonction callback si cliquée
    """
    # Formatage valeurs principales
    resistance = formulation.get("Resistance", 0)
    ratio_el = formulation.get("Ratio_E_L", 0)
    cost = formulation.get("Cost", 0)
    
    # Couleur selon performance
    if resistance >= 40:
        border_color = "#388E3C"  # Vert
        performance = "Haute Performance"
    elif resistance >= 25:
        border_color = "#1976D2"  # Bleu
        performance = "Standard"
    else:
        border_color = "#F57C00"  # Orange
        performance = "Faible Performance"
    
    st.markdown(f"""
    <div style="
        background: white;
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 3px 6px rgba(0,0,0,0.05);
    "
    onmouseover="this.style.boxShadow='0 6px 12px rgba(0,0,0,0.1)'; this.style.transform='translateY(-2px)';"
    onmouseout="this.style.boxShadow='0 3px 6px rgba(0,0,0,0.05)'; this.style.transform='translateY(0)';"
    >
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; color: #333;">{name}</h4>
            <span style="background: {border_color}; color: white; padding: 4px 12px; 
                         border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                {performance}
            </span>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 15px;">
            <div>
                <div style="font-size: 0.9rem; color: #666;">Résistance</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #333;">
                    {resistance:.1f} MPa
                </div>
            </div>
            <div>
                <div style="font-size: 0.9rem; color: #666;">Ratio E/L</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #333;">
                    {ratio_el:.2f}
                </div>
            </div>
            <div>
                <div style="font-size: 0.9rem; color: #666;">Coût estimé</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #333;">
                    {cost:.0f} €/m³
                </div>
            </div>
        </div>
        
        <div style="color: #666; font-size: 0.9rem; border-top: 1px solid #eee; 
                    padding-top: 10px;">
            Ciment: {formulation.get('Ciment', 0):.0f} kg/m³ • 
            Eau: {formulation.get('Eau', 0):.0f} L/m³ • 
            Laitier: {formulation.get('Laitier', 0):.0f} kg/m³
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Bouton de sélection
    if on_select and st.button(
        "🔍 Voir détails",
        key=f"btn_view_{index}",
        use_container_width=True
    ):
        on_select(formulation, name)


__all__ = [
    "render_kpi_card",
    "render_info_card",
    "render_formulation_card"
]