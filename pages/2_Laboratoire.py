"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Laboratoire - Analyses Avancées AVEC CO₂
Fichier: pages/2_Laboratoire.py
Version: 1.0.0 - NIVEAU RECHERCHE + CO₂
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

# IMPORTS NOUVEAUX MOTEURS
from app.lab.monte_carlo_engine import MonteCarloEngine
from app.lab.surface_engine import SurfaceEngine, plot_surface_with_co2

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
        🧪 Laboratoire - Analyses Avancées + CO₂
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Niveau Recherche : Monte Carlo, Surfaces 3D, DOE, Sensibilité - Avec empreinte carbone
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SÉLECTEUR MODE
# ═══════════════════════════════════════════════════════════════════════════════

mode = st.radio(
    "📋 Type d'Analyse",
    options=[
        "🔍 Sensibilité Simple",
        "📊 Sensibilité Multi-Paramètres",
        "🎲 Monte Carlo + CO₂",  
        "📐 Surfaces 3D + CO₂"  
    ],
    horizontal=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1: SENSIBILITÉ SIMPLE (INCHANGÉ)
# ═══════════════════════════════════════════════════════════════════════════════

if mode == "🔍 Sensibilité Simple":
    from config.constants import PRESET_FORMULATIONS
    
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("### ⚙️ Configuration")
        
        preset_names = list(PRESET_FORMULATIONS.keys())
        selected_preset = st.selectbox("🧪 Formulation", options=preset_names, index=0)
        
        baseline_formulation = {k: v for k, v in PRESET_FORMULATIONS[selected_preset].items() if k in BOUNDS}
        
        st.markdown("---")
        
        parameter_options = ['Ciment', 'Eau', 'Laitier', 'CendresVolantes', 
                           'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']
        
        selected_param = st.selectbox("📊 Paramètre", options=parameter_options, index=0)
        variation_percent = st.slider("📈 Variation (%)", 5, 50, 20, 5)
        n_points = st.slider("🔢 Points", 10, 50, 20, 5)
        
        analyze_button = st.button("🚀 Analyser", type="primary", use_container_width=True)
    
    with col_right:
        st.markdown("### 📊 Résultats")
        
        if analyze_button:
            with st.spinner("🔄 Analyse..."):
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
                    
                    st.success("✅ Analyse terminée")
                    
                    # Élasticités
                    col_e1, col_e2, col_e3 = st.columns(3)
                    
                    with col_e1:
                        st.metric("Résistance", f"{sensitivity_result.elasticities.get('Resistance', 0):.3f}")
                    with col_e2:
                        st.metric("Diffusion Cl⁻", f"{sensitivity_result.elasticities.get('Diffusion_Cl', 0):.3f}")
                    with col_e3:
                        st.metric("Carbonatation", f"{sensitivity_result.elasticities.get('Carbonatation', 0):.3f}")
                    
                    # Graphiques
                    st.markdown("---")
                    fig = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=["Résistance", "Diffusion Cl⁻", "Carbonatation"],
                        vertical_spacing=0.10
                    )
                    
                    min_val, max_val = sensitivity_result.variation_range
                    param_values = np.linspace(min_val, max_val, n_points)
                    
                    targets = ['Resistance', 'Diffusion_Cl', 'Carbonatation']
                    colors = [COLOR_PALETTE['primary'], COLOR_PALETTE['success'], COLOR_PALETTE['warning']]
                    
                    for i, (target, color) in enumerate(zip(targets, colors), start=1):
                        values = sensitivity_result.impacts[target]
                        
                        fig.add_trace(
                            go.Scatter(x=param_values, y=values, mode='lines+markers',
                                     line=dict(color=color, width=3), marker=dict(size=6),
                                     showlegend=False),
                            row=i, col=1
                        )
                        
                        fig.add_hline(y=values[n_points // 2], line_dash="dash", line_color="gray", row=i, col=1)
                        fig.add_vline(x=sensitivity_result.baseline_value, line_dash="dot", line_color="red", row=i, col=1)
                    
                    fig.update_layout(height=900, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        else:
            info_box("Mode d'emploi", "1. Sélectionnez formulation\n2. Choisissez paramètre\n3. Lancez analyse", icon="ℹ️", color="info")

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2: SENSIBILITÉ MULTI (INCHANGÉ - Simplifié)
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "📊 Sensibilité Multi-Paramètres":
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
# MODE 3: MONTE CARLO + CO₂ (✅ NOUVEAU MOTEUR)
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "🎲 Monte Carlo + CO₂":
    st.markdown("### 🎲 Simulation Monte Carlo + Empreinte CO₂")
    st.info("✨ Moteur vectorisé niveau recherche : 4 cibles, statistiques complètes, tests normalité")
    
    col_mc1, col_mc2 = st.columns([1, 2])
    
    with col_mc1:
        st.markdown("#### Configuration")
        
        baseline_mc = render_formulation_input(
            key_suffix="monte_carlo",
            layout="compact",
            show_presets=True
        )
        
        # ✅ Type ciment
        from config.co2_database import CEMENT_CO2_KG_PER_TONNE
        cement_types = list(CEMENT_CO2_KG_PER_TONNE.keys())
        
        selected_cement_mc = st.selectbox(
            "🏭 Type de Ciment",
            options=cement_types,
            index=0,
            key="mc_cement",
            help="Impact CO₂"
        )
        
        cement_factor = CEMENT_CO2_KG_PER_TONNE[selected_cement_mc]
        st.caption(f"📊 Facteur: {cement_factor:.1f} kg CO₂/t")
        
        st.markdown("---")
        
        n_simulations = st.slider("Nombre simulations", 100, 5000, 1000, 100)
        uncertainty = st.slider("Incertitude (%)", 1.0, 10.0, 5.0, 0.5)
        
        run_mc = st.button("🚀 Lancer Monte Carlo", type="primary", use_container_width=True)
    
    with col_mc2:
        st.markdown("#### Résultats + CO₂")
        
        if run_mc:
            with st.spinner(f"🔄 Simulation {n_simulations} scénarios..."):
                try:
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    
                    # ✅ NOUVEAU MOTEUR
                    engine = MonteCarloEngine(seed=42)
                    
                    result = engine.run_simulation(
                        baseline_formulation=baseline_mc,
                        model=model,
                        feature_list=features,
                        cement_type=selected_cement_mc,
                        n_simulations=n_simulations,
                        uncertainty_percent=uncertainty,
                        batch_size=100
                    )
                    
                    st.success(f"✅ {result.n_valid}/{result.n_simulations} simulations valides")
                    
                    # ═══════════════════════════════════════════════════
                    # STATISTIQUES (4 CIBLES)
                    # ═══════════════════════════════════════════════════
                    
                    st.markdown("##### 📊 Statistiques Descriptives")
                    
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    
                    with col_s1:
                        st.metric("Résistance", f"{result.resistance_stats.mean:.1f} MPa",
                                delta=f"±{result.resistance_stats.std:.1f}")
                        st.caption(f"CV: {result.resistance_stats.cv_percent:.1f}%")
                    
                    with col_s2:
                        st.metric("Diffusion Cl⁻", f"{result.diffusion_stats.mean:.2f}",
                                delta=f"±{result.diffusion_stats.std:.2f}")
                        st.caption(f"CV: {result.diffusion_stats.cv_percent:.1f}%")
                    
                    with col_s3:
                        st.metric("Carbonatation", f"{result.carbonatation_stats.mean:.1f} mm",
                                delta=f"±{result.carbonatation_stats.std:.1f}")
                        st.caption(f"CV: {result.carbonatation_stats.cv_percent:.1f}%")
                    
                    # ✅ CO₂
                    with col_s4:
                        st.metric("🌍 CO₂", f"{result.co2_stats.mean:.1f} kg/m³",
                                delta=f"±{result.co2_stats.std:.1f}")
                        st.caption(f"CV: {result.co2_stats.cv_percent:.1f}%")
                    
                    st.markdown("---")
                    
                    # ═══════════════════════════════════════════════════
                    # INTERVALLES CONFIANCE
                    # ═══════════════════════════════════════════════════
                    
                    with st.expander("📈 Intervalles Confiance 95% + Risk Metrics"):
                        col_ic1, col_ic2, col_ic3, col_ic4 = st.columns(4)
                        
                        with col_ic1:
                            st.markdown("**Résistance**")
                            st.markdown(f"IC: [{result.resistance_stats.ci_lower:.1f}, {result.resistance_stats.ci_upper:.1f}]")
                            st.markdown(f"VaR 95%: {result.resistance_stats.var_95:.1f}")
                        
                        with col_ic2:
                            st.markdown("**Diffusion**")
                            st.markdown(f"IC: [{result.diffusion_stats.ci_lower:.2f}, {result.diffusion_stats.ci_upper:.2f}]")
                            st.markdown(f"VaR 95%: {result.diffusion_stats.var_95:.2f}")
                        
                        with col_ic3:
                            st.markdown("**Carbonatation**")
                            st.markdown(f"IC: [{result.carbonatation_stats.ci_lower:.1f}, {result.carbonatation_stats.ci_upper:.1f}]")
                            st.markdown(f"VaR 95%: {result.carbonatation_stats.var_95:.1f}")
                        
                        # ✅ CO₂
                        with col_ic4:
                            st.markdown("**CO₂**")
                            st.markdown(f"IC: [{result.co2_stats.ci_lower:.1f}, {result.co2_stats.ci_upper:.1f}]")
                            st.markdown(f"VaR 95%: {result.co2_stats.var_95:.1f}")
                    
                    # ═══════════════════════════════════════════════════
                    # GRAPHIQUES (4 HISTOGRAMMES)
                    # ═══════════════════════════════════════════════════
                    
                    st.markdown("---")
                    st.markdown("##### 📊 Distributions de Probabilité")
                    
                    fig_mc = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=['Résistance (MPa)', 'Diffusion Cl⁻', 'Carbonatation (mm)', '🌍 CO₂ (kg/m³)']
                    )
                    
                    # Résistance
                    fig_mc.add_trace(go.Histogram(x=result.resistance_samples, marker_color='#3498db',
                                                 opacity=0.7, nbinsx=30, showlegend=False), row=1, col=1)
                    fig_mc.add_vline(x=result.resistance_stats.mean, line_dash="dash", line_color="red", row=1, col=1)
                    
                    # Diffusion
                    fig_mc.add_trace(go.Histogram(x=result.diffusion_samples, marker_color='#2ecc71',
                                                 opacity=0.7, nbinsx=30, showlegend=False), row=1, col=2)
                    fig_mc.add_vline(x=result.diffusion_stats.mean, line_dash="dash", line_color="red", row=1, col=2)
                    
                    # Carbonatation
                    fig_mc.add_trace(go.Histogram(x=result.carbonatation_samples, marker_color='#e74c3c',
                                                 opacity=0.7, nbinsx=30, showlegend=False), row=2, col=1)
                    fig_mc.add_vline(x=result.carbonatation_stats.mean, line_dash="dash", line_color="red", row=2, col=1)
                    
                    # ✅ CO₂
                    fig_mc.add_trace(go.Histogram(x=result.co2_samples, marker_color='#27ae60',
                                                 opacity=0.7, nbinsx=30, showlegend=False), row=2, col=2)
                    fig_mc.add_vline(x=result.co2_stats.mean, line_dash="dash", line_color="red", row=2, col=2)
                    
                    fig_mc.update_layout(title="Distributions Monte Carlo (4 Cibles)", height=600, showlegend=False)
                    st.plotly_chart(fig_mc, use_container_width=True)
                    
                    # ═══════════════════════════════════════════════════
                    # TESTS NORMALITÉ
                    # ═══════════════════════════════════════════════════
                    
                    with st.expander("🧪 Tests Normalité (Shapiro-Wilk p>0.05)"):
                        tests_results = [
                            ("Résistance", result.resistance_stats),
                            ("Diffusion Cl⁻", result.diffusion_stats),
                            ("Carbonatation", result.carbonatation_stats),
                            ("CO₂", result.co2_stats)
                        ]
                        
                        for name, stats in tests_results:
                            status = "✅ Normale" if stats.is_normal else "❌ Non-normale"
                            st.markdown(f"**{name}** : {status} (p={stats.normality_pvalue:.4f})")
                
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 4: SURFACES 3D + CO₂
# ═══════════════════════════════════════════════════════════════════════════════

elif mode == "📐 Surfaces 3D + CO₂":
    st.markdown("### 📐 Surfaces de Réponse 3D + Empreinte CO₂")
    st.info("✨ Génération simultanée des 4 surfaces (Résistance, Diffusion, Carbonatation, CO₂)")
    
    col_3d1, col_3d2 = st.columns([1, 2])
    
    with col_3d1:
        st.markdown("#### Configuration")
        
        baseline_3d = render_formulation_input(key_suffix="surface_3d", layout="compact", show_presets=True)
        
        # ✅ Type ciment
        from config.co2_database import CEMENT_CO2_KG_PER_TONNE
        cement_types_3d = list(CEMENT_CO2_KG_PER_TONNE.keys())
        
        selected_cement_3d = st.selectbox("🏭 Type Ciment", options=cement_types_3d, index=0, key="surf_cement")
        
        st.markdown("---")
        
        available_params = ['Ciment', 'Eau', 'Laitier', 'CendresVolantes', 'Superplastifiant', 'Age']
        
        param_x = st.selectbox("Axe X", options=available_params, index=0)
        param_y = st.selectbox("Axe Y", options=[p for p in available_params if p != param_x], index=0)
        
        resolution = st.slider("Résolution", 10, 30, 15)
        
        generate_3d = st.button("🚀 Générer Surfaces", type="primary", use_container_width=True)
    
    with col_3d2:
        st.markdown("#### Visualisation 4 Cibles")
        
        if generate_3d:
            with st.spinner(f"🔄 Calcul surfaces ({resolution}x{resolution})..."):
                try:
                    model = st.session_state.get('model')
                    features = st.session_state.get('features')
                    
                    # ✅ NOUVEAU MOTEUR
                    engine = SurfaceEngine()
                    
                    multi_surf = engine.generate_all_surfaces(
                        baseline=baseline_3d,
                        param1=param_x,
                        param2=param_y,
                        model=model,
                        feature_list=features,
                        cement_type=selected_cement_3d,
                        resolution=resolution
                    )
                    
                    st.success("✅ 4 surfaces générées")
                    
                    # ═══════════════════════════════════════════════════
                    # GRAPHIQUE 4 SUBPLOTS
                    # ═══════════════════════════════════════════════════
                    
                    fig_multi = plot_surface_with_co2(multi_surf)
                    st.plotly_chart(fig_multi, use_container_width=True)
                    
                    # ═══════════════════════════════════════════════════
                    # POINTS OPTIMAUX
                    # ═══════════════════════════════════════════════════
                    
                    st.markdown("---")
                    st.markdown("##### 🎯 Points Optimaux")
                    
                    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
                    
                    surfaces = [
                        ("Résistance", multi_surf.resistance_surface),
                        ("Diffusion", multi_surf.diffusion_surface),
                        ("Carbonatation", multi_surf.carbonatation_surface),
                        ("CO₂", multi_surf.co2_surface)
                    ]
                    
                    for col, (name, surf) in zip([col_opt1, col_opt2, col_opt3, col_opt4], surfaces):
                        with col:
                            st.markdown(f"**{name}**")
                            x_opt, y_opt, z_opt = surf.optimal_point
                            st.markdown(f"{param_x}: {x_opt:.0f}")
                            st.markdown(f"{param_y}: {y_opt:.0f}")
                            st.markdown(f"Valeur: {z_opt:.2f}")
                
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("🧪 Laboratoire Niveau Recherche v2.1.0 - Moteurs vectorisés + Empreinte CO₂")