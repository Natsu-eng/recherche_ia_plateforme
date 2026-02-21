"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/cards.py
Description: Composants de cartes réutilisables (métriques, formulations, alertes)
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
from typing import Dict, List, Optional, Callable, Any
import logging

from config.settings import UI_SETTINGS
from config.constants import STATUS_EMOJI, COLOR_PALETTE, QUALITY_THRESHOLDS
from app.core.validator import ValidationAlert, Severity

logger = logging.getLogger(__name__)


def metric_card(
    title: str,
    value: float,
    unit: str = "",
    delta: Optional[float] = None,
    icon: str = "📊",
    help_text: Optional[str] = None,
    quality_grade: Optional[str] = None,
    key: Optional[str] = None
) -> None:
    """
    Carte métrique stylisée – version corrigée pour rétrocompatibilité.
    
    Gère les deux signatures:
    - Nouvelle: metric_card(title, value, unit, delta, icon, help_text, quality_grade)
    - Ancienne: metric_card(title, value, unit, icon, quality_grade) ← COMPATIBLE
    """
    
    # Détection ordre arguments
    # Si delta est une string (emoji), les arguments sont dans l'ancien ordre
    if isinstance(delta, str):
        # Ancien ordre: title, value, unit, icon, quality_grade
        # delta contient l'icon, icon contient quality_grade
        quality_grade = icon if isinstance(icon, str) else quality_grade
        icon = delta
        delta = None  # Pas de delta dans ancien format
    
    # Détermine la couleur et emoji selon grade
    if quality_grade and quality_grade in QUALITY_THRESHOLDS:
        card_color = COLOR_PALETTE.get(QUALITY_THRESHOLDS[quality_grade]["color"], COLOR_PALETTE["primary"])
        emoji = STATUS_EMOJI.get(quality_grade, "")
    else:
        card_color = COLOR_PALETTE["primary"]
        emoji = ""

    # Formatage valeur
    value_str = f"{value:,.1f}" if abs(value) >= 1000 else f"{value:.1f}" if abs(value) >= 10 else f"{value:.2f}"

    # Delta VÉRIFICATION TYPE
    delta_html = ""
    if delta is not None and isinstance(delta, (int, float)):
        delta_color = COLOR_PALETTE["success"] if delta >= 0 else COLOR_PALETTE["danger"]
        delta_symbol = "↑" if delta >= 0 else "↓"
        delta_html = f'<span style="color:{delta_color};font-size:0.9rem;margin-left:0.5rem;">{delta_symbol} {abs(delta):.1f}</span>'

    # HTML (reste identique)
    card_html = f"""
    <div class="custom-metric-card" style="
        background: linear-gradient(135deg, {card_color}15 0%, {card_color}05 100%);
        border-left: 4px solid {card_color};
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <div style="
                    color: {UI_SETTINGS['colors']['dark']};
                    font-size: 0.9rem;
                    margin-bottom: 0.4rem;
                    opacity: 0.8;
                ">
                    {icon} {title}
                </div>
                <div style="
                    color: {card_color};
                    font-size: 2.4rem;
                    font-weight: 700;
                    line-height: 1.1;
                ">
                    {value_str}
                    <span style="font-size: 1.1rem; font-weight: 400; opacity: 0.9;">{unit}</span>
                    {delta_html}
                </div>
            </div>
            <div style="font-size: 3rem; opacity: 0.25;">
                {emoji}
            </div>
        </div>
    </div>

    <style>
        .custom-metric-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }}
    </style>
    """

    st.html(card_html)

    if help_text:
        with st.expander("Détails", expanded=False):
            st.caption(help_text)


def formulation_card(
    composition: Dict[str, float],
    predictions: Dict[str, float],
    name: str = "Formulation",
    on_select: Optional[Callable] = None,
    show_actions: bool = True
) -> None:
    """
    Carte affichant une formulation avec ses prédictions.
    
    Args:
        composition: Composition béton (kg/m³)
        predictions: Résultats prédiction
        name: Nom formulation
        on_select: Callback sélection
        show_actions: Afficher boutons d'action
    
    Example:
        ```python
        formulation_card(
            composition={'Ciment': 350, 'Eau': 175, ...},
            predictions={'Resistance': 45.2, ...},
            name="C35/45 HP"
        )
        ```
    """
    
    with st.container():
        # Header
        st.markdown(
            f"""
            <div style="
                background: {COLOR_PALETTE['primary']};
                color: white;
                padding: 0.75rem 1rem;
                border-radius: 8px 8px 0 0;
                font-weight: 600;
            ">
                🧪 {name}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Contenu
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📦 Composition**")
            
            # Constituants principaux
            key_components = ['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'Superplastifiant']
            for comp in key_components:
                value = composition.get(comp, 0)
                if value > 0:
                    st.caption(f"• {comp}: **{value:.1f}** kg/m³")
            
            # Ratio E/L
            if 'Ratio_E_L' in predictions:
                st.caption(f"• Ratio E/L: **{predictions['Ratio_E_L']:.3f}**")
        
        with col2:
            st.markdown("**🎯 Prédictions**")
            
            # Résistance
            resistance = predictions.get('Resistance', 0)
            st.caption(f"💪 Résistance: **{resistance:.1f}** MPa")
            
            # Diffusion Cl⁻
            diffusion = predictions.get('Diffusion_Cl', 0)
            st.caption(f"🧂 Diffusion Cl⁻: **{diffusion:.2f}** ×10⁻¹²")
            
            # Carbonatation
            carbonatation = predictions.get('Carbonatation', 0)
            st.caption(f"🌫️ Carbonatation: **{carbonatation:.1f}** mm")
        
        # Actions
        if show_actions:
            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("📊 Analyser", key=f"analyze_{name}", width="stretch"):
                    if on_select:
                        on_select(composition, predictions)
            
            with col_b:
                if st.button("⭐ Favori", key=f"fav_{name}", width="stretch"):
                    st.toast(f"✅ {name} ajouté aux favoris", icon="⭐")
            
            with col_c:
                if st.button("📥 Export", key=f"export_{name}", width="stretch"):
                    st.toast("📥 Export en cours...", icon="⏳")


def alert_banner(
    alerts: List[ValidationAlert],
    max_display: int = 5
) -> None:
    """
    Affiche les alertes de validation avec couleurs par sévérité.
    
    Args:
        alerts: Liste ValidationAlert
        max_display: Nombre max d'alertes affichées
    
    Example:
        ```python
        alerts = [
            ValidationAlert(
                severity=Severity.WARNING,
                category="Ratio E/L",
                message="Ratio élevé",
                recommendation="Réduire eau"
            )
        ]
        alert_banner(alerts)
        ```
    """
    
    if not alerts:
        st.success("✅ Aucune alerte - Formulation conforme", icon="✅")
        return
    
    # Trier par sévérité (CRITICAL > ERROR > WARNING > INFO)
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.ERROR: 1,
        Severity.WARNING: 2,
        Severity.INFO: 3
    }
    sorted_alerts = sorted(alerts, key=lambda a: severity_order.get(a.severity, 4))
    
    # Limiter affichage
    display_alerts = sorted_alerts[:max_display]
    hidden_count = len(alerts) - max_display
    
    st.markdown(f"### 🚨 Alertes de Validation ({len(alerts)})")
    
    for alert in display_alerts:
        # Déterminer style selon sévérité
        if alert.severity == Severity.CRITICAL:
            alert_type = "error"
            icon = "🔴"
            border_color = COLOR_PALETTE["danger"]
        elif alert.severity == Severity.ERROR:
            alert_type = "error"
            icon = "❌"
            border_color = COLOR_PALETTE["danger"]
        elif alert.severity == Severity.WARNING:
            alert_type = "warning"
            icon = "⚠️"
            border_color = COLOR_PALETTE["warning"]
        else:  # INFO
            alert_type = "info"
            icon = "ℹ️"
            border_color = COLOR_PALETTE["info"]
        
        # Créer message structuré
        message_parts = [
            f"**{icon} {alert.category}**",
            f"\n\n{alert.message}",
            f"\n\n💡 **Recommandation** : {alert.recommendation}"
        ]
        
        if alert.norm_ref:
            message_parts.append(f"\n\n📖 *Norme : {alert.norm_ref}*")
        
        full_message = "".join(message_parts)
        
        # Afficher
        if alert_type == "error":
            st.error(full_message, icon=icon)
        elif alert_type == "warning":
            st.warning(full_message, icon=icon)
        else:
            st.info(full_message, icon=icon)
    
    # Alertes masquées
    if hidden_count > 0:
        with st.expander(f"➕ Afficher {hidden_count} alerte(s) supplémentaire(s)"):
            for alert in sorted_alerts[max_display:]:
                st.caption(f"{STATUS_EMOJI.get(alert.severity.value, '')} **{alert.category}** : {alert.message}")


from markdown import markdown
from markdown.extensions.extra import ExtraExtension

def info_box(title: str, content: str, icon: str = "ℹ️", color: str = "primary") -> None:
    color_value = COLOR_PALETTE.get(color, COLOR_PALETTE["primary"])
    
    # Nettoyage du content : s'assurer que c'est une string pure
    if not isinstance(content, str):
        content = str(content)  # évite [object Object]
    
    # Conversion markdown → HTML
    html_content = markdown(
        content.strip(),  # retire espaces inutiles
        extensions=['extra', 'sane_lists', 'nl2br'],  # nl2br pour sauts de ligne
        output_format='html5'
    )
    
    # Injection via st.html (plus stable que st.markdown pour du HTML pur)
    st.markdown(f"""
    <div style="
        background: {color_value}15;
        border-left: 4px solid {color_value};
        border-radius: 8px;
        padding: 1.2rem;
        margin: 1rem 0;
        line-height: 1.6;
    ">
        <div style="display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.8rem;">
            <span style="font-size: 1.6rem;">{icon}</span>
            <h4 style="margin: 0; color: {color_value}; font-weight: 600;">{title}</h4>
        </div>
        <div style="color: {UI_SETTINGS['colors']['dark']};">
            {html_content}
        </div>
    </div>
    """, unsafe_allow_html=True)


__all__ = [
    'metric_card',
    'formulation_card',
    'alert_banner',
    'info_box'
]