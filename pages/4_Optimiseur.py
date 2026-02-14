"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Optimiseur - Algorithme Génétique
Fichier: app/pages/4_Optimiseur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
- Sélection objectif (Coût / CO₂)
- Contrainte résistance minimale
- Algorithme génétique (Optuna)
- Affichage résultat optimal
- Historique optimisations
"""

import streamlit as st
import logging
from datetime import datetime
import time

from config.settings import APP_SETTINGS, OPTIMIZER_SETTINGS
from config.constants import COLOR_PALETTE, MATERIALS_COST_EURO_KG, CO2_EMISSIONS_KG
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import metric_card, info_box
from app.components.charts import plot_composition_pie, plot_performance_radar, plot_cost_breakdown
from app.core.optimizer import optimize_mix, compute_cost, compute_co2
from app.core.validator import validate_formulation

from app.core.session_manager import initialize_session

# Charge tout ce qu'il faut
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
# INITIALISATION SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

if 'optimization_history' not in st.session_state:
    st.session_state['optimization_history'] = []

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        🎯 Optimiseur - Recherche de Formulation Optimale
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Trouvez la formulation idéale selon vos objectifs et contraintes avec l'algorithme génétique.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION OPTIMISATION
# ═══════════════════════════════════════════════════════════════════════════════

col_config, col_results = st.columns([1, 1.5], gap="large")

with col_config:
    st.markdown("## ⚙️ Configuration")
    
    # ───────────────────────────────────────────────────────────────
    # OBJECTIF
    # ───────────────────────────────────────────────────────────────
    
    st.markdown("### 🎯 Objectif d'Optimisation")
    
    objective = st.radio(
        "Choisir l'objectif principal",
        options=["Minimiser le Coût", "Minimiser l'Empreinte CO₂"],
        help="L'algorithme cherchera à minimiser ce critère"
    )
    
    objective_key = "minimize_cost" if "Coût" in objective else "minimize_co2"
    
    st.markdown("---")
    
    # ───────────────────────────────────────────────────────────────
    # CONTRAINTES
    # ───────────────────────────────────────────────────────────────
    
    st.markdown("### 📊 Contraintes")
    
    target_resistance = st.number_input(
        "Résistance Minimale (MPa)",
        min_value=10.0,
        max_value=90.0,
        value=30.0,
        step=5.0,
        help="Résistance minimale requise à 28 jours"
    )
    
    st.markdown("---")
    
    # ───────────────────────────────────────────────────────────────
    # PARAMÈTRES ALGORITHME
    # ───────────────────────────────────────────────────────────────
    
    with st.expander("🔧 Paramètres Avancés", expanded=False):
        st.markdown("#### Algorithme Génétique")
        
        population_size = st.slider(
            "Taille Population",
            min_value=50,
            max_value=200,
            value=OPTIMIZER_SETTINGS['genetic_algorithm']['population_size'],
            step=10
        )
        
        num_generations = st.slider(
            "Nombre Générations",
            min_value=20,
            max_value=100,
            value=OPTIMIZER_SETTINGS['genetic_algorithm']['num_generations'],
            step=10
        )
        
        st.caption(f"⏱️ Temps estimé : ~{population_size * num_generations * 0.002:.1f}s")
    
    st.markdown("---")
    
    # ───────────────────────────────────────────────────────────────
    # BOUTON OPTIMISATION
    # ───────────────────────────────────────────────────────────────
    
    optimize_button = st.button(
        "🚀 Lancer l'Optimisation",
        type="primary",
        width="stretch"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════

with col_results:
    st.markdown("## 🎯 Résultat Optimal")
    
    if optimize_button:
        with st.spinner("🔄 Optimisation en cours..."):
            
            # Barre de progression
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
                
                # Lancer optimisation
                start_time = time.time()
                
                result = optimize_mix(
                    model=model,
                    feature_list=features,
                    target_strength=target_resistance,
                    objective=objective_key,
                    random_state=42
                )
                
                elapsed_time = time.time() - start_time
                
                progress_bar.progress(100)
                status_text.text("✅ Optimisation terminée !")
                
                if result is None:
                    st.error(
                        "❌ **Aucune solution trouvée**  \n\n"
                        f"Impossible d'atteindre {target_resistance} MPa avec les contraintes actuelles.  \n"
                        "**Suggestions** :  \n"
                        "- Réduire la résistance cible  \n"
                        "- Assouplir les contraintes  \n"
                        "- Augmenter le nombre de générations"
                    )
                else:
                    st.success(f"✅ Solution optimale trouvée en {elapsed_time:.2f}s !")
                    
                    # Stocker dans historique
                    st.session_state['optimization_history'].append({
                        'timestamp': datetime.now(),
                        'objective': objective,
                        'target_resistance': target_resistance,
                        'result': result
                    })
                    
                    # ───────────────────────────────────────────────────
                    # AFFICHAGE SOLUTION
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("---")
                    st.markdown("### 🧪 Composition Optimale")
                    
                    composition = result.mix
                    predictions = result.targets
                    
                    # Tableau composition
                    col_comp1, col_comp2 = st.columns(2)
                    
                    with col_comp1:
                        st.markdown("**Liants**")
                        st.markdown(f"• Ciment : **{composition['Ciment']:.1f}** kg/m³")
                        st.markdown(f"• Laitier : **{composition['Laitier']:.1f}** kg/m³")
                        st.markdown(f"• Cendres : **{composition['CendresVolantes']:.1f}** kg/m³")
                        st.markdown(f"• Eau : **{composition['Eau']:.1f}** kg/m³")
                    
                    with col_comp2:
                        st.markdown("**Granulats & Adjuvants**")
                        st.markdown(f"• Gravillons : **{composition['GravilonsGros']:.1f}** kg/m³")
                        st.markdown(f"• Sable : **{composition['SableFin']:.1f}** kg/m³")
                        st.markdown(f"• Superplast. : **{composition['Superplastifiant']:.1f}** kg/m³")
                        st.markdown(f"• Âge : **{composition['Age']:.0f}** jours")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # PERFORMANCES
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 📈 Performances Prédites")
                    
                    col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)
                    
                    with col_perf1:
                        metric_card(
                            title="Résistance",
                            value=predictions['Resistance'],
                            unit="MPa",
                            icon="💪",
                            quality_grade="bon" if predictions['Resistance'] >= target_resistance else "moyen"
                        )
                    
                    with col_perf2:
                        metric_card(
                            title="Diffusion Cl⁻",
                            value=predictions['Diffusion_Cl'],
                            unit="×10⁻¹²",
                            icon="🧂",
                            quality_grade="excellent" if predictions['Diffusion_Cl'] < 5 else "bon"
                        )
                    
                    with col_perf3:
                        metric_card(
                            title="Carbonatation",
                            value=predictions['Carbonatation'],
                            unit="mm",
                            icon="🌫️",
                            quality_grade="excellent" if predictions['Carbonatation'] < 10 else "bon"
                        )
                    
                    with col_perf4:
                        metric_card(
                            title="Ratio E/L",
                            value=predictions['Ratio_E_L'],
                            unit="",
                            icon="💧",
                            quality_grade="excellent" if predictions['Ratio_E_L'] < 0.5 else "bon"
                        )
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # ÉCONOMIE & ÉCOLOGIE
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 💰 Économie & Écologie")
                    
                    col_eco1, col_eco2 = st.columns(2)
                    
                    with col_eco1:
                        st.metric(
                            "💰 Coût Total",
                            f"{result.cost:.2f} €/m³"
                        )
                        
                        # Détails coûts
                        with st.expander("Détail des Coûts"):
                            for material in ['Ciment', 'Laitier', 'CendresVolantes', 
                                           'Superplastifiant', 'GravilonsGros', 'SableFin']:
                                qty = composition.get(material, 0)
                                if qty > 0:
                                    cost_mat = qty * MATERIALS_COST_EURO_KG.get(material, 0)
                                    st.markdown(f"• {material} : {cost_mat:.2f} €/m³")
                    
                    with col_eco2:
                        st.metric(
                            "🌱 Empreinte CO₂",
                            f"{result.co2:.1f} kg/m³"
                        )
                        
                        # Détails CO₂
                        with st.expander("Détail Émissions"):
                            for material in ['Ciment', 'Laitier', 'CendresVolantes', 
                                           'Superplastifiant', 'GravilonsGros', 'SableFin']:
                                qty = composition.get(material, 0)
                                if qty > 0:
                                    co2_mat = qty * CO2_EMISSIONS_KG.get(material, 0)
                                    st.markdown(f"• {material} : {co2_mat:.1f} kg CO₂/m³")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # VALIDATION
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 🔍 Validation Normative")
                    
                    validation = validate_formulation(
                        composition=composition,
                        predictions=predictions
                    )
                    
                    col_val1, col_val2, col_val3 = st.columns(3)
                    
                    with col_val1:
                        score = validation.compliance_score
                        color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
                        st.metric("Score Conformité", f"{color} {score:.0f}/100")
                    
                    with col_val2:
                        st.metric("Classe Résistance", validation.resistance_class or "N/A")
                    
                    with col_val3:
                        st.metric("Classe Exposition", validation.exposure_class or "N/A")
                    
                    # Alertes
                    if validation.alerts:
                        with st.expander(f"⚠️ {len(validation.alerts)} Alerte(s)", expanded=False):
                            for alert in validation.alerts[:3]:
                                st.warning(f"{alert.category} : {alert.message}")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # VISUALISATIONS
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### 📊 Visualisations")
                    
                    tab_pie, tab_cost, tab_radar = st.tabs([
                        "Composition",
                        "Coûts",
                        "Performance"
                    ])
                    
                    with tab_pie:
                        fig_pie = plot_composition_pie(composition)
                        st.plotly_chart(fig_pie, width="stretch")
                    
                    with tab_cost:
                        fig_cost = plot_cost_breakdown(composition)
                        st.plotly_chart(fig_cost, width="stretch")
                    
                    with tab_radar:
                        fig_radar = plot_performance_radar(predictions, name="Solution Optimale")
                        st.plotly_chart(fig_radar, width="stretch")
                    
                    st.markdown("---")
                    
                    # ───────────────────────────────────────────────────
                    # ACTIONS
                    # ───────────────────────────────────────────────────
                    
                    st.markdown("### ⚡ Actions")
                    
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    with col_act1:
                        if st.button("💾 Sauvegarder", width="stretch"):
                            db_manager = st.session_state.get('db_manager')
                            if db_manager:
                                success = db_manager.save_prediction(
                                    formulation=composition,
                                    predictions=predictions,
                                    formulation_name=f"Optimisée_{objective_key}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                                )
                                if success:
                                    st.toast("✅ Sauvegardée !", icon="💾")
                            else:
                                st.warning("DB non connectée")
                    
                    with col_act2:
                        if st.button("📊 Vers Formulateur", width="stretch"):
                            # Stocker composition pour utilisation dans Formulateur
                            st.session_state['imported_composition'] = composition
                            st.toast("✅ Composition exportée vers Formulateur", icon="📊")
                    
                    with col_act3:
                        # Export CSV
                        import pandas as pd
                        export_data = {**composition, **predictions}
                        df_export = pd.DataFrame([export_data])
                        csv = df_export.to_csv(index=False)
                        
                        st.download_button(
                            "📥 Export CSV",
                            data=csv,
                            file_name=f"optimal_{objective_key}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            width="stretch"
                        )
            
            except Exception as e:
                logger.error(f"Erreur optimisation: {e}", exc_info=True)
                st.error(f"❌ Erreur : {e}")
    
    else:
        info_box(
            "Mode d'emploi",
            """
            1. **Choisissez** votre objectif (Coût ou CO₂)
            2. **Définissez** la résistance minimale requise
            3. **Ajustez** les paramètres avancés si nécessaire
            4. **Cliquez** sur "🚀 Lancer l'Optimisation"
            
            L'algorithme génétique explorera l'espace des solutions
            pour trouver la formulation optimale respectant vos contraintes.
            
            ⏱️ Temps moyen : 5-15 secondes
            """,
            icon="ℹ️",
            color="info"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state['optimization_history']:
    st.markdown("---")
    st.markdown("## 🕐 Historique des Optimisations")
    
    for i, opt in enumerate(reversed(st.session_state['optimization_history'][-5:])):
        with st.expander(
            f"{opt['timestamp'].strftime('%Y-%m-%d %H:%M')} - {opt['objective']} "
            f"(R ≥ {opt['target_resistance']} MPa)",
            expanded=False
        ):
            result = opt['result']
            
            col_h1, col_h2, col_h3 = st.columns(3)
            
            with col_h1:
                st.metric("Résistance", f"{result.targets['Resistance']:.1f} MPa")
            
            with col_h2:
                st.metric("Coût", f"{result.cost:.2f} €/m³")
            
            with col_h3:
                st.metric("CO₂", f"{result.co2:.1f} kg/m³")

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("💡 **Astuce** : Pour un béton économique, minimisez le coût. Pour un béton écologique, minimisez le CO₂.")