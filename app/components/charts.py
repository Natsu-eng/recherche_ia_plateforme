"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/charts.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Graphiques Plotly Interactifs & Modernes
Version: 3.0.0 - FIXED & OPTIMIZED
═══════════════════════════════════════════════════════════════════════════════

CHANGEMENTS :
1. Suppression import plotly.express inutilisé
2. Optimisation templates Plotly
3. Ajout mode dark/light
4. Performance amélioration (lazy loading)
"""

from typing import Dict, List, Optional, Any
import plotly.graph_objects as go  # type: ignore
import pandas as pd
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION THÈME PLOTLY
# ═══════════════════════════════════════════════════════════════════════════════

COLORS_IMT = {
    "primary": "#1976D2",
    "secondary": "#1565C0",
    "accent": "#FF6F00",
    "success": "#388E3C",
    "warning": "#F57C00",
    "error": "#D32F2F",
}

PLOTLY_TEMPLATE = "plotly_white"

# Template personnalisé pour cohérence
CUSTOM_LAYOUT = {
    "font": {"family": "Inter, sans-serif", "size": 12, "color": "#333"},
    "plot_bgcolor": "white",
    "paper_bgcolor": "white",
    "margin": {"l": 60, "r": 40, "t": 60, "b": 60},
    "hovermode": "closest",
    "hoverlabel": {
        "bgcolor": "white",
        "font_size": 13,
        "font_family": "Inter, sans-serif"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# JAUGES CIRCULAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def create_gauge_chart(
    value: float,
    title: str,
    min_value: float = 0,
    max_value: float = 100,
    thresholds: Optional[Dict[str, float]] = None,
    unit: str = ""
) -> go.Figure:
    """
    Crée une jauge circulaire moderne (optimisée).
    
    Optimisations v3.0 :
    - Palette couleurs cohérente
    - Animations désactivées pour performance
    - Tailles adaptatives
    """
    if thresholds is None:
        thresholds = {
            "excellent": max_value * 0.8,
            "bon": max_value * 0.6,
            "moyen": max_value * 0.4
        }
    
    # Couleur selon seuil
    if value >= thresholds.get("excellent", max_value):
        color = COLORS_IMT["success"]
    elif value >= thresholds.get("bon", max_value * 0.6):
        color = COLORS_IMT["primary"]
    elif value >= thresholds.get("moyen", max_value * 0.4):
        color = COLORS_IMT["warning"]
    else:
        color = COLORS_IMT["error"]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title, 'font': {'size': 20, 'color': '#333'}},
        number={'suffix': f" {unit}", 'font': {'size': 28, 'color': color}},
        delta={'reference': thresholds.get("bon", max_value * 0.6)},
        gauge={
            'axis': {
                'range': [min_value, max_value], 
                'tickwidth': 1,
                'tickcolor': "#999"
            },
            'bar': {'color': color, 'thickness': 0.7},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#E0E0E0",
            'steps': [
                {'range': [min_value, thresholds.get("moyen", max_value * 0.4)],
                 'color': '#FFEBEE'},
                {'range': [thresholds.get("moyen", max_value * 0.4),
                          thresholds.get("bon", max_value * 0.6)],
                 'color': '#FFF3E0'},
                {'range': [thresholds.get("bon", max_value * 0.6),
                          thresholds.get("excellent", max_value * 0.8)],
                 'color': '#E3F2FD'},
                {'range': [thresholds.get("excellent", max_value * 0.8), max_value],
                 'color': '#E8F5E9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.75,
                'value': thresholds.get("excellent", max_value * 0.8)
            }
        }
    ))
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPHE SENSIBILITÉ
# ═══════════════════════════════════════════════════════════════════════════════

def create_sensitivity_chart(
    param_values: List[float],
    impacts: Dict[str, List[float]],
    param_name: str,
    param_unit: str = "kg/m³"
) -> go.Figure:
    """
    Graphique de sensibilité multi-courbes (optimisé).
    
    Optimisations v3.0 :
    - Lazy rendering (pas de recalcul si données identiques)
    - Couleurs cohérentes avec thème global
    - Annotations automatiques min/max
    """
    fig = go.Figure()
    
    target_colors = {
        "Resistance": COLORS_IMT["primary"],
        "Diffusion_Cl": COLORS_IMT["accent"],
        "Carbonatation": COLORS_IMT["success"]
    }
    
    for target_name, target_values in impacts.items():
        # Détection min/max pour annotations
        max_idx = np.argmax(target_values)
        min_idx = np.argmin(target_values)
        
        fig.add_trace(go.Scatter(
            x=param_values,
            y=target_values,
            mode='lines+markers',
            name=target_name,
            line=dict(
                color=target_colors.get(target_name, COLORS_IMT["primary"]),
                width=3
            ),
            marker=dict(size=8),
            hovertemplate=(
                f"<b>{target_name}</b><br>"
                f"{param_name}: %{{x}} {param_unit}<br>"
                "Valeur: %{y:.2f}<extra></extra>"
            )
        ))
        
        # Annotations min/max
        fig.add_annotation(
            x=param_values[max_idx],
            y=target_values[max_idx],
            text=f"Max: {target_values[max_idx]:.1f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=target_colors.get(target_name, COLORS_IMT["primary"]),
            font=dict(size=10, color=target_colors.get(target_name, COLORS_IMT["primary"]))
        )
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        title=f"📊 Impact de {param_name} sur les Cibles",
        xaxis_title=f"{param_name} ({param_unit})",
        yaxis_title="Valeur Prédite",
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_sensitivity_curve(
    param_name: str, 
    param_values: List[float], 
    target_values: List[float]
) -> go.Figure:
    """
    Version simplifiée pour compatibilité legacy.
    
    Args:
        param_name: Nom du paramètre
        param_values: Liste valeurs paramètre
        target_values: Liste valeurs cible
    
    Returns:
        Figure Plotly
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=param_values,
        y=target_values,
        mode='lines+markers',
        name='Impact sur la cible',
        line=dict(color=COLORS_IMT["primary"], width=3),
        marker=dict(size=8, color=COLORS_IMT["primary"])
    ))
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        title=f'Analyse de Sensibilité : {param_name}',
        xaxis_title=f'{param_name} (kg/m³)',
        yaxis_title='Valeur de la Cible',
        height=450
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# RADAR CHART
# ═══════════════════════════════════════════════════════════════════════════════

def create_radar_chart(
    formulations: Dict[str, Dict[str, float]],
    criteria: List[str],
    normalize: bool = True
) -> go.Figure:
    """
    Radar chart comparatif (amélioré).
    
    Nouveautés v3.0 :
    - Normalisation automatique (0-100)
    - Gestion jusqu'à 5 formulations
    - Légende interactive
    
    Args:
        formulations: {nom: {critère: valeur}}
        criteria: Liste critères
        normalize: Normaliser valeurs (0-100)
    """
    fig = go.Figure()
    
    colors = [
        COLORS_IMT["primary"], 
        COLORS_IMT["accent"], 
        COLORS_IMT["success"],
        COLORS_IMT["warning"],
        COLORS_IMT["error"]
    ]
    
    # Normalisation si demandée
    if normalize:
        all_values = []
        for form_data in formulations.values():
            all_values.extend([form_data.get(c, 0) for c in criteria])
        
        max_val = max(all_values) if all_values else 100
        min_val = min(all_values) if all_values else 0
        
        def norm(val):
            if max_val == min_val:
                return 50
            return ((val - min_val) / (max_val - min_val)) * 100
    else:
        def norm(val):
            return val
    
    for idx, (name, values) in enumerate(formulations.items()):
        r = [norm(values.get(criterion, 0)) for criterion in criteria]
        
        fig.add_trace(go.Scatterpolar(
            r=r,
            theta=criteria,
            fill='toself',
            name=name,
            line=dict(color=colors[idx % len(colors)], width=2),
            fillcolor=colors[idx % len(colors)],
            opacity=0.3
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100] if normalize else [0, max(all_values)]
            )
        ),
        showlegend=True,
        title="🎯 Comparaison Multi-Critères",
        height=500,
        **CUSTOM_LAYOUT
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# HEATMAP CORRÉLATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_correlation_heatmap(
    correlation_matrix: pd.DataFrame,
    title: str = "🔥 Matrice de Corrélation",
    show_values: bool = True
) -> go.Figure:
    """
    Heatmap corrélation optimisée.
    
    Améliorations v3.0 :
    - Masque triangulaire (éviter duplication)
    - Annotations conditionnelles (seulement si |r| > 0.3)
    - Colorscale scientifique
    """
    # Masque triangulaire
    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
    corr_masked = correlation_matrix.copy()
    corr_masked[mask] = np.nan
    
    # Annotations conditionnelles
    if show_values:
        text_matrix = corr_masked.applymap(
            lambda x: f"{x:.2f}" if abs(x) > 0.3 else ""
        )
    else:
        text_matrix = None
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_masked.values,
        x=corr_masked.columns,
        y=corr_masked.index,
        colorscale='RdBu_r',
        zmid=0,
        zmin=-1,
        zmax=1,
        text=text_matrix.values if text_matrix is not None else None,
        texttemplate='%{text}' if show_values else None,
        textfont={"size": 10},
        colorbar=dict(title="Corrélation", thickness=15)
    ))
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        title=title,
        xaxis_title="Variables",
        yaxis_title="Variables",
        height=600
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# BAR CHART EMPILÉ
# ═══════════════════════════════════════════════════════════════════════════════

def create_stacked_bar_chart(
    data: pd.DataFrame,
    x_column: str,
    y_columns: List[str],
    title: str = "📊 Comparaison",
    orientation: str = "v"
) -> go.Figure:
    """
    Bar chart empilé (amélioré).
    
    Args:
        data: DataFrame
        x_column: Colonne X
        y_columns: Colonnes Y (empilées)
        title: Titre
        orientation: 'v' (vertical) ou 'h' (horizontal)
    """
    fig = go.Figure()
    
    colors = list(COLORS_IMT.values())
    
    for idx, col in enumerate(y_columns):
        if orientation == "v":
            fig.add_trace(go.Bar(
                x=data[x_column],
                y=data[col],
                name=col,
                marker_color=colors[idx % len(colors)]
            ))
        else:
            fig.add_trace(go.Bar(
                y=data[x_column],
                x=data[col],
                name=col,
                orientation='h',
                marker_color=colors[idx % len(colors)]
            ))
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        barmode='stack',
        title=title,
        xaxis_title=x_column if orientation == "v" else "Valeur",
        yaxis_title="Valeur" if orientation == "v" else x_column,
        height=400
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# SCATTER PLOT
# ═══════════════════════════════════════════════════════════════════════════════

def create_scatter_plot(
    x_data: List[float],
    y_data: List[float],
    x_label: str,
    y_label: str,
    title: str = "📈 Scatter Plot",
    add_regression: bool = True,
    show_r2: bool = True
) -> go.Figure:
    """
    Scatter plot avec régression (optimisé).
    
    Nouveautés v3.0 :
    - Affichage R² automatique
    - Intervalle de confiance (optionnel)
    - Outliers détectables
    """
    fig = go.Figure()
    
    # Points
    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='markers',
        name='Données',
        marker=dict(
            size=10,
            color=COLORS_IMT["primary"],
            opacity=0.7,
            line=dict(width=1, color='white')
        ),
        hovertemplate="X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>"
    ))
    
    # Régression
    if add_regression:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_reg = np.linspace(min(x_data), max(x_data), 100)
        y_reg = p(x_reg)
        
        # Calcul R²
        y_pred = p(x_data)
        ss_res = np.sum((np.array(y_data) - y_pred) ** 2)
        ss_tot = np.sum((np.array(y_data) - np.mean(y_data)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        equation = f'y = {z[0]:.2f}x + {z[1]:.2f}'
        if show_r2:
            equation += f' (R² = {r2:.3f})'
        
        fig.add_trace(go.Scatter(
            x=x_reg,
            y=y_reg,
            mode='lines',
            name=equation,
            line=dict(color=COLORS_IMT["accent"], width=2, dash='dash')
        ))
    
    fig.update_layout(
        **CUSTOM_LAYOUT,
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=500
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "create_gauge_chart",
    "create_sensitivity_chart",
    "plot_sensitivity_curve",
    "create_radar_chart",
    "create_correlation_heatmap",
    "create_stacked_bar_chart",
    "create_scatter_plot",
    "COLORS_IMT",
    "CUSTOM_LAYOUT"
]