"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: 4_Laboratoire.py - VERSION 1.0.0 COMPLÈTE
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

NOUVEAU v1.0.0 :
✅ Tous les types d'analyse disponibles
✅ Monte Carlo fonctionnel
✅ DOE (Latin Hypercube) fonctionnel
✅ Robustesse fonctionnelle
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))
from app.components.navbar import render_top_nav
from app.components.charts import create_sensitivity_chart
from app.styles.theme import apply_custom_theme
from app.core.predictor import predict_concrete_properties
from app.core.analyzer import ConcreteAnalyzer
from config.constants import BOUNDS, LABELS_MAP
from config.settings import UI_SETTINGS

st.set_page_config(
    page_title="Laboratoire R&D - IMT Nord Europe",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_theme()
render_top_nav(active_page="laboratoire")

@st.cache_resource
def load_ml_model():
    try:
        from app.models.loader import load_production_assets
        model, features, metadata = load_production_assets()
        return model, features, metadata, "production"
    except:
        try:
            from app.models.loader import load_demo_assets
            model, features, metadata = load_demo_assets()
            return model, features, metadata, "demo"
        except:
            return None, None, {}, "unavailable"

model, features, metadata, model_status = load_ml_model()
analyzer = ConcreteAnalyzer()

if 'lab_v21' not in st.session_state:
    st.session_state.lab_v21 = True
    st.session_state.experiments = []
    st.session_state.current_experiment = None
    st.session_state.baseline = {
        "Ciment": 280.0, "Laitier": 0.0, "CendresVolantes": 0.0,
        "Eau": 180.0, "Superplastifiant": 0.0,
        "GravilonsGros": 1100.0, "SableFin": 750.0, "Age": 28.0
    }

def calculate_elasticity(param_values, response_values):
    if len(param_values) < 3:
        return 0.0
    
    mid_idx = len(param_values) // 2
    
    if mid_idx > 0 and mid_idx < len(param_values) - 1:
        x_mid = param_values[mid_idx]
        y_mid = response_values[mid_idx]
        
        dy = response_values[mid_idx + 1] - response_values[mid_idx - 1]
        dx = param_values[mid_idx + 1] - param_values[mid_idx - 1]
        
        if dx != 0 and y_mid != 0 and x_mid != 0:
            slope = dy / dx
            elasticity = slope * (x_mid / y_mid)
            return elasticity
    
    return 0.0

st.markdown(f"""
<div style='background: linear-gradient(135deg, #B71C1C 0%, #880E4F 100%);
            padding: 1.8rem 2rem; border-radius: 15px; margin-bottom: 2rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div>
            <h1 style='color: white; margin: 0; font-size: 2em;'>
                🔬 Laboratoire R&D v1.0
            </h1>
            <p style='color: rgba(255,255,255,0.9); font-size: 1em; margin-top: 0.4rem;'>
                Plateforme d'analyse paramétrique scientifique
            </p>
        </div>
        <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; border-radius: 10px;'>
            <div style='color: white; font-weight: 600; font-size: 0.8em;'>
                {model_status.upper()}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1.2, 1.8], gap="large")

with col_left:
    st.markdown("### ⚙️ Configuration")
    
    st.markdown("#### 🎯 Type d'Analyse")
    
    analysis_type = st.radio(
        "Sélectionnez :",
        options=[
            "Analyse de Sensibilité",
            "Simulation Monte Carlo",
            "Plan d'Expériences (DOE)",
            "Analyse de Robustesse"
        ],
        help="Type d'analyse scientifique"
    )
    
    st.markdown("---")
    st.markdown("#### 📊 Paramètres")
    
    if analysis_type == "Analyse de Sensibilité":
        sensitivity_param = st.selectbox(
            "Variable :",
            options=list(BOUNDS.keys()),
            format_func=lambda x: LABELS_MAP.get(x, x)
        )
        
        bounds_param = BOUNDS[sensitivity_param]
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            min_val = st.number_input(
                "Min :",
                value=float(bounds_param["min"]),
                min_value=float(bounds_param["min"]),
                max_value=float(bounds_param["max"]),
                step=float(bounds_param.get("step", 10))
            )
        
        with col_r2:
            max_val = st.number_input(
                "Max :",
                value=float(bounds_param["max"]),
                min_value=float(bounds_param["min"]),
                max_value=float(bounds_param["max"]),
                step=float(bounds_param.get("step", 10))
            )
        
        num_points = st.slider("Points :", 5, 50, 20)
        
        response_vars = st.multiselect(
            "Indicateurs :",
            options=["Resistance", "Diffusion_Cl", "Carbonatation"],
            default=["Resistance", "Diffusion_Cl"]
        )
        
        use_bootstrap = st.checkbox("Bootstrap IC", value=False)
    
    elif analysis_type == "Simulation Monte Carlo":
        num_simulations = st.slider("Simulations :", 100, 5000, 1000, 100)
        
        mc_params = st.multiselect(
            "Paramètres incertains :",
            options=list(BOUNDS.keys()),
            default=["Ciment", "Eau"]
        )
        
        uncertainty_level = st.slider("Incertitude (%) :", 1, 20, 5)
    
    elif analysis_type == "Plan d'Expériences (DOE)":
        doe_params = st.multiselect(
            "Paramètres à explorer :",
            options=list(BOUNDS.keys()),
            default=["Ciment", "Eau", "Laitier"]
        )
        
        num_experiments = st.slider("Expériences :", 10, 100, 30)
    
    else:  # Robustesse
        robustness_params = st.multiselect(
            "Paramètres critiques :",
            options=list(BOUNDS.keys()),
            default=["Ciment", "Eau"]
        )
        
        robustness_level = st.slider("Variation (%) :", 1, 20, 5)
        num_trials = st.slider("Essais :", 50, 1000, 200)
    
    st.markdown("---")
    st.markdown("#### 🧱 Baseline")
    
    edit_baseline = st.checkbox("Modifier", value=False)
    
    if edit_baseline:
        with st.expander("✏️ Édition", expanded=True):
            for param in BOUNDS.keys():
                if analysis_type == "Analyse de Sensibilité" and param == sensitivity_param:
                    continue
                
                st.session_state.baseline[param] = st.number_input(
                    LABELS_MAP.get(param, param),
                    min_value=float(BOUNDS[param]["min"]),
                    max_value=float(BOUNDS[param]["max"]),
                    value=float(st.session_state.baseline[param]),
                    step=float(BOUNDS[param].get("step", 10)),
                    key=f"baseline_{param}_v21"
                )
    else:
        st.info(f"""
        Ciment: {st.session_state.baseline['Ciment']:.0f} kg/m³  
        Eau: {st.session_state.baseline['Eau']:.0f} L/m³  
        Âge: {st.session_state.baseline['Age']:.0f} jours
        """)
    
    st.markdown("---")
    
    experiment_name = st.text_input(
        "Nom :",
        value=f"{analysis_type[:4]}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        key="exp_name_v21"
    )
    
    run_btn = st.button(
        "🚀 Lancer",
        type="primary",
        use_container_width=True,
        disabled=(model is None)
    )

with col_right:
    if not run_btn and not st.session_state.current_experiment:
        st.markdown("""
        <div style='text-align: center; padding: 5rem 2rem; background: #FAFAFA; 
                    border-radius: 12px; border: 2px dashed #E0E0E0;'>
            <div style='font-size: 4.5em; margin-bottom: 1rem;'>🔬</div>
            <h2 style='color: #B71C1C; margin-bottom: 1rem;'>Laboratoire</h2>
            <p style='color: #666; font-size: 1rem; line-height: 1.6; max-width: 450px; margin: 0 auto;'>
                Configurez puis cliquez sur <strong>"🚀 Lancer"</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    if run_btn:
        with st.spinner(f"🔬 Analyse en cours..."):
            try:
                if analysis_type == "Analyse de Sensibilité":
                    if use_bootstrap:
                        baseline_val = st.session_state.baseline[sensitivity_param]
                        variation_pct = ((max_val - min_val) / max(baseline_val, 1e-6)) * 100
                        
                        results_obj = analyzer.sensitivity_analysis(
                            baseline_formulation=st.session_state.baseline,
                            parameter=sensitivity_param,
                            feature_list=features,
                            predictor=model,
                            variation_percent=variation_pct,
                            n_points=num_points
                        )
                        
                        param_values = np.linspace(min_val, max_val, num_points)
                        results = {
                            "param_values": param_values.tolist(),
                            "responses": results_obj.impacts
                        }
                        
                        ci_results = analyzer.confidence_interval(
                            formulation=st.session_state.baseline,
                            feature_list=features,
                            predictor=model,
                            n_bootstrap=100
                        )
                        
                        for resp_var in response_vars:
                            if resp_var in ci_results:
                                ci = ci_results[resp_var]
                                results[f"{resp_var}_CI_lower"] = ci.lower_bound
                                results[f"{resp_var}_CI_upper"] = ci.upper_bound
                    
                    else:
                        param_values = np.linspace(min_val, max_val, num_points)
                        results = {"param_values": param_values.tolist(), "responses": {}}
                        
                        for value in param_values:
                            mix = st.session_state.baseline.copy()
                            mix[sensitivity_param] = float(value)
                            
                            preds = predict_concrete_properties(
                                composition=mix,
                                model=model,
                                feature_list=features
                            )
                            
                            for resp_var in response_vars:
                                if resp_var not in results["responses"]:
                                    results["responses"][resp_var] = []
                                results["responses"][resp_var].append(float(preds[resp_var]))
                    
                    experiment = {
                        "name": experiment_name,
                        "type": analysis_type,
                        "param": sensitivity_param,
                        "param_values": results["param_values"],
                        "responses": results["responses"],
                        "baseline": st.session_state.baseline.copy(),
                        "timestamp": datetime.now().isoformat(),
                        "num_points": num_points,
                        "bootstrap": use_bootstrap
                    }
                
                elif analysis_type == "Simulation Monte Carlo":
                    results_data = []
                    
                    for _ in range(num_simulations):
                        mix = st.session_state.baseline.copy()
                        
                        for param in mc_params:
                            baseline_val = st.session_state.baseline[param]
                            std_dev = baseline_val * (uncertainty_level / 100)
                            variation = np.random.normal(0, std_dev)
                            new_val = np.clip(
                                baseline_val + variation,
                                BOUNDS[param]["min"],
                                BOUNDS[param]["max"]
                            )
                            mix[param] = float(new_val)
                        
                        preds = predict_concrete_properties(
                            composition=mix,
                            model=model,
                            feature_list=features
                        )
                        
                        results_data.append({
                            **{p: mix[p] for p in mc_params},
                            "Resistance": preds["Resistance"],
                            "Diffusion_Cl": preds["Diffusion_Cl"],
                            "Carbonatation": preds["Carbonatation"]
                        })
                    
                    df_mc = pd.DataFrame(results_data)
                    
                    experiment = {
                        "name": experiment_name,
                        "type": analysis_type,
                        "params": mc_params,
                        "num_simulations": num_simulations,
                        "uncertainty_level": uncertainty_level,
                        "results_df": df_mc,
                        "baseline": st.session_state.baseline.copy(),
                        "timestamp": datetime.now().isoformat()
                    }
                
                elif analysis_type == "Plan d'Expériences (DOE)":
                    from scipy.stats import qmc
                    
                    sampler = qmc.LatinHypercube(d=len(doe_params))
                    samples = sampler.random(n=num_experiments)
                    
                    results_data = []
                    
                    for sample in samples:
                        mix = st.session_state.baseline.copy()
                        
                        for idx, param in enumerate(doe_params):
                            param_range = BOUNDS[param]["max"] - BOUNDS[param]["min"]
                            mix[param] = float(BOUNDS[param]["min"] + sample[idx] * param_range)
                        
                        preds = predict_concrete_properties(
                            composition=mix,
                            model=model,
                            feature_list=features
                        )
                        
                        results_data.append({
                            **{p: mix[p] for p in doe_params},
                            "Resistance": preds["Resistance"],
                            "Diffusion_Cl": preds["Diffusion_Cl"],
                            "Carbonatation": preds["Carbonatation"]
                        })
                    
                    df_doe = pd.DataFrame(results_data)
                    
                    experiment = {
                        "name": experiment_name,
                        "type": analysis_type,
                        "params": doe_params,
                        "num_experiments": num_experiments,
                        "results_df": df_doe,
                        "baseline": st.session_state.baseline.copy(),
                        "timestamp": datetime.now().isoformat()
                    }
                
                else:  # Robustesse
                    results_data = []
                    
                    for _ in range(num_trials):
                        mix = st.session_state.baseline.copy()
                        
                        for param in robustness_params:
                            baseline_val = st.session_state.baseline[param]
                            variation_range = baseline_val * (robustness_level / 100)
                            variation = np.random.uniform(-variation_range, variation_range)
                            new_val = np.clip(
                                baseline_val + variation,
                                BOUNDS[param]["min"],
                                BOUNDS[param]["max"]
                            )
                            mix[param] = float(new_val)
                        
                        preds = predict_concrete_properties(
                            composition=mix,
                            model=model,
                            feature_list=features
                        )
                        
                        results_data.append({
                            "Resistance": preds["Resistance"],
                            "Diffusion_Cl": preds["Diffusion_Cl"],
                            "Carbonatation": preds["Carbonatation"]
                        })
                    
                    df_rob = pd.DataFrame(results_data)
                    
                    experiment = {
                        "name": experiment_name,
                        "type": analysis_type,
                        "params": robustness_params,
                        "num_trials": num_trials,
                        "robustness_level": robustness_level,
                        "results_df": df_rob,
                        "baseline": st.session_state.baseline.copy(),
                        "timestamp": datetime.now().isoformat()
                    }
                
                st.session_state.current_experiment = experiment
                st.session_state.experiments.append(experiment)
                
                st.success(f"✅ Terminée !")
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                st.stop()
    
    if st.session_state.current_experiment:
        exp = st.session_state.current_experiment
        
        st.markdown(f"### 📈 {exp['name']}")
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        if exp["type"] == "Analyse de Sensibilité":
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.metric("Paramètre", LABELS_MAP.get(exp['param'], exp['param']))
            with col_m2:
                st.metric("Points", exp['num_points'])
            with col_m3:
                st.metric("Bootstrap", "✅" if exp.get('bootstrap') else "❌")
            
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            
            st.markdown("#### 📊 Courbes")
            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            
            fig_sens = create_sensitivity_chart(
                param_values=exp['param_values'],
                impacts=exp['responses'],
                param_name=LABELS_MAP.get(exp['param'], exp['param']),
                param_unit="kg/m³" if exp['param'] != "Age" else "jours"
            )
            
            st.plotly_chart(fig_sens, use_container_width=True)
            
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            
            st.markdown("#### 🎯 Élasticités")
            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            
            elasticities = {}
            
            for resp_name, resp_values in exp['responses'].items():
                elast = calculate_elasticity(exp['param_values'], resp_values)
                elasticities[resp_name] = elast
            
            cols_elast = st.columns(len(elasticities))
            
            for idx, (resp, elast) in enumerate(elasticities.items()):
                with cols_elast[idx]:
                    if abs(elast) > 1:
                        interp = "Très sensible"
                        color = "#D32F2F"
                    elif abs(elast) > 0.5:
                        interp = "Sensible"
                        color = "#FF9800"
                    elif abs(elast) > 0.1:
                        interp = "Modéré"
                        color = "#1976D2"
                    else:
                        interp = "Peu"
                        color = "#4CAF50"
                    
                    st.markdown(f"""
                    <div style='background: {color}15; padding: 0.9rem; border-radius: 10px; 
                                border-left: 4px solid {color}; text-align: center;'>
                        <div style='font-size: 0.7em; color: #666; font-weight: 600; margin-bottom: 0.3rem;'>
                            {resp}
                        </div>
                        <div style='font-size: 1.8em; font-weight: 700; color: {color}; margin-bottom: 0.3rem;'>
                            {elast:.3f}
                        </div>
                        <div style='font-size: 0.75em; color: #888;'>
                            {interp}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        elif exp["type"] in ["Simulation Monte Carlo", "Plan d'Expériences (DOE)", "Analyse de Robustesse"]:
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.metric("Type", exp['type'])
            with col_m2:
                if "num_simulations" in exp:
                    st.metric("Simulations", exp['num_simulations'])
                elif "num_experiments" in exp:
                    st.metric("Expériences", exp['num_experiments'])
                else:
                    st.metric("Essais", exp['num_trials'])
            
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            
            st.markdown("#### 📊 Statistiques")
            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            
            df = exp["results_df"]
            
            stats_df = df[["Resistance", "Diffusion_Cl", "Carbonatation"]].describe()
            st.dataframe(stats_df, use_container_width=True)
            
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            
            st.markdown("#### 📋 Données")
            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True, hide_index=True, height=350)
        
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        st.markdown("#### 📤 Export")
        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            exp_json = {k: v for k, v in exp.items() if k != "results_df"}
            if "results_df" in exp:
                exp_json["results"] = exp["results_df"].to_dict(orient="records")
            
            st.download_button(
                "📝 JSON",
                data=json.dumps(exp_json, indent=2),
                file_name=f"{exp['name']}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col_exp2:
            if exp["type"] == "Analyse de Sensibilité":
                df_exp = pd.DataFrame({
                    LABELS_MAP.get(exp['param'], exp['param']): exp['param_values'],
                    **exp['responses']
                })
            else:
                df_exp = exp["results_df"]
            
            st.download_button(
                "📊 CSV",
                data=df_exp.to_csv(index=False),
                file_name=f"{exp['name']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp3:
            if st.button("🔄 Nouvelle", use_container_width=True):
                st.session_state.current_experiment = None
                st.rerun()

if st.session_state.experiments:
    st.markdown("---")
    st.markdown("### 📚 Historique")
    
    for idx, exp in enumerate(st.session_state.experiments[-5:]):
        with st.expander(f"📊 {exp['name']}"):
            st.write(f"**Type :** {exp['type']}")
            st.write(f"**Date :** {datetime.fromisoformat(exp['timestamp']).strftime('%d/%m/%Y %H:%M')}")
            
            if st.button("📊 Afficher", key=f"hist_{idx}"):
                st.session_state.current_experiment = exp
                st.rerun()

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.85em;'>
    <strong>Laboratoire v1.0.0</strong> • IMT Nord Europe • © {datetime.now().year}
</div>
""", unsafe_allow_html=True)