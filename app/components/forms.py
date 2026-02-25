"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/forms.py
Description: Formulaires de saisie (composition béton, objectifs optimisation)
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
from typing import Dict, Optional, Literal
import logging

from config.constants import BOUNDS, LABELS_MAP, PRESET_FORMULATIONS
from config.settings import OPTIMIZER_SETTINGS

logger = logging.getLogger(__name__)


def render_formulation_input(
    key_suffix: str = "",
    default_values: Optional[Dict[str, float]] = None,
    layout: Literal["compact", "expanded"] = "compact",
    show_presets: bool = True
) -> Dict[str, float]:
    """
    Génère les sliders pour saisir une composition béton.
    
    Args:
        key_suffix: Suffixe pour clés Streamlit (éviter conflits)
        default_values: Valeurs par défaut (sinon utilise BOUNDS['default'])
        layout: Layout (compact = 2 colonnes, expanded = 1 colonne)
        show_presets: Afficher sélecteur formulations prédéfinies
    
    Returns:
        Dict avec composition (kg/m³)
    
    Example:
        ```python
        composition = render_formulation_input(key_suffix="page1")
        # {'Ciment': 350.0, 'Eau': 175.0, ...}
        ```
    """
    
    composition = {}
    
    # ═══════════════════════════════════════════════════════════════
    # SÉLECTEUR FORMULATIONS PRÉDÉFINIES
    # ═══════════════════════════════════════════════════════════════
    
    if show_presets:
        st.markdown("#### 📚 Formulations Prédéfinies")
        
        preset_options = ["Personnalisée"] + list(PRESET_FORMULATIONS.keys())
        
        selected_preset = st.selectbox(
            label="Charger une formulation type",
            options=preset_options,
            index=0,
            key=f"preset_selector_{key_suffix}",
            help="Sélectionner une formulation standard comme point de départ"
        )
        
        # Si formulation prédéfinie sélectionnée, l'utiliser comme défaut
        if selected_preset != "Personnalisée":
            preset_data = PRESET_FORMULATIONS[selected_preset]
            
            # Mettre à jour les sliders via session_state
            for param, value in preset_data.items():
                if param in BOUNDS:
                    slider_key = f"{param}_slider_{key_suffix}"
                    if slider_key in st.session_state:
                        st.session_state[slider_key] = float(value)
            
            # Afficher description
            st.info(
                f"ℹ️ **{selected_preset}** : {preset_data.get('description', '')}  \n"
                f"*Classe : {preset_data.get('classe', 'N/A')} | "
                f"Exposition : {preset_data.get('exposition', 'N/A')}*"
            )
        
        st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # SLIDERS COMPOSITION
    # ═══════════════════════════════════════════════════════════════
    
    st.markdown("#### ⚗️ Composition du Mélange")
    
    # Déterminer layout
    if layout == "compact":
        col1, col2 = st.columns(2)
        columns = [col1, col2]
    else:
        columns = [st.container()]
    
    # Regroupement constituants
    groups = {
        "Liants": ['Ciment', 'Laitier', 'CendresVolantes', 'Metakaolin'],
        "Eau & Adjuvants": ['Eau', 'Superplastifiant'],
        "Granulats": ['GravilonsGros', 'SableFin'],
        "Maturation": ['Age']
    }
    
    current_col = 0
    
    for group_name, params in groups.items():
        with columns[current_col % len(columns)]:
            st.markdown(f"**{group_name}**")
            
            for param in params:
                if param not in BOUNDS:
                    continue
                
                bounds = BOUNDS[param]
                
                # Valeur par défaut
                if default_values and param in default_values:
                    default_val = default_values[param]
                else:
                    default_val = bounds.get('default', bounds['min'])
                
                # Slider
                value = st.slider(
                    label=f"{LABELS_MAP.get(param, param)}",
                    min_value=float(bounds['min']),
                    max_value=float(bounds['max']),
                    step=float(bounds.get('step', 1.0)),
                    key=f"{param}_slider_{key_suffix}",
                    help=f"{bounds.get('description', '')} ({bounds.get('unit', '')})"
                )
                
                composition[param] = value
        
        # Alterner colonnes en mode compact
        if layout == "compact":
            current_col += 1
    
    # ═══════════════════════════════════════════════════════════════
    # RÉSUMÉ RAPIDE
    # ═══════════════════════════════════════════════════════════════
    
    with st.expander("📊 Résumé de la Formulation", expanded=False):
        # Calculs rapides
        liant_total = (
            composition.get('Ciment', 0) +
            composition.get('Laitier', 0) +
            composition.get('CendresVolantes', 0)
        )
        ratio_el = composition.get('Eau', 0) / (liant_total + 1e-5) if liant_total > 0 else 0
        
        taux_sub = 0
        if liant_total > 0:
            taux_sub = (
                (composition.get('Laitier', 0) + composition.get('CendresVolantes', 0)) /
                liant_total * 100
            )
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            st.metric("Liant Total", f"{liant_total:.1f} kg/m³")
        
        with col_r2:
            # Couleur selon seuil
            color = "🟢" if ratio_el <= 0.50 else ("🟡" if ratio_el <= 0.60 else "🔴")
            st.metric("Ratio E/L", f"{color} {ratio_el:.3f}")
        
        with col_r3:
            st.metric("Substitution", f"{taux_sub:.1f}%")
    
    return composition


def render_target_selector(
    key_suffix: str = "",
    show_description: bool = True
) -> str:
    """
    Sélecteur d'objectif pour optimisation.
    
    Args:
        key_suffix: Suffixe clé Streamlit
        show_description: Afficher description objectif
    
    Returns:
        Nom objectif sélectionné (ex: "minimize_cost")
    
    Example:
        ```python
        objective = render_target_selector()
        # "minimize_cost"
        ```
    """
    
    st.markdown("#### 🎯 Objectif d'Optimisation")
    
    # Mapping objectifs → Labels FR
    objectives_map = {
        "minimize_cost": {
            "label": "💰 Minimiser le Coût",
            "description": "Trouve la formulation la moins chère atteignant la résistance cible.",
            "icon": "💰"
        },
        "minimize_co2": {
            "label": "🌱 Minimiser l'Empreinte Carbone",
            "description": "Optimise pour réduire les émissions de CO₂ tout en respectant la performance.",
            "icon": "🌱"
        },
        "maximize_resistance": {
            "label": "💪 Maximiser la Résistance",
            "description": "Maximise la résistance en compression dans les contraintes de coût/matériaux.",
            "icon": "💪"
        },
        "minimize_diffusion_cl": {
            "label": "🧂 Minimiser Diffusion Chlorures",
            "description": "Optimise la durabilité face à la corrosion (milieux marins, sels).",
            "icon": "🧂"
        },
        "minimize_carbonatation": {
            "label": "🌫️ Minimiser Carbonatation",
            "description": "Améliore la durabilité face au vieillissement CO₂.",
            "icon": "🌫️"
        }
    }
    
    # Sélecteur
    objective_keys = list(objectives_map.keys())
    objective_labels = [objectives_map[k]["label"] for k in objective_keys]
    
    selected_label = st.radio(
        label="Choisir l'objectif principal",
        options=objective_labels,
        index=0,
        key=f"objective_selector_{key_suffix}",
        horizontal=False
    )
    
    # Retrouver clé correspondante
    selected_key = objective_keys[objective_labels.index(selected_label)]
    
    # Afficher description
    if show_description:
        objective_info = objectives_map[selected_key]
        st.info(
            f"{objective_info['icon']} **{objective_info['label']}**  \n"
            f"{objective_info['description']}"
        )
    
    return selected_key


def render_constraints_input(
    key_suffix: str = ""
) -> Dict[str, float]:
    """
    Saisie des contraintes pour optimisation.
    
    Args:
        key_suffix: Suffixe clé
    
    Returns:
        Dict avec contraintes
    
    Example:
        ```python
        constraints = render_constraints_input()
        # {'target_resistance': 35.0, 'max_cost': 50.0, 'max_co2': 350.0}
        ```
    """
    
    st.markdown("#### ⚙️ Contraintes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_resistance = st.number_input(
            label="Résistance Minimale (MPa)",
            min_value=10.0,
            max_value=90.0,
            value=30.0,
            step=5.0,
            key=f"target_resistance_{key_suffix}",
            help="Résistance minimale requise à 28 jours"
        )
        
        max_cost = st.number_input(
            label="Coût Maximal (€/m³)",
            min_value=20.0,
            max_value=200.0,
            value=100.0,
            step=10.0,
            key=f"max_cost_{key_suffix}",
            help="Budget maximal pour les matériaux"
        )
    
    with col2:
        max_co2 = st.number_input(
            label="CO₂ Maximal (kg/m³)",
            min_value=100.0,
            max_value=600.0,
            value=350.0,
            step=50.0,
            key=f"max_co2_{key_suffix}",
            help="Empreinte carbone maximale tolérée"
        )
        
        max_el_ratio = st.number_input(
            label="Ratio E/L Maximal",
            min_value=0.30,
            max_value=0.70,
            value=0.55,
            step=0.05,
            key=f"max_el_{key_suffix}",
            help="Ratio Eau/Liant maximal (durabilité)"
        )
    
    return {
        'target_resistance': target_resistance,
        'max_cost': max_cost,
        'max_co2': max_co2,
        'max_el_ratio': max_el_ratio
    }


__all__ = [
    'render_formulation_input',
    'render_target_selector',
    'render_constraints_input'
]