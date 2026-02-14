"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/charts.py
Description: Visualisations interactives (Plotly)
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from config.settings import UI_SETTINGS
from config.constants import COLOR_PALETTE, LABELS_MAP
from app.core.analyzer import SensitivityResult

logger = logging.getLogger(__name__)


def plot_composition_pie(
    composition: Dict[str, float],
    title: str = "Composition du Béton"
) -> go.Figure:
    """
    Camembert de la composition.
    
    Args:
        composition: Dict composition (kg/m³)
        title: Titre graphique
    
    Returns:
        Figure Plotly
    """
    
    # Filtrer constituants significatifs (> 0)
    data = {
        LABELS_MAP.get(k, k): v
        for k, v in composition.items()
        if v > 0 and k in ['Ciment', 'Laitier', 'CendresVolantes', 'Eau',
                           'Superplastifiant', 'GravilonsGros', 'SableFin']
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=0.4,
        marker=dict(
            colors=px.colors.qualitative.Set3,
            line=dict(color='white', width=2)
        ),
        textinfo='label+percent',
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{value:.1f} kg/m³<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLOR_PALETTE['primary'])),
        showlegend=True,
        height=400,
        margin=dict(t=50, b=30, l=30, r=30)
    )
    
    return fig


def plot_parallel_coordinates(
    formulations_df: pd.DataFrame,
    color_by: str = "Resistance"
) -> go.Figure:
    """
    Coordonnées parallèles pour comparer formulations.
    
    Args:
        formulations_df: DataFrame avec formulations
        color_by: Colonne pour coloration
    
    Returns:
        Figure Plotly
    """
    
    # Sélectionner colonnes pertinentes
    key_cols = [
        'Ciment', 'Eau', 'Laitier', 'CendresVolantes',
        'Ratio_E_L', 'Resistance', 'Diffusion_Cl', 'Carbonatation'
    ]
    
    available_cols = [c for c in key_cols if c in formulations_df.columns]
    df_plot = formulations_df[available_cols].copy()
    
    # Normaliser pour affichage
    dimensions = []
    for col in df_plot.columns:
        dimensions.append(dict(
            label=LABELS_MAP.get(col, col),
            values=df_plot[col],
            range=[df_plot[col].min(), df_plot[col].max()]
        ))
    
    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=df_plot[color_by] if color_by in df_plot.columns else df_plot.iloc[:, 0],
            colorscale='Viridis',
            showscale=True,
            cmin=df_plot[color_by].min() if color_by in df_plot.columns else 0,
            cmax=df_plot[color_by].max() if color_by in df_plot.columns else 100
        ),
        dimensions=dimensions
    ))
    
    fig.update_layout(
        title="Comparaison Multi-Paramètres",
        height=500,
        margin=dict(t=50, b=30, l=100, r=100)
    )
    
    return fig


def plot_sensitivity(
    sensitivity_result: SensitivityResult,
    targets: Optional[List[str]] = None
) -> go.Figure:
    """
    Graphique d'analyse de sensibilité.
    
    Args:
        sensitivity_result: Résultat SensitivityResult
        targets: Cibles à afficher (None = toutes)
    
    Returns:
        Figure Plotly
    """
    
    if targets is None:
        targets = list(sensitivity_result.impacts.keys())
    
    # Créer plage de valeurs du paramètre
    min_val, max_val = sensitivity_result.variation_range
    n_points = len(sensitivity_result.impacts[targets[0]])
    param_values = np.linspace(min_val, max_val, n_points)
    
    fig = make_subplots(
        rows=len(targets),
        cols=1,
        subplot_titles=[f"Impact sur {LABELS_MAP.get(t, t)}" for t in targets],
        vertical_spacing=0.12
    )
    
    colors = [COLOR_PALETTE['primary'], COLOR_PALETTE['success'], COLOR_PALETTE['warning']]
    
    for i, target in enumerate(targets, start=1):
        values = sensitivity_result.impacts[target]
        elasticity = sensitivity_result.elasticities.get(target, 0)
        
        fig.add_trace(
            go.Scatter(
                x=param_values,
                y=values,
                mode='lines+markers',
                name=LABELS_MAP.get(target, target),
                line=dict(color=colors[i-1], width=3),
                marker=dict(size=6),
                hovertemplate=(
                    f'<b>{sensitivity_result.parameter_name}</b>: %{{x:.1f}}<br>'
                    f'<b>{LABELS_MAP.get(target, target)}</b>: %{{y:.2f}}<br>'
                    '<extra></extra>'
                )
            ),
            row=i,
            col=1
        )
        
        # Ligne baseline
        fig.add_hline(
            y=values[n_points // 2],
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Baseline (Élasticité: {elasticity:.2f})",
            row=i,
            col=1
        )
        
        # Axes
        fig.update_xaxes(title_text=f"{sensitivity_result.parameter_name} (kg/m³)", row=i, col=1)
        fig.update_yaxes(title_text=LABELS_MAP.get(target, target), row=i, col=1)
    
    fig.update_layout(
        title=f"Analyse de Sensibilité - {sensitivity_result.parameter_name}",
        height=300 * len(targets),
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def plot_performance_radar(
    predictions: Dict[str, float],
    thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    name: str = "Formulation"
) -> go.Figure:
    """
    Graphique radar pour performance globale.
    
    Args:
        predictions: Dict prédictions
        thresholds: Seuils qualité (optionnel)
        name: Nom formulation
    
    Returns:
        Figure Plotly
    """
    
    from config.constants import QUALITY_THRESHOLDS
    
    if thresholds is None:
        thresholds = QUALITY_THRESHOLDS
    
    # Normalisation (0-100)
    categories = []
    values = []
    
    # Résistance (0-100 MPa → 0-100%)
    if 'Resistance' in predictions:
        categories.append("Résistance")
        values.append(min(100, predictions['Resistance'] / 60 * 100))
    
    # Diffusion Cl⁻ (inversé : moins = mieux)
    if 'Diffusion_Cl' in predictions:
        categories.append("Résistance Chlorures")
        diff_cl = predictions['Diffusion_Cl']
        # 0 = excellent (100%), 20 = faible (0%)
        values.append(max(0, 100 - (diff_cl / 20 * 100)))
    
    # Carbonatation (inversé)
    if 'Carbonatation' in predictions:
        categories.append("Résistance Carbonatation")
        carb = predictions['Carbonatation']
        values.append(max(0, 100 - (carb / 40 * 100)))
    
    # Ratio E/L (inversé)
    if 'Ratio_E_L' in predictions:
        categories.append("Compacité (E/L)")
        el = predictions['Ratio_E_L']
        # 0.3 = excellent (100%), 0.7 = faible (0%)
        values.append(max(0, 100 - ((el - 0.3) / 0.4 * 100)))
    
    # Fermer le radar
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=name,
        line=dict(color=COLOR_PALETTE['primary'], width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[0, 25, 50, 75, 100],
                ticktext=['0', '25', '50', '75', '100']
            )
        ),
        title=f"Performance Globale - {name}",
        showlegend=False,
        height=450
    )
    
    return fig


def plot_cost_breakdown(
    composition: Dict[str, float],
    material_costs: Optional[Dict[str, float]] = None
) -> go.Figure:
    """
    Diagramme en barres des coûts par matériau.
    
    Args:
        composition: Composition béton
        material_costs: Coûts matériaux (€/kg)
    
    Returns:
        Figure Plotly
    """
    
    from config.constants import MATERIALS_COST_EURO_KG
    
    if material_costs is None:
        material_costs = MATERIALS_COST_EURO_KG
    
    # Calcul coûts
    costs = {}
    total_cost = 0
    
    for material, quantity in composition.items():
        if material in material_costs and quantity > 0:
            cost = quantity * material_costs[material]
            costs[LABELS_MAP.get(material, material)] = cost
            total_cost += cost
    
    # Trier par coût décroissant
    sorted_costs = dict(sorted(costs.items(), key=lambda x: x[1], reverse=True))
    
    fig = go.Figure(data=[go.Bar(
        x=list(sorted_costs.keys()),
        y=list(sorted_costs.values()),
        marker=dict(
            color=list(sorted_costs.values()),
            colorscale='Blues',
            showscale=False,
            line=dict(color='white', width=1.5)
        ),
        text=[f"{v:.2f} €" for v in sorted_costs.values()],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Coût: %{y:.2f} €/m³<extra></extra>'
    )])
    
    fig.update_layout(
        title=f"Répartition des Coûts (Total: {total_cost:.2f} €/m³)",
        xaxis_title="Matériau",
        yaxis_title="Coût (€/m³)",
        height=400,
        showlegend=False
    )
    
    return fig

def generate_response_surface_data(
    baseline: dict[str, float],
    param1: str,
    param2: str,
    model,
    feature_list: list[str],
    target: str = 'Resistance',
    n_points: int = 20
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Génère les données pour une surface de réponse 3D.
    
    Args:
        baseline: Formulation de base
        param1, param2: Paramètres axes X et Y
        model: Modèle ML
        feature_list: Liste des features
        target: Cible à prédire (Z)
        n_points: Résolution grille
    
    Returns:
        (X, Y, Z) meshgrids
    """
    from config.constants import BOUNDS
    from app.core.predictor import predict_concrete_properties
    
    # Plages
    x_range = np.linspace(
        BOUNDS[param1]['min'],
        BOUNDS[param1]['max'],
        n_points
    )
    
    y_range = np.linspace(
        BOUNDS[param2]['min'],
        BOUNDS[param2]['max'],
        n_points
    )
    
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.zeros_like(X)
    
    # Calcul prédictions
    for i in range(n_points):
        for j in range(n_points):
            composition = baseline.copy()
            composition[param1] = float(X[i, j])
            composition[param2] = float(Y[i, j])
            
            try:
                preds = predict_concrete_properties(
                    composition=composition,
                    model=model,
                    feature_list=feature_list,
                    validate=False
                )
                Z[i, j] = preds[target]
            except:
                Z[i, j] = np.nan
    
    logger.info(f"Surface generee: {param1} vs {param2} -> {target}")
    
    return X, Y, Z


def plot_response_surface_3d(
    X: np.ndarray,
    Y: np.ndarray,
    Z: np.ndarray,
    param1: str,
    param2: str,
    target: str,
    title: Optional[str] = None
) -> go.Figure:
    """
    Graphique 3D surface de réponse.
    
    Args:
        X, Y, Z: Meshgrids
        param1, param2: Noms paramètres
        target: Nom cible
        title: Titre custom (optionnel)
    
    Returns:
        Figure Plotly
    """
    from config.constants import LABELS_MAP
    
    fig = go.Figure(data=[go.Surface(
        x=X,
        y=Y,
        z=Z,
        colorscale='Viridis',
        colorbar=dict(
            title=LABELS_MAP.get(target, target),
            titleside='right',
            tickmode='linear',
            tick0=np.nanmin(Z),
            dtick=(np.nanmax(Z) - np.nanmin(Z)) / 5
        ),
        contours=dict(
            z=dict(
                show=True,
                usecolormap=True,
                highlightcolor="limegreen",
                project=dict(z=True)
            )
        ),
        hovertemplate=(
            f'<b>{LABELS_MAP.get(param1, param1)}</b>: %{{x:.1f}}<br>'
            f'<b>{LABELS_MAP.get(param2, param2)}</b>: %{{y:.1f}}<br>'
            f'<b>{LABELS_MAP.get(target, target)}</b>: %{{z:.2f}}<br>'
            '<extra></extra>'
        )
    )])
    
    # Mise en page
    fig.update_layout(
        title=title or f"Surface de Reponse 3D: {LABELS_MAP.get(target, target)}",
        scene=dict(
            xaxis_title=LABELS_MAP.get(param1, param1) + " (kg/m³)",
            yaxis_title=LABELS_MAP.get(param2, param2) + " (kg/m³)",
            zaxis_title=LABELS_MAP.get(target, target),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            )
        ),
        height=600,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig


def plot_contour_2d(
    X: np.ndarray,
    Y: np.ndarray,
    Z: np.ndarray,
    param1: str,
    param2: str,
    target: str,
    title: Optional[str] = None
) -> go.Figure:
    """
    Carte de contours 2D (vue de dessus).
    
    Args:
        X, Y, Z: Meshgrids
        param1, param2: Noms paramètres
        target: Nom cible
        title: Titre custom
    
    Returns:
        Figure Plotly
    """
    from config.constants import LABELS_MAP
    
    fig = go.Figure(data=go.Contour(
        x=X[0, :],
        y=Y[:, 0],
        z=Z,
        colorscale='Viridis',
        contours=dict(
            showlabels=True,
            labelfont=dict(
                size=12,
                color='white'
            )
        ),
        colorbar=dict(
            title=LABELS_MAP.get(target, target),
            titleside='right'
        ),
        hovertemplate=(
            f'<b>{LABELS_MAP.get(param1, param1)}</b>: %{{x:.1f}}<br>'
            f'<b>{LABELS_MAP.get(param2, param2)}</b>: %{{y:.1f}}<br>'
            f'<b>{LABELS_MAP.get(target, target)}</b>: %{{z:.2f}}<br>'
            '<extra></extra>'
        )
    ))
    
    # Ajouter point optimal
    optimal_idx = np.unravel_index(np.nanargmax(Z), Z.shape)
    optimal_x = X[optimal_idx]
    optimal_y = Y[optimal_idx]
    optimal_z = Z[optimal_idx]
    
    fig.add_trace(go.Scatter(
        x=[optimal_x],
        y=[optimal_y],
        mode='markers',
        marker=dict(
            size=15,
            color='red',
            symbol='star',
            line=dict(width=2, color='white')
        ),
        name='Optimal',
        hovertemplate=(
            f'<b>OPTIMAL</b><br>'
            f'{LABELS_MAP.get(param1, param1)}: {optimal_x:.1f}<br>'
            f'{LABELS_MAP.get(param2, param2)}: {optimal_y:.1f}<br>'
            f'{LABELS_MAP.get(target, target)}: {optimal_z:.2f}<br>'
            '<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title=title or f"Carte de Contours: {LABELS_MAP.get(target, target)}",
        xaxis_title=LABELS_MAP.get(param1, param1) + " (kg/m³)",
        yaxis_title=LABELS_MAP.get(param2, param2) + " (kg/m³)",
        height=500,
        showlegend=True
    )
    
    return fig


def plot_3d_scatter_formulations(
    formulations: list[dict],
    param1: str,
    param2: str,
    target: str,
    names: Optional[list[str]] = None
) -> go.Figure:
    """
    Nuage de points 3D pour comparer plusieurs formulations.
    
    Args:
        formulations: Liste de formulations
        param1, param2: Paramètres axes X et Y
        target: Cible axe Z
        names: Noms formulations (optionnel)
    
    Returns:
        Figure Plotly
    """
    from config.constants import LABELS_MAP
    
    if names is None:
        names = [f"Form. {i+1}" for i in range(len(formulations))]
    
    # Extraire données
    x_vals = [f[param1] for f in formulations]
    y_vals = [f[param2] for f in formulations]
    z_vals = [f[target] for f in formulations]
    
    fig = go.Figure(data=[go.Scatter3d(
        x=x_vals,
        y=y_vals,
        z=z_vals,
        mode='markers+text',
        marker=dict(
            size=10,
            color=z_vals,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title=LABELS_MAP.get(target, target)),
            line=dict(width=1, color='white')
        ),
        text=names,
        textposition='top center',
        textfont=dict(size=10),
        hovertemplate=(
            '<b>%{text}</b><br>'
            f'{LABELS_MAP.get(param1, param1)}: %{{x:.1f}}<br>'
            f'{LABELS_MAP.get(param2, param2)}: %{{y:.1f}}<br>'
            f'{LABELS_MAP.get(target, target)}: %{{z:.2f}}<br>'
            '<extra></extra>'
        )
    )])
    
    fig.update_layout(
        title=f"Comparaison 3D: {LABELS_MAP.get(target, target)}",
        scene=dict(
            xaxis_title=LABELS_MAP.get(param1, param1),
            yaxis_title=LABELS_MAP.get(param2, param2),
            zaxis_title=LABELS_MAP.get(target, target)
        ),
        height=600
    )
    
    return fig


def plot_heatmap_correlation(
    data: dict[str, list[float]],
    title: str = "Matrice de Correlation"
) -> go.Figure:
    """
    Heatmap de corrélation entre paramètres.
    
    Args:
        data: Dict {nom_param: [valeurs]}
        title: Titre graphique
    
    Returns:
        Figure Plotly
    """
    import pandas as pd
    
    df = pd.DataFrame(data)
    corr_matrix = df.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont=dict(size=10),
        colorbar=dict(title="Correlation"),
        hovertemplate=(
            '<b>%{y}</b> vs <b>%{x}</b><br>'
            'Correlation: %{z:.3f}<br>'
            '<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="",
        height=500,
        width=600
    )
    
    return fig

__all__ = [
    'plot_composition_pie',
    'plot_parallel_coordinates',
    'plot_sensitivity',
    'plot_performance_radar',
    'plot_cost_breakdown',
    'generate_response_surface_data',
    'plot_response_surface_3d',
    'plot_contour_2d',
    'plot_3d_scatter_formulations',
    'plot_heatmap_correlation'
]