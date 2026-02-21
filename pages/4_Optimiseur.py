"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Optimiseur - Algorithme Génétique + CO₂
Fichier: pages/4_Optimiseur.py
Version: 1.1.0 - AVEC OBJECTIF CO₂
═══════════════════════════════════════════════════════════════════════════════

NOUVEAUTÉS v1.1.0:
✅ Nouvel objectif: Minimiser CO₂
✅ Sélection type de ciment
✅ Affichage empreinte optimale
✅ Comparaison impact environnemental
✅ Multi-objectifs (Coût + CO₂)
"""

import streamlit as st
import logging
from datetime import datetime
import time

from config.settings import APP_SETTINGS, OPTIMIZER_SETTINGS
from config.constants import COLOR_PALETTE, MATERIALS_COST_EURO_KG
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import metric_card, info_box
from app.components.charts import plot_composition_pie, plot_performance_radar, plot_cost_breakdown
from app.core.optimizer import optimize_mix, compute_cost
from app.core.validator import validate_formulation

# ✅ IMPORT MODULE CO₂
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from config.co2_database import CEMENT_CO2_KG_PER_TONNE

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Optimiseur - Béton IA",
    page_icon="🎯",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════════

if 'optimization_history' not in st.session_state:
    st.session_state['optimization_history'] = []

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        🎯 Optimiseur - Formulation Optimale (Coût + CO₂)
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Trouvez la formulation idéale selon vos objectifs économiques et environnementaux.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

col_config, col_results = st.columns([1, 1.5], gap="large")

with col_config:
    st.markdown("## ⚙️ Configuration")
    
    # ✅ OBJECTIF (avec CO₂)
    st.markdown("### 🎯 Objectif d'Optimisation")
    
    objective = st.radio(
        "Choisir l'objectif principal",
        options=[
            "Minimiser le Coût",
            "Minimiser l'Empreinte CO₂",  # ✅ NOUVEAU
            "Équilibre Coût/CO₂"           # ✅ NOUVEAU
        ],
        help="L'algorithme optimisera selon ce critère"
    )
    
    if "Coût" in objective and "CO₂" not in objective:
        objective_key = "minimize_cost"
    elif "CO₂" in objective and "Coût" not in objective:
        objective_key = "minimize_co2"  # ✅ NOUVEAU
    else:
        objective_key = "balance_cost_co2"  # ✅ NOUVEAU
    
    # ✅ Type de ciment
    st.markdown("### 🏭 Type de Ciment")
    
    cement_types = list(CEMENT_CO2_KG_PER_TONNE.keys())
    selected_cement = st.selectbox(
        "Choisir le type de ciment",
        options=cement_types,
        index=2,  # CEM II/A-LL par défaut
        help="Impact majeur sur empreinte CO₂"
    )
    
    cement_co2_factor = CEMENT_CO2_KG_PER_TONNE[selected_cement]
    st.caption(f"📊 Facteur : {cement_co2_factor:.1f} kg CO₂/t")
    
    st.markdown("---")
    
    # CONTRAINTES
    st.markdown("### 📊 Contraintes")
    
    target_resistance = st.number_input(
        "Résistance Minimale (MPa)",
        min_value=10.0,
        max_value=90.0,
        value=30.0,
        step=5.0
    )
    
    # ✅ Contrainte CO₂ (optionnelle)
    if objective_key in ["minimize_co2", "balance_cost_co2"]:
        max_co2 = st.number_input(
            "CO₂ Maximum (kg/m³) - Optionnel",
            min_value=0.0,
            max_value=500.0,
            value=0.0,
            step=50.0,
            help="0 = pas de limite"
        )
    else:
        max_co2 = 0.0
    
    st.markdown("---")
    
    # PARAMÈTRES
    with st.expander("🔧 Paramètres Avancés", expanded=False):
        population_size = st.slider("Taille Population", 50, 200, 100, 10)
        num_generations = st.slider("Générations", 20, 100, 50, 10)
        st.caption(f"⏱️ ~{population_size * num_generations * 0.002:.1f}s")
    
    st.markdown("---")
    
    # BOUTON
    optimize_button = st.button("🚀 Lancer l'Optimisation", type="primary", width='stretch')

# ═══════════════════════════════════════════════════════════════════════════════
# RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════

with col_results:
    st.markdown("## 🎯 Résultat Optimal")
    
    if optimize_button:
        with st.spinner("🔄 Optimisation en cours..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                model = st.session_state.get('model')
                features = st.session_state.get('features')
                
                # Simuler progression
                for i in range(10):
                    progress_bar.progress((i + 1) * 10)
                    status_text.text(f"Génération {i+1}/10...")
                    time.sleep(0.1)
                
                start_time = time.time()
                
                # ✅ Optimisation (l'optimizer interne gère déjà minimize_cost et minimize_co2)
                result = optimize_mix(
                    model=model,
                    feature_list=features,
                    target_strength=target_resistance,
                    objective=objective_key if objective_key in ["minimize_cost", "minimize_co2"] else "minimize_cost",
                    random_state=42
                )
                
                elapsed_time = time.time() - start_time
                
                progress_bar.progress(100)
                status_text.text("✅ Optimisation terminée !")
                
                if result is None:
                    st.error(f"❌ Aucune solution trouvée pour R ≥ {target_resistance} MPa")
                    st.info("💡 Suggestions: Réduire résistance cible ou assouplir contraintes")
                else:
                    st.success(f"✅ Solution trouvée en {elapsed_time:.2f}s !")
                    
                    # ✅ CALCUL CO₂
                    co2_calc = CO2Calculator()
                    co2_result = co2_calc.calculate(result.mix, selected_cement)
                    
                    # Stocker
                    st.session_state['optimization_history'].append({
                        'timestamp': datetime.now(),
                        'objective': objective,
                        'target_resistance': target_resistance,
                        'result': result,
                        'co2_result': co2_result,  # ✅ NOUVEAU
                        'cement_type': selected_cement
                    })
                    
                    # ───────────────────────────────────────────────────
                    # COMPOSITION
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("---")
                    st.markdown("### 🧪 Composition Optimale")
                    
                    composition = result.mix
                    predictions = result.targets
                    
                    col_comp1, col_comp2 = st.columns(2)
                    
                    with col_comp1:
                        st.markdown("**Liants**")
                        st.markdown(f"• Ciment : **{composition['Ciment']:.1f}** kg/m³")
                        st.markdown(f"• Laitier : **{composition['Laitier']:.1f}** kg/m³")
                        st.markdown(f"• Cendres : **{composition['CendresVolantes']:.1f}** kg/m³")
                        st.markdown(f"• Eau : **{composition['Eau']:.1f}** kg/m³")
                    
                    with col_comp2:
                        st.markdown("**Granulats**")
                        st.markdown(f"• Gravillons : **{composition['GravilonsGros']:.1f}** kg/m³")
                        st.markdown(f"• Sable : **{composition['SableFin']:.1f}** kg/m³")
                        st.markdown(f"• Superplast. : **{composition['Superplastifiant']:.1f}** kg/m³")
                        st.markdown(f"• Âge : **{composition['Age']:.0f}** j")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # PERFORMANCES
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 📈 Performances")
                    
                    col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)
                    
                    with col_perf1:
                        metric_card("Résistance", predictions['Resistance'], "MPa", "💪", "bon")
                    
                    with col_perf2:
                        metric_card("Diffusion Cl⁻", predictions['Diffusion_Cl'], "×10⁻¹²", "🧂", "bon")
                    
                    with col_perf3:
                        metric_card("Carbonatation", predictions['Carbonatation'], "mm", "🌫️", "bon")
                    
                    with col_perf4:
                        metric_card("Ratio E/L", predictions['Ratio_E_L'], "", "💧", "bon")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # ✅ ÉCONOMIE + ÉCOLOGIE
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 💰 Économie + 🌍 Écologie")
                    
                    col_eco1, col_eco2, col_eco3 = st.columns(3)
                    
                    with col_eco1:
                        st.metric("💰 Coût Total", f"{result.cost:.2f} €/m³")
                    
                    with col_eco2:
                        # ✅ CO₂
                        co2_total = co2_result.co2_total_kg_m3
                        classe_co2, emoji, _ = get_environmental_grade(co2_total)
                        st.metric("🌍 Empreinte CO₂", f"{co2_total:.1f} kg/m³")
                        st.caption(f"{emoji} Classe: **{classe_co2}**")
                    
                    with col_eco3:
                        # Ratio €/CO₂
                        ratio_cost_co2 = result.cost / co2_total if co2_total > 0 else 0
                        st.metric("📊 Ratio €/CO₂", f"{ratio_cost_co2:.3f}")
                        st.caption("Plus faible = meilleur")
                    
                    # Détails
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        with st.expander("💰 Détail Coûts"):
                            for mat in ['Ciment', 'Laitier', 'CendresVolantes', 'Superplastifiant', 'GravilonsGros', 'SableFin']:
                                qty = composition.get(mat, 0)
                                if qty > 0:
                                    cost_mat = qty * MATERIALS_COST_EURO_KG.get(mat, 0)
                                    st.markdown(f"• {mat}: {cost_mat:.2f} €/m³")
                    
                    with col_detail2:
                        with st.expander("🌍 Détail CO₂"):
                            breakdown = co2_calc.get_breakdown_percentages(co2_result)
                            for const, percent in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                                if percent > 1:
                                    co2_val = getattr(co2_result, f'co2_{const.lower()}', 0)
                                    st.markdown(f"• {const}: {co2_val:.1f} kg ({percent:.0f}%)")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # VALIDATION
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 🔍 Validation")
                    
                    validation = validate_formulation(composition, predictions)
                    
                    col_val1, col_val2, col_val3 = st.columns(3)
                    
                    with col_val1:
                        score = validation.compliance_score
                        color = "🟢" if score >= 80 else "🟡"
                        st.metric("Conformité", f"{color} {score:.0f}/100")
                    
                    with col_val2:
                        st.metric("Classe R", validation.resistance_class or "N/A")
                    
                    with col_val3:
                        st.metric("Classe Exp", validation.exposure_class or "N/A")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # VISUALISATIONS
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 📊 Visualisations")
                    
                    tab_pie, tab_cost, tab_co2, tab_radar = st.tabs(["Composition", "Coûts", "🌍 CO₂", "Performance"])
                    
                    with tab_pie:
                        fig_pie = plot_composition_pie(composition)
                        st.plotly_chart(fig_pie, width='stretch')
                    
                    with tab_cost:
                        fig_cost = plot_cost_breakdown(composition)
                        st.plotly_chart(fig_cost, width='stretch')
                    
                    # ✅ NOUVEAU : Tab CO₂
                    with tab_co2:
                        import plotly.graph_objects as go
                        
                        breakdown = co2_calc.get_breakdown_percentages(co2_result)
                        filtered = {k: v for k, v in breakdown.items() if v > 1}
                        
                        fig_co2_pie = go.Figure(data=[go.Pie(
                            labels=list(filtered.keys()),
                            values=list(filtered.values()),
                            hole=0.4,
                            marker=dict(colors=['#e74c3c', '#3498db', '#2ecc71', '#f39c12'])
                        )])
                        
                        fig_co2_pie.update_layout(title=f"Répartition CO₂ - {co2_total:.1f} kg/m³", height=400)
                        st.plotly_chart(fig_co2_pie, width='stretch')
                    
                    with tab_radar:
                        fig_radar = plot_performance_radar(predictions, name="Solution Optimale")
                        st.plotly_chart(fig_radar, width='stretch')
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # ACTIONS
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### ⚡ Actions")
                    
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    with col_act1:
                        if st.button("💾 Sauvegarder", width='stretch'):
                            db = st.session_state.get('db_manager')
                            if db and db.is_connected:
                                success = db.save_prediction(
                                    composition, predictions,
                                    f"Optimisée_{objective_key}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                                )
                                if success:
                                    st.toast("✅ Sauvegardée !", icon="💾")
                            else:
                                st.warning("DB non connectée")
                    
                    with col_act2:
                        if st.button("📊 Vers Formulateur", width='stretch'):
                            st.session_state['imported_composition'] = composition
                            st.toast("✅ Exportée", icon="📊")
                    
                    with col_act3:
                        import pandas as pd
                        export_data = {**composition, **predictions, 'CO2_kg_m3': co2_total, 'Cement_Type': selected_cement}
                        df = pd.DataFrame([export_data])
                        csv = df.to_csv(index=False)
                        
                        st.download_button(
                            "📥 CSV",
                            data=csv,
                            file_name=f"optimal_{objective_key}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            width='stretch'
                        )
            
            except Exception as e:
                logger.error(f"Erreur: {e}", exc_info=True)
                st.error(f"❌ Erreur : {e}")
    
    else:
        info_box(
            "Mode d'emploi",
            """
            1. **Choisissez** objectif (Coût / CO₂ / Équilibre)
            2. **Sélectionnez** type de ciment
            3. **Définissez** contraintes (résistance min, CO₂ max)
            4. **Lancez** l'optimisation
            
            **Nouveau** : Optimisation empreinte carbone !
            """,
            icon="ℹ️",
            color="info"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state['optimization_history']:
    st.markdown("---")
    st.markdown("## 🕐 Historique")
    
    for opt in reversed(st.session_state['optimization_history'][-5:]):
        with st.expander(f"{opt['timestamp'].strftime('%Y-%m-%d %H:%M')} - {opt['objective']}", expanded=False):
            result = opt['result']
            co2_res = opt.get('co2_result')
            
            col_h1, col_h2, col_h3, col_h4 = st.columns(4)
            
            with col_h1:
                st.metric("R", f"{result.targets['Resistance']:.1f} MPa")
            with col_h2:
                st.metric("Coût", f"{result.cost:.2f} €")
            with col_h3:
                if co2_res:
                    st.metric("CO₂", f"{co2_res.co2_total_kg_m3:.1f} kg")
            with col_h4:
                st.caption(f"Ciment: {opt.get('cement_type', 'N/A')}")

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("🌍 **Nouveau** : Optimisation empreinte CO₂ | 💡 CEM III/B recommandé pour béton bas-carbone")