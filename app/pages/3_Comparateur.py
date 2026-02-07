"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: 3_Comparateur.py - VERSION 1.0 PRODUCTION
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════

FONCTIONNALITÉS :
✅ Comparaison côte-à-côte de 2-4 formulations
✅ Graphiques radar + barres + scatter
✅ Tableau comparatif détaillé
✅ Export multi-formulations
✅ Recommandations automatiques
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))
from app.components.navbar import render_top_nav
from app.styles.theme import apply_custom_theme
from app.core.predictor import predict_concrete_properties, get_default_features
from config.constants import BOUNDS, PRESET_FORMULATIONS
from config.settings import UI_SETTINGS

st.set_page_config(
    page_title="Comparateur - IMT Nord Europe",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_theme()
render_top_nav(active_page="comparateur")

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
            return None, get_default_features(), {
                "model_name": "Simulation",
                "performance": {"Resistance": 0.85}
            }, "simulation"

model, features, metadata, model_status = load_ml_model()

if 'comparateur_v1' not in st.session_state:
    st.session_state.comparateur_v1 = True
    st.session_state.formulations = []
    st.session_state.comparisons = []

st.markdown(f"""
<div style='background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
            padding: 1.8rem 2rem; border-radius: 15px; margin-bottom: 2rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div>
            <h1 style='color: white; margin: 0; font-size: 2em;'>
                📊 Comparateur Multi-Formulations v1.0
            </h1>
            <p style='color: rgba(255,255,255,0.9); font-size: 1em; margin-top: 0.4rem;'>
                Analyse comparative avancée de formulations béton
            </p>
        </div>
        <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; border-radius: 10px;'>
            <div style='color: white; font-weight: 600; font-size: 0.8em;'>
                {len(st.session_state.formulations)} FORMULATIONS
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1.3, 1.7], gap="large")

with col_left:
    st.markdown("### 🎯 Gestion des Formulations")
    
    st.markdown("#### ➕ Ajouter une Formulation")
    
    add_method = st.radio(
        "Méthode :",
        options=["Preset", "Personnalisée"],
        horizontal=True,
        key="add_method"
    )
    
    if add_method == "Preset":
        selected_preset = st.selectbox(
            "Choisir un preset :",
            options=list(PRESET_FORMULATIONS.keys()),
            key="preset_add"
        )
        
        formulation_name = st.text_input(
            "Nom de la formulation :",
            value=selected_preset,
            key="form_name_preset"
        )
        
        if st.button("✅ Ajouter ce Preset", use_container_width=True):
            preset = PRESET_FORMULATIONS[selected_preset]
            
            formulation = {
                "name": formulation_name,
                "composition": {key: float(preset[key]) for key in BOUNDS.keys() if key in preset},
                "source": "preset",
                "timestamp": datetime.now().isoformat()
            }
            
            st.session_state.formulations.append(formulation)
            st.success(f"✅ '{formulation_name}' ajoutée !")
            st.rerun()
    
    else:
        formulation_name = st.text_input(
            "Nom :",
            value=f"Custom_{len(st.session_state.formulations)+1}",
            key="form_name_custom"
        )
        
        with st.expander("⚙️ Configuration Composition", expanded=True):
            custom_composition = {}
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                custom_composition["Ciment"] = st.number_input(
                    "Ciment (kg/m³)",
                    min_value=float(BOUNDS["Ciment"]["min"]),
                    max_value=float(BOUNDS["Ciment"]["max"]),
                    value=280.0,
                    step=10.0,
                    key="custom_ciment"
                )
                
                custom_composition["Eau"] = st.number_input(
                    "Eau (L/m³)",
                    min_value=float(BOUNDS["Eau"]["min"]),
                    max_value=float(BOUNDS["Eau"]["max"]),
                    value=180.0,
                    step=5.0,
                    key="custom_eau"
                )
                
                custom_composition["GravilonsGros"] = st.number_input(
                    "Gravillons (kg/m³)",
                    min_value=float(BOUNDS["GravilonsGros"]["min"]),
                    max_value=float(BOUNDS["GravilonsGros"]["max"]),
                    value=1100.0,
                    step=10.0,
                    key="custom_grav"
                )
                
                custom_composition["Age"] = st.number_input(
                    "Âge (jours)",
                    min_value=float(BOUNDS["Age"]["min"]),
                    max_value=float(BOUNDS["Age"]["max"]),
                    value=28.0,
                    step=1.0,
                    key="custom_age"
                )
            
            with col_c2:
                custom_composition["Laitier"] = st.number_input(
                    "Laitier (kg/m³)",
                    min_value=float(BOUNDS["Laitier"]["min"]),
                    max_value=float(BOUNDS["Laitier"]["max"]),
                    value=0.0,
                    step=10.0,
                    key="custom_laitier"
                )
                
                custom_composition["CendresVolantes"] = st.number_input(
                    "Cendres (kg/m³)",
                    min_value=float(BOUNDS["CendresVolantes"]["min"]),
                    max_value=float(BOUNDS["CendresVolantes"]["max"]),
                    value=0.0,
                    step=10.0,
                    key="custom_cendres"
                )
                
                custom_composition["SableFin"] = st.number_input(
                    "Sable (kg/m³)",
                    min_value=float(BOUNDS["SableFin"]["min"]),
                    max_value=float(BOUNDS["SableFin"]["max"]),
                    value=750.0,
                    step=10.0,
                    key="custom_sable"
                )
                
                custom_composition["Superplastifiant"] = st.number_input(
                    "SP (kg/m³)",
                    min_value=float(BOUNDS["Superplastifiant"]["min"]),
                    max_value=float(BOUNDS["Superplastifiant"]["max"]),
                    value=0.0,
                    step=0.5,
                    key="custom_sp"
                )
        
        if st.button("✅ Ajouter Personnalisée", use_container_width=True):
            formulation = {
                "name": formulation_name,
                "composition": custom_composition,
                "source": "custom",
                "timestamp": datetime.now().isoformat()
            }
            
            st.session_state.formulations.append(formulation)
            st.success(f"✅ '{formulation_name}' ajoutée !")
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### 📋 Formulations Actives")
    
    if st.session_state.formulations:
        for idx, form in enumerate(st.session_state.formulations):
            col_form1, col_form2 = st.columns([3, 1])
            
            with col_form1:
                st.markdown(f"""
                <div style='background: #E3F2FD; padding: 0.6rem; border-radius: 6px; 
                            border-left: 3px solid #1976D2; margin-bottom: 0.5rem;'>
                    <div style='font-weight: 600; color: #1976D2;'>{form['name']}</div>
                    <div style='font-size: 0.8em; color: #666;'>
                        Source: {form['source']} • {datetime.fromisoformat(form['timestamp']).strftime('%d/%m %H:%M')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_form2:
                if st.button("🗑️", key=f"del_{idx}", use_container_width=True):
                    st.session_state.formulations.pop(idx)
                    st.rerun()
        
        st.markdown("---")
        
        if st.button("🔬 Lancer la Comparaison", type="primary", use_container_width=True, disabled=(len(st.session_state.formulations) < 2)):
            with st.spinner("🔬 Calcul des prédictions..."):
                comparison_results = []
                
                for form in st.session_state.formulations:
                    try:
                        if model is not None:
                            preds = predict_concrete_properties(
                                composition=form["composition"],
                                model=model,
                                feature_list=features
                            )
                        else:
                            from app.core.predictor import simulate_prediction
                            preds = simulate_prediction(form["composition"])
                        
                        comparison_results.append({
                            "name": form["name"],
                            "composition": form["composition"],
                            "predictions": preds
                        })
                    
                    except Exception as e:
                        st.error(f"❌ Erreur {form['name']}: {str(e)}")
                
                if comparison_results:
                    st.session_state.comparisons = comparison_results
                    st.success(f"✅ Comparaison de {len(comparison_results)} formulations OK !")
                    st.rerun()
    
    else:
        st.info("Aucune formulation. Ajoutez-en au moins 2 pour comparer.")

with col_right:
    if not st.session_state.comparisons:
        st.markdown("""
        <div style='text-align: center; padding: 5rem 2rem; background: #FAFAFA; 
                    border-radius: 12px; border: 2px dashed #E0E0E0;'>
            <div style='font-size: 4.5em; margin-bottom: 1rem;'>📊</div>
            <h2 style='color: #1976D2; margin-bottom: 1rem;'>Comparateur</h2>
            <p style='color: #666; font-size: 1rem; line-height: 1.6; max-width: 450px; margin: 0 auto;'>
                Ajoutez au moins <strong>2 formulations</strong> puis cliquez sur 
                <strong>"🔬 Lancer la Comparaison"</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.stop()
    
    comps = st.session_state.comparisons
    
    st.markdown("### 📈 Résultats Comparatifs")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    # GRAPHIQUE RADAR
    st.markdown("#### 🎯 Graphique Radar")
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    
    fig_radar = go.Figure()
    
    categories = ["Résistance", "Diffusion Cl⁻", "Carbonatation"]
    
    for comp in comps:
        preds = comp["predictions"]
        
        # Normalisation pour le radar
        values = [
            preds["Resistance"] / 80,  # Normalisé sur 80 MPa
            1 - (preds["Diffusion_Cl"] / 20),  # Inversé (moins = mieux)
            1 - (preds["Carbonatation"] / 20)  # Inversé
        ]
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=comp["name"]
        ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
    
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # GRAPHIQUES BARRES
    st.markdown("#### 📊 Comparaison par Indicateur")
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    
    col_bar1, col_bar2, col_bar3 = st.columns(3)
    
    with col_bar1:
        df_res = pd.DataFrame({
            "Formulation": [c["name"] for c in comps],
            "Résistance": [c["predictions"]["Resistance"] for c in comps]
        })
        
        fig_res = px.bar(
            df_res,
            x="Formulation",
            y="Résistance",
            title="Résistance (MPa)",
            color="Résistance",
            color_continuous_scale="Blues"
        )
        fig_res.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_res, use_container_width=True)
    
    with col_bar2:
        df_diff = pd.DataFrame({
            "Formulation": [c["name"] for c in comps],
            "Diffusion": [c["predictions"]["Diffusion_Cl"] for c in comps]
        })
        
        fig_diff = px.bar(
            df_diff,
            x="Formulation",
            y="Diffusion",
            title="Diffusion Cl⁻",
            color="Diffusion",
            color_continuous_scale="Purples"
        )
        fig_diff.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_diff, use_container_width=True)
    
    with col_bar3:
        df_carb = pd.DataFrame({
            "Formulation": [c["name"] for c in comps],
            "Carbonatation": [c["predictions"]["Carbonatation"] for c in comps]
        })
        
        fig_carb = px.bar(
            df_carb,
            x="Formulation",
            y="Carbonatation",
            title="Carbonatation (mm)",
            color="Carbonatation",
            color_continuous_scale="Oranges"
        )
        fig_carb.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_carb, use_container_width=True)
    
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # TABLEAU COMPARATIF
    st.markdown("#### 📋 Tableau Comparatif Détaillé")
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    
    comparison_data = []
    
    for comp in comps:
        row = {
            "Formulation": comp["name"],
            "Résistance (MPa)": f"{comp['predictions']['Resistance']:.1f}",
            "Diffusion Cl⁻": f"{comp['predictions']['Diffusion_Cl']:.3f}",
            "Carbonatation (mm)": f"{comp['predictions']['Carbonatation']:.1f}",
            "Ratio E/L": f"{comp['predictions']['Ratio_E_L']:.3f}",
            "Liant (kg/m³)": f"{comp['predictions']['Liant_Total']:.0f}",
            "Substitution (%)": f"{comp['predictions']['Pct_Substitution']*100:.1f}"
        }
        comparison_data.append(row)
    
    df_comp = pd.DataFrame(comparison_data)
    
    st.dataframe(df_comp, use_container_width=True, hide_index=True, height=250)
    
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # RECOMMANDATIONS
    st.markdown("#### 💡 Recommandations Automatiques")
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    
    # Meilleure résistance
    best_resistance = max(comps, key=lambda x: x["predictions"]["Resistance"])
    
    # Meilleure durabilité (diffusion + carbonatation)
    best_durability = min(comps, key=lambda x: x["predictions"]["Diffusion_Cl"] + x["predictions"]["Carbonatation"])
    
    # Meilleur ratio E/L
    best_el = min(comps, key=lambda x: x["predictions"]["Ratio_E_L"])
    
    col_rec1, col_rec2, col_rec3 = st.columns(3)
    
    with col_rec1:
        st.markdown(f"""
        <div style='background: #E8F5E9; padding: 1rem; border-radius: 8px; 
                    border-left: 4px solid #4CAF50;'>
            <div style='font-weight: 600; color: #4CAF50; margin-bottom: 0.5rem;'>
                🏆 Meilleure Résistance
            </div>
            <div style='font-size: 1.2em; font-weight: 700; color: #2E7D32;'>
                {best_resistance["name"]}
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 0.3rem;'>
                {best_resistance["predictions"]["Resistance"]:.1f} MPa
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_rec2:
        st.markdown(f"""
        <div style='background: #E3F2FD; padding: 1rem; border-radius: 8px; 
                    border-left: 4px solid #1976D2;'>
            <div style='font-weight: 600; color: #1976D2; margin-bottom: 0.5rem;'>
                🛡️ Meilleure Durabilité
            </div>
            <div style='font-size: 1.2em; font-weight: 700; color: #0D47A1;'>
                {best_durability["name"]}
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 0.3rem;'>
                Diffusion + Carb minimisés
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_rec3:
        st.markdown(f"""
        <div style='background: #FFF3E0; padding: 1rem; border-radius: 8px; 
                    border-left: 4px solid #FF9800;'>
            <div style='font-weight: 600; color: #FF9800; margin-bottom: 0.5rem;'>
                ⚡ Meilleur Ratio E/L
            </div>
            <div style='font-size: 1.2em; font-weight: 700; color: #E65100;'>
                {best_el["name"]}
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 0.3rem;'>
                E/L = {best_el["predictions"]["Ratio_E_L"]:.3f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    # EXPORT
    st.markdown("#### 📤 Export Multi-Formulations")
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "num_formulations": len(comps),
            "formulations": comps
        }
        
        st.download_button(
            "📝 JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"comparaison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_exp2:
        st.download_button(
            "📊 CSV",
            data=df_comp.to_csv(index=False),
            file_name=f"comparaison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_exp3:
        if st.button("🔄 Nouvelle Comparaison", use_container_width=True):
            st.session_state.formulations = []
            st.session_state.comparisons = []
            st.rerun()

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.85em;'>
    <strong>Comparateur v1.0</strong> • IMT Nord Europe • © {datetime.now().year}
</div>
""", unsafe_allow_html=True)