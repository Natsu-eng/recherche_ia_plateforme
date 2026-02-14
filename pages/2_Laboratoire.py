"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Laboratoire - Analyses Avancées COMPLÈTE
Fichier: pages/2_Laboratoire.py
Version: 2.0.0 - TOUTES FONCTIONNALITÉS
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import logging
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE, BOUNDS, LABELS_MAP
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.forms import render_formulation_input
from app.components.cards import info_box, metric_card
from app.core.analyzer import ConcreteAnalyzer
from app.core.session_manager import initialize_session

initialize_session()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Laboratoire - Béton IA",
    page_icon="🧪",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        🧪 Laboratoire - Analyses Avancées
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Suite complète d'outils d'analyse: Sensibilité, Monte Carlo, Plans d'Expériences, Surfaces 3D
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SÉLECTEUR DE MODE
# ═══════════════════════════════════════════════════════════════════════════════

mode = st.radio(
    "📋 Type d'Analyse",
    options=[
        "Sensibilité Simple",
        "Sensibilité Multi-Paramètres",
        "Monte Carlo",
        "Plan d'Expériences (DOE)",
        "Surfaces 3D"
    ],
    horizontal=True,
    help="Choisissez le type d'analyse statistique"
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1: SENSIBILITÉ SIMPLE
# ═══════════════════════════════════════════════════════════════════════════════

if mode == "Sensibilité Simple":
    from config.constants import PRESET_FORMULATIONS
    
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("### ⚙️ Configuration")
        
        preset_names = list(PRESET_FORMULATIONS.keys())
        selected_preset = st.selectbox(
            "🧪 Formulation de référence",
            options=preset_names,
            index=0
        )
        
        baseline_formulation = {
            k: v for k, v in PRESET_FORMULATIONS[selected_preset].items()
            if k in BOUNDS
        }
        
        st.markdown("---")
        
        parameter_options = ['Ciment', 'Eau', 'Laitier', 'CendresVolantes', 
                           'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']
        
        selected_param = st.selectbox(
            "📊 Paramètre à analyser",
            options=parameter_options,
            index=0
        )
        
        variation_percent = st.slider(
            "📈 Plage de variation (%)",
            min_value=5,
            max_value=50,
            value=20,
            step=5
        )
        
        n_points = st.slider(
            "🔢 Nombre de points",
            min_value=10,
            max_value=50,
            value=20,
            step=5
        )
        
        analyze_button = st.button(
            "🚀 Lancer l'Analyse",
            type="primary",
            use_container_width=True
        )
    
    with col_right:
        st.markdown("### 📊 Résultats de Sensibilité")
        
        if analyze_button:
            with st.spinner("🔄 Analyse en cours..."):
                try:
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    analyzer = ConcreteAnalyzer()
                    
                    sensitivity_result = analyzer.sensitivity_analysis(
                        baseline_formulation=baseline_formulation,
                        parameter=selected_param,
                        feature_list=features,
                        predictor=model,
                        variation_percent=variation_percent,
                        n_points=n_points
                    )
                    
                    st.success("Analyse terminee !")
                    
                    # Élasticités
                    st.markdown("#### Elasticites")
                    col_e1, col_e2, col_e3 = st.columns(3)
                    
                    elasticities = sensitivity_result.elasticities
                    
                    with col_e1:
                        elast_r = elasticities.get('Resistance', 0)
                        st.metric("Resistance", f"{elast_r:.3f}")
                    
                    with col_e2:
                        elast_d = elasticities.get('Diffusion_Cl', 0)
                        st.metric("Diffusion Cl-", f"{elast_d:.3f}")
                    
                    with col_e3:
                        elast_c = elasticities.get('Carbonatation', 0)
                        st.metric("Carbonatation", f"{elast_c:.3f}")
                    
                    # Graphiques
                    st.markdown("---")
                    fig = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=[
                            "Impact sur Resistance (MPa)",
                            "Impact sur Diffusion Cl- (x10^-12 m²/s)",
                            "Impact sur Carbonatation (mm)"
                        ],
                        vertical_spacing=0.10
                    )
                    
                    min_val, max_val = sensitivity_result.variation_range
                    param_values = np.linspace(min_val, max_val, n_points)
                    baseline_value = sensitivity_result.baseline_value
                    
                    targets = ['Resistance', 'Diffusion_Cl', 'Carbonatation']
                    colors = [COLOR_PALETTE['primary'], COLOR_PALETTE['success'], COLOR_PALETTE['warning']]
                    
                    for i, (target, color) in enumerate(zip(targets, colors), start=1):
                        values = sensitivity_result.impacts[target]
                        
                        fig.add_trace(
                            go.Scatter(
                                x=param_values,
                                y=values,
                                mode='lines+markers',
                                line=dict(color=color, width=3),
                                marker=dict(size=6),
                                showlegend=False
                            ),
                            row=i, col=1
                        )
                        
                        fig.add_hline(
                            y=values[n_points // 2],
                            line_dash="dash",
                            line_color="gray",
                            row=i, col=1
                        )
                        
                        fig.add_vline(
                            x=baseline_value,
                            line_dash="dot",
                            line_color="red",
                            row=i, col=1
                        )
                    
                    fig.update_layout(height=900, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"Erreur sensibilite: {e}", exc_info=True)
        else:
            info_box(
                "Mode d'emploi",
                """
                1. Selectionnez une formulation de reference
                2. Choisissez le parametre a analyser
                3. Definissez la plage de variation (%)
                4. Cliquez sur Lancer l'Analyse
                """,
                icon="i",
                color="info"
            )

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2: SENSIBILITÉ MULTI-PARAMÈTRES
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "Sensibilité Multi-Paramètres":
    col_adv1, col_adv2 = st.columns([1, 1])
    
    with col_adv1:
        st.markdown("#### Formulation Personnalisee")
        baseline_formulation_adv = render_formulation_input(
            key_suffix="lab_advanced",
            layout="compact",
            show_presets=True
        )
    
    with col_adv2:
        st.markdown("#### Comparaison Multi-Parametres")
        
        params_to_compare = st.multiselect(
            "Parametres a comparer",
            options=['Ciment', 'Eau', 'Laitier', 'Superplastifiant', 'Age'],
            default=['Ciment', 'Eau'],
            max_selections=3
        )
        
        if st.button("Comparer les Sensibilites", type="primary", use_container_width=True):
            if len(params_to_compare) < 2:
                st.warning("Selectionnez au moins 2 parametres")
            else:
                with st.spinner("Calcul en cours..."):
                    try:
                        model = st.session_state.get('model')
                        features = st.session_state.get('features')
                        analyzer = ConcreteAnalyzer()
                        
                        results = {}
                        for param in params_to_compare:
                            result = analyzer.sensitivity_analysis(
                                baseline_formulation=baseline_formulation_adv,
                                parameter=param,
                                feature_list=features,
                                predictor=model,
                                variation_percent=20,
                                n_points=15
                            )
                            results[param] = result
                        
                        st.success("Comparaison terminee")
                        
                        # Tableau élasticités
                        elasticity_data = []
                        for param, res in results.items():
                            elasticity_data.append({
                                'Parametre': param,
                                'Resistance': res.elasticities.get('Resistance', 0),
                                'Diffusion Cl-': res.elasticities.get('Diffusion_Cl', 0),
                                'Carbonatation': res.elasticities.get('Carbonatation', 0)
                            })
                        
                        df_elast = pd.DataFrame(elasticity_data)
                        st.dataframe(df_elast, use_container_width=True)
                        
                        # Graphique comparatif
                        fig_comp = go.Figure()
                        for param in params_to_compare:
                            fig_comp.add_trace(go.Bar(
                                name=param,
                                x=['Resistance', 'Diffusion Cl-', 'Carbonatation'],
                                y=[
                                    results[param].elasticities.get('Resistance', 0),
                                    results[param].elasticities.get('Diffusion_Cl', 0),
                                    results[param].elasticities.get('Carbonatation', 0)
                                ]
                            ))
                        
                        fig_comp.update_layout(
                            title="Comparaison des Elasticites",
                            barmode='group',
                            height=400
                        )
                        st.plotly_chart(fig_comp, use_container_width=True)
                    
                    except Exception as e:
                        st.error(f"Erreur: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 3: MONTE CARLO
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "Monte Carlo":
    st.markdown("### Simulation Monte Carlo")
    st.info("Quantifiez l'incertitude des predictions en simulant des variations aleatoires")
    
    col_mc1, col_mc2 = st.columns([1, 2])
    
    with col_mc1:
        st.markdown("#### Configuration")
        
        baseline_mc = render_formulation_input(
            key_suffix="monte_carlo",
            layout="compact",
            show_presets=True
        )
        
        n_simulations = st.slider(
            "Nombre de simulations",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100
        )
        
        uncertainty = st.slider(
            "Incertitude (%) par parametre",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5
        )
        
        run_mc = st.button("Lancer Monte Carlo", type="primary", use_container_width=True)
    
    with col_mc2:
        st.markdown("#### Resultats")
        
        if run_mc:
            with st.spinner(f"Simulation de {n_simulations} scenarios..."):
                try:
                    from app.core.predictor import predict_concrete_properties
                    
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    
                    # Simulation Monte Carlo
                    results_mc = {
                        'Resistance': [],
                        'Diffusion_Cl': [],
                        'Carbonatation': []
                    }
                    
                    valid_sims = 0
                    progress_bar = st.progress(0)
                    
                    for i in range(n_simulations):
                        # Perturbation
                        perturbed = {}
                        for param, value in baseline_mc.items():
                            if value > 0:
                                noise = np.random.normal(0, uncertainty / 100 * value)
                                perturbed[param] = max(0, value + noise)
                            else:
                                perturbed[param] = 0
                        
                        # Prédiction
                        try:
                            preds = predict_concrete_properties(
                                composition=perturbed,
                                model=model,
                                feature_list=features,
                                validate=False
                            )
                            
                            results_mc['Resistance'].append(preds['Resistance'])
                            results_mc['Diffusion_Cl'].append(preds['Diffusion_Cl'])
                            results_mc['Carbonatation'].append(preds['Carbonatation'])
                            valid_sims += 1
                        except:
                            continue
                        
                        if i % 50 == 0:
                            progress_bar.progress((i + 1) / n_simulations)
                    
                    progress_bar.progress(1.0)
                    st.success(f"{valid_sims}/{n_simulations} simulations valides")
                    
                    # Statistiques
                    st.markdown("##### Statistiques Descriptives")
                    
                    col_s1, col_s2, col_s3 = st.columns(3)
                    
                    with col_s1:
                        mean_r = np.mean(results_mc['Resistance'])
                        std_r = np.std(results_mc['Resistance'])
                        st.metric("Resistance Moyenne", f"{mean_r:.2f} MPa", delta=f"±{std_r:.2f}")
                    
                    with col_s2:
                        mean_d = np.mean(results_mc['Diffusion_Cl'])
                        std_d = np.std(results_mc['Diffusion_Cl'])
                        st.metric("Diffusion Moyenne", f"{mean_d:.2f}", delta=f"±{std_d:.2f}")
                    
                    with col_s3:
                        mean_c = np.mean(results_mc['Carbonatation'])
                        std_c = np.std(results_mc['Carbonatation'])
                        st.metric("Carbonatation Moyenne", f"{mean_c:.2f} mm", delta=f"±{std_c:.2f}")
                    
                    # Histogrammes
                    fig_mc = make_subplots(rows=1, cols=3, subplot_titles=[
                        "Resistance", "Diffusion Cl-", "Carbonatation"
                    ])
                    
                    targets_mc = ['Resistance', 'Diffusion_Cl', 'Carbonatation']
                    colors_mc = ['#3498db', '#2ecc71', '#e74c3c']
                    
                    for i, (target, color) in enumerate(zip(targets_mc, colors_mc), start=1):
                        values = results_mc[target]
                        
                        fig_mc.add_trace(
                            go.Histogram(
                                x=values,
                                marker_color=color,
                                opacity=0.7,
                                nbinsx=30,
                                showlegend=False
                            ),
                            row=1, col=i
                        )
                        
                        mean_val = np.mean(values)
                        fig_mc.add_vline(
                            x=mean_val,
                            line_dash="dash",
                            line_color="red",
                            row=1, col=i
                        )
                    
                    fig_mc.update_layout(
                        title="Distributions de Probabilite",
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_mc, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"Monte Carlo error: {e}", exc_info=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 4: PLAN D'EXPÉRIENCES (DOE)
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "Plan d'Expériences (DOE)":
    st.markdown("### Design of Experiments")
    st.info("Explorez systematiquement l'espace des parametres")
    
    col_doe1, col_doe2 = st.columns([1, 2])
    
    with col_doe1:
        st.markdown("#### Configuration")
        
        baseline_doe = render_formulation_input(
            key_suffix="doe",
            layout="compact",
            show_presets=True
        )
        
        available_params_doe = ['Ciment', 'Eau', 'Laitier', 'Superplastifiant', 'Age']
        
        selected_params_doe = st.multiselect(
            "Parametres a varier",
            options=available_params_doe,
            default=['Ciment', 'Eau'],
            max_selections=4
        )
        
        n_levels = st.radio(
            "Nombre de niveaux",
            options=[2, 3],
            index=1
        )
        
        variation_doe = st.slider(
            "Plage de variation (%)",
            min_value=10,
            max_value=30,
            value=20,
            step=5
        )
        
        run_doe = st.button("Generer Plan DOE", type="primary", use_container_width=True)
    
    with col_doe2:
        st.markdown("#### Resultats")
        
        if run_doe and len(selected_params_doe) >= 2:
            with st.spinner("Generation et execution du plan..."):
                try:
                    from app.core.predictor import predict_concrete_properties
                    from itertools import product
                    
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    
                    # Générer plan factoriel
                    if n_levels == 2:
                        level_values = [-1, 1]
                    else:
                        level_values = [-1, 0, 1]
                    
                    combinations = list(product(level_values, repeat=len(selected_params_doe)))
                    
                    experiments = []
                    for combo in combinations:
                        experiment = baseline_doe.copy()
                        for param, level in zip(selected_params_doe, combo):
                            base_value = baseline_doe[param]
                            delta = base_value * (variation_doe / 100) * level
                            experiment[param] = max(0, base_value + delta)
                        experiments.append(experiment)
                    
                    n_experiments = len(experiments)
                    st.info(f"{n_experiments} experiences generees ({n_levels}^{len(selected_params_doe)})")
                    
                    # Exécuter
                    responses_doe = {
                        'Resistance': [],
                        'Diffusion_Cl': [],
                        'Carbonatation': []
                    }
                    
                    progress_doe = st.progress(0)
                    
                    for i, exp in enumerate(experiments):
                        try:
                            preds = predict_concrete_properties(
                                composition=exp,
                                model=model,
                                feature_list=features,
                                validate=False
                            )
                            responses_doe['Resistance'].append(preds['Resistance'])
                            responses_doe['Diffusion_Cl'].append(preds['Diffusion_Cl'])
                            responses_doe['Carbonatation'].append(preds['Carbonatation'])
                        except:
                            responses_doe['Resistance'].append(np.nan)
                            responses_doe['Diffusion_Cl'].append(np.nan)
                            responses_doe['Carbonatation'].append(np.nan)
                        
                        progress_doe.progress((i + 1) / n_experiments)
                    
                    st.success("Plan execute et analyse")
                    
                    # Analyse effets
                    effects_doe = {}
                    for target_doe in ['Resistance', 'Diffusion_Cl', 'Carbonatation']:
                        param_effects = {}
                        for param in selected_params_doe:
                            # Effet principal (simplifié)
                            param_idx = selected_params_doe.index(param)
                            high_vals = [responses_doe[target_doe][i] for i, combo in enumerate(combinations) if combo[param_idx] > 0]
                            low_vals = [responses_doe[target_doe][i] for i, combo in enumerate(combinations) if combo[param_idx] < 0]
                            
                            if high_vals and low_vals:
                                effect = np.nanmean(high_vals) - np.nanmean(low_vals)
                                param_effects[param] = float(effect)
                        
                        effects_doe[target_doe] = param_effects
                    
                    # Graphique effets
                    fig_doe = make_subplots(rows=1, cols=3, subplot_titles=list(effects_doe.keys()))
                    
                    for i, (target_doe, param_effects) in enumerate(effects_doe.items(), start=1):
                        sorted_effects = dict(sorted(param_effects.items(), key=lambda x: abs(x[1]), reverse=True))
                        
                        fig_doe.add_trace(
                            go.Bar(
                                x=list(sorted_effects.keys()),
                                y=list(sorted_effects.values()),
                                marker_color=['green' if v > 0 else 'red' for v in sorted_effects.values()],
                                showlegend=False
                            ),
                            row=1, col=i
                        )
                    
                    fig_doe.update_layout(title="Effets Principaux", height=400)
                    st.plotly_chart(fig_doe, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"DOE error: {e}", exc_info=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 5: SURFACES 3D
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "Surfaces 3D":
    st.markdown("### Surfaces de Reponse 3D")
    st.info("Visualisez l'influence combinee de deux parametres")
    
    col_3d1, col_3d2 = st.columns([1, 2])
    
    with col_3d1:
        st.markdown("#### Configuration")
        
        baseline_3d = render_formulation_input(
            key_suffix="surface_3d",
            layout="compact",
            show_presets=True
        )
        
        available_params_3d = ['Ciment', 'Eau', 'Laitier', 'CendresVolantes', 
                               'Superplastifiant', 'Age']
        
        param_x = st.selectbox("Axe X", options=available_params_3d, index=0)
        param_y = st.selectbox(
            "Axe Y",
            options=[p for p in available_params_3d if p != param_x],
            index=0
        )
        
        target_3d = st.selectbox(
            "Cible (Axe Z)",
            options=['Resistance', 'Diffusion_Cl', 'Carbonatation'],
            index=0
        )
        
        resolution = st.slider(
            "Resolution (points par axe)",
            min_value=10,
            max_value=30,
            value=15
        )
        
        plot_type = st.radio(
            "Type de visualisation",
            options=["Surface 3D", "Contours 2D", "Les deux"],
            index=0
        )
        
        generate_3d = st.button("Generer Surface", type="primary", use_container_width=True)
    
    with col_3d2:
        st.markdown("#### Visualisation")
        
        if generate_3d:
            with st.spinner(f"Calcul de la surface ({resolution}x{resolution} points)..."):
                try:
                    from app.components.charts import generate_response_surface_data, plot_response_surface_3d, plot_contour_2d
                    
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    
                    # Générer surface
                    X, Y, Z = generate_response_surface_data(
                        baseline=baseline_3d,
                        param1=param_x,
                        param2=param_y,
                        model=model,
                        feature_list=features,
                        target=target_3d,
                        n_points=resolution
                    )
                    
                    st.success("Surface generee")
                    
                    # Affichage
                    if plot_type in ["Surface 3D", "Les deux"]:
                        fig_3d = plot_response_surface_3d(X, Y, Z, param_x, param_y, target_3d)
                        st.plotly_chart(fig_3d, use_container_width=True)
                    
                    if plot_type in ["Contours 2D", "Les deux"]:
                        fig_contour = plot_contour_2d(X, Y, Z, param_x, param_y, target_3d)
                        st.plotly_chart(fig_contour, use_container_width=True)
                    
                    # Infos
                    col_i1, col_i2, col_i3 = st.columns(3)
                    
                    with col_i1:
                        st.metric("Valeur Min", f"{np.nanmin(Z):.2f}")
                    with col_i2:
                        st.metric("Valeur Max", f"{np.nanmax(Z):.2f}")
                    with col_i3:
                        st.metric("Plage", f"{np.nanmax(Z) - np.nanmin(Z):.2f}")
                
                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"3D Surface error: {e}", exc_info=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("Laboratoire d'Analyses Avancees - Concrete AI Platform v2.0")