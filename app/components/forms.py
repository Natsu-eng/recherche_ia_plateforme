"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/forms.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Composants de formulaire stylisés
Version: 2.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st  # type: ignore
from typing import Dict, List, Optional, Callable, Any


def create_slider_with_help(
    label: str,
    min_value: float,
    max_value: float,
    value: float,
    step: float = 1.0,
    unit: str = "",
    help_text: str = "",
    key: Optional[str] = None
) -> float:
    """
    Slider avec aide contextuelle et indicateurs.
    
    Args:
        label: Label du slider
        min_value: Valeur minimale
        max_value: Valeur maximale
        value: Valeur initiale
        step: Incrément
        unit: Unité de mesure
        help_text: Texte d'aide
        key: Clé unique Streamlit
    
    Returns:
        Valeur sélectionnée
    """
    # Container avec style
    with st.container():
        # Header slider
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{label}**")
            if help_text:
                st.caption(f"ℹ️ {help_text}")
        
        with col2:
            st.markdown(f"`{value:,.1f} {unit}`")
        
        # Slider Streamlit
        val = st.slider(
            label="",  # Label déjà affiché
            min_value=min_value,
            max_value=max_value,
            value=value,
            step=step,
            key=key or label
        )
        
        # Indicateur de plage
        col3, col4, col5 = st.columns([1, 4, 1])
        with col3:
            st.caption(f"{min_value:,.0f}")
        with col4:
            # Barre de progression
            progress = (val - min_value) / (max_value - min_value)
            st.progress(progress)
        with col5:
            st.caption(f"{max_value:,.0f}")
        
        return val


def create_formulation_form(
    default_values: Dict[str, float],
    bounds: Dict[str, Dict[str, Any]],
    key_prefix: str = ""
) -> Dict[str, float]:
    """
    Formulaire complet pour saisir une formulation béton.
    
    Args:
        default_values: Valeurs par défaut
        bounds: Bornes des paramètres
        key_prefix: Préfixe pour clés Streamlit
    
    Returns:
        Dictionnaire avec valeurs saisies
    """
    formulation = {}
    
    st.markdown("### 🧪 Composition Béton")
    
    # 1. LIANTS HYDRAULIQUES
    with st.expander("📦 Liants Hydrauliques", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            formulation["Ciment"] = create_slider_with_help(
                label="Ciment CEM I/II",
                min_value=bounds["Ciment"]["min"],
                max_value=bounds["Ciment"]["max"],
                value=default_values.get("Ciment", bounds["Ciment"]["default"]),
                step=bounds["Ciment"]["step"],
                unit="kg/m³",
                help_text=bounds["Ciment"]["description"],
                key=f"{key_prefix}_ciment"
            )
        
        with col2:
            formulation["Laitier"] = create_slider_with_help(
                label="Laitier de Haut-Fourneau",
                min_value=bounds["Laitier"]["min"],
                max_value=bounds["Laitier"]["max"],
                value=default_values.get("Laitier", bounds["Laitier"]["default"]),
                step=bounds["Laitier"]["step"],
                unit="kg/m³",
                help_text=bounds["Laitier"]["description"],
                key=f"{key_prefix}_laitier"
            )
        
        with col3:
            formulation["CendresVolantes"] = create_slider_with_help(
                label="Cendres Volantes",
                min_value=bounds["CendresVolantes"]["min"],
                max_value=bounds["CendresVolantes"]["max"],
                value=default_values.get("CendresVolantes", bounds["CendresVolantes"]["default"]),
                step=bounds["CendresVolantes"]["step"],
                unit="kg/m³",
                help_text=bounds["CendresVolantes"]["description"],
                key=f"{key_prefix}_cendres"
            )
    
    # 2. EAU & ADJUVANTS
    with st.expander("💧 Eau & Adjuvants", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            formulation["Eau"] = create_slider_with_help(
                label="Eau de Gâchage",
                min_value=bounds["Eau"]["min"],
                max_value=bounds["Eau"]["max"],
                value=default_values.get("Eau", bounds["Eau"]["default"]),
                step=bounds["Eau"]["step"],
                unit="L/m³",
                help_text=bounds["Eau"]["description"],
                key=f"{key_prefix}_eau"
            )
        
        with col2:
            formulation["Superplastifiant"] = create_slider_with_help(
                label="Superplastifiant",
                min_value=bounds["Superplastifiant"]["min"],
                max_value=bounds["Superplastifiant"]["max"],
                value=default_values.get("Superplastifiant", bounds["Superplastifiant"]["default"]),
                step=bounds["Superplastifiant"]["step"],
                unit="kg/m³",
                help_text=bounds["Superplastifiant"]["description"],
                key=f"{key_prefix}_sp"
            )
    
    # 3. GRANULATS
    with st.expander("🪨 Granulats", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            formulation["GravilonsGros"] = create_slider_with_help(
                label="Gravillons 4/20",
                min_value=bounds["GravilonsGros"]["min"],
                max_value=bounds["GravilonsGros"]["max"],
                value=default_values.get("GravilonsGros", bounds["GravilonsGros"]["default"]),
                step=bounds["GravilonsGros"]["step"],
                unit="kg/m³",
                help_text=bounds["GravilonsGros"]["description"],
                key=f"{key_prefix}_gravi"
            )
        
        with col2:
            formulation["SableFin"] = create_slider_with_help(
                label="Sable 0/4",
                min_value=bounds["SableFin"]["min"],
                max_value=bounds["SableFin"]["max"],
                value=default_values.get("SableFin", bounds["SableFin"]["default"]),
                step=bounds["SableFin"]["step"],
                unit="kg/m³",
                help_text=bounds["SableFin"]["description"],
                key=f"{key_prefix}_sable"
            )
    
    # 4. TEMPS
    with st.expander("⏰ Paramètres Temporels"):
        formulation["Age"] = create_slider_with_help(
            label="Âge du Béton",
            min_value=bounds["Age"]["min"],
            max_value=bounds["Age"]["max"],
            value=default_values.get("Age", bounds["Age"]["default"]),
            step=bounds["Age"]["step"],
            unit="jours",
            help_text=bounds["Age"]["description"],
            key=f"{key_prefix}_age"
        )
    
    return formulation


def create_preset_selector(
    presets: Dict[str, Dict[str, float]],
    on_select: Optional[Callable[[Dict[str, float], str], None]] = None
) -> Optional[Dict[str, float]]:
    """
    Sélecteur de formulations prédéfinies.
    
    Args:
        presets: Dictionnaire {nom: formulation}
        on_select: Callback sur sélection
    
    Returns:
        Formulation sélectionnée ou None
    """
    st.markdown("### 📋 Formulations Prédéfinies")
    
    selected_preset = st.selectbox(
        "Choisissez une formulation type :",
        options=list(presets.keys()),
        format_func=lambda x: f"{x} ({presets[x].get('classe', '')})"
    )
    
    if selected_preset:
        preset = presets[selected_preset]
        
        # Affichage info
        with st.container():
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                <h4>ℹ️ {selected_preset}</h4>
                <p>{preset.get('description', '')}</p>
                <div style="color: #666; font-size: 0.9rem;">
                    <strong>Classe:</strong> {preset.get('classe', 'N/A')} • 
                    <strong>Exposition:</strong> {preset.get('exposition', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Bouton appliquer
        if st.button("✅ Appliquer cette formulation", use_container_width=True):
            if on_select:
                on_select(preset, selected_preset)
            return preset
    
    return None


def create_validation_form(
    formulation: Dict[str, float],
    on_validate: Callable[[Dict[str, float]], None]
) -> None:
    """
    Formulaire de validation avec recommandations.
    
    Args:
        formulation: Formulation à valider
        on_validate: Callback validation
    """
    st.markdown("### 🧪 Validation")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            # Informations
            liant_total = (
                formulation.get("Ciment", 0) + 
                formulation.get("Laitier", 0) + 
                formulation.get("CendresVolantes", 0)
            )
            
            eau = formulation.get("Eau", 0)
            ratio_el = eau / (liant_total + 1e-5)
            
            st.metric("Liant Total", f"{liant_total:.0f} kg/m³")
            st.metric("Ratio E/L", f"{ratio_el:.3f}")
        
        with col2:
            # Validation rapide
            if ratio_el > 0.65:
                st.error("⚠️ Ratio E/L > 0.65 - Non conforme EN 206 béton armé")
            elif ratio_el > 0.60:
                st.warning("⚠️ Ratio E/L élevé (0.60-0.65)")
            elif ratio_el < 0.40:
                st.success("✅ Ratio E/L excellent (< 0.40)")
            else:
                st.info("ℹ️ Ratio E/L acceptable")
        
        # Boutons d'action
        col3, col4, col5 = st.columns([1, 1, 1])
        
        with col3:
            if st.button("📊 Voir détails", use_container_width=True):
                st.session_state["show_details"] = True
        
        with col4:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                for key in formulation.keys():
                    formulation[key] = 0
        
        with col5:
            if st.button("✅ Valider & Prédire", type="primary", use_container_width=True):
                on_validate(formulation)


__all__ = [
    "create_slider_with_help",
    "create_formulation_form",
    "create_preset_selector",
    "create_validation_form"
]