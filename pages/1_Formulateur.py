"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Formulateur - Prédiction des Propriétés du Béton
Fichier: pages/1_Formulateur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.2.0 - AVEC MODULE CO₂
═══════════════════════════════════════════════════════════════════════════════

NOUVEAUTÉS v1.2.0:
✅ Calcul empreinte CO₂ automatique
✅ Sélection type de ciment
✅ Classe environnementale
✅ Suggestions réduction CO₂
✅ Graphiques impact carbone
"""

import psycopg2
import streamlit as st
import logging
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.forms import render_formulation_input
from app.components.cards import metric_card, alert_banner, info_box
from app.components.charts import plot_composition_pie, plot_performance_radar
from app.core.predictor import predict_concrete_properties
from app.core.validator import validate_formulation

# ✅ IMPORT MODULE CO₂
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from config.co2_database import CEMENT_CO2_KG_PER_TONNE

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Formulateur - Béton IA",
    page_icon="📊",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION COMPTEURS
# ═══════════════════════════════════════════════════════════════════════════════

if 'prediction_count' not in st.session_state:
    st.session_state['prediction_count'] = 0

if 'total_saves' not in st.session_state:
    st.session_state['total_saves'] = 0

if 'favorites' not in st.session_state:
    st.session_state['favorites'] = []

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        📊 Formulateur - Prédiction des Propriétés + CO₂
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Saisissez votre composition et obtenez les prédictions ML + empreinte carbone.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

col_input, col_results = st.columns([1, 1], gap="large")

# ─────────────────────────────────────────────────────────────────────
# COLONNE GAUCHE : SAISIE
# ─────────────────────────────────────────────────────────────────────

with col_input:
    st.markdown("## ⚗️ Composition du Béton")
    
    # Formulaire de saisie
    composition = render_formulation_input(
        key_suffix="formulateur",
        layout="expanded",
        show_presets=True
    )
    
    st.markdown("---")
    
    # ✅ NOUVEAU : Sélection type de ciment
    st.markdown("### 🏭 Type de Ciment")
    
    cement_types = list(CEMENT_CO2_KG_PER_TONNE.keys())
    
    selected_cement = st.selectbox(
        "Choisir le type de ciment",
        options=cement_types,
        index=0,  # CEM I par défaut
        help="Le type de ciment impacte directement l'empreinte carbone"
    )
    
    # Afficher facteur CO₂ du ciment choisi
    cement_co2_factor = CEMENT_CO2_KG_PER_TONNE[selected_cement]
    st.caption(f"📊 Facteur CO₂ : {cement_co2_factor:.1f} kg CO₂/tonne")
    
    st.markdown("---")
    
    # Nom formulation
    formulation_name = st.text_input(
        label="📝 Nom de la Formulation",
        value=f"Formulation_{datetime.now().strftime('%Y%m%d_%H%M')}",
        max_chars=100
    )
    
    # Bouton prédiction
    predict_button = st.button(
        label="🚀 Lancer la Prédiction + CO₂",
        type="primary",
        width='stretch'
    )

# ─────────────────────────────────────────────────────────────────────
# COLONNE DROITE : RÉSULTATS
# ─────────────────────────────────────────────────────────────────────

with col_results:
    st.markdown("## 🎯 Résultats")
    
    # ═══════════════════════════════════════════════════════════════
    # DÉCLENCHEMENT PRÉDICTION
    # ═══════════════════════════════════════════════════════════════
    
    if predict_button:
        with st.spinner("🔄 Calcul en cours..."):
            try:
                model = st.session_state.get('model')
                features = st.session_state.get('features')
                
                if not model or not features:
                    st.error("❌ Modèle non chargé. Redémarrez l'application.")
                    st.stop()
                
                # 1. Prédiction ML
                predictions = predict_concrete_properties(
                    composition=composition,
                    model=model,
                    feature_list=features,
                    validate=True
                )
                
                # ✅ 2. CALCUL CO₂
                co2_calc = CO2Calculator()
                co2_result = co2_calc.calculate(composition, selected_cement)
                
                # Stocker résultats
                st.session_state['last_prediction'] = {
                    'composition': composition,
                    'predictions': predictions,
                    'co2_result': co2_result,  # ✅ NOUVEAU
                    'cement_type': selected_cement,  # ✅ NOUVEAU
                    'timestamp': datetime.now(),
                    'name': formulation_name
                }
                st.session_state['show_results'] = True
                
                # Incrémenter compteur
                st.session_state['prediction_count'] += 1
                
                st.success("Prédiction + CO₂ réussie !")
                
            except ValueError as e:
                st.error(f"**Erreur de validation** : {e}")
                st.session_state['show_results'] = False
            
            except Exception as e:
                logger.error(f"Erreur prédiction: {e}", exc_info=True)
                st.error(f"**Erreur** : {e}")
                st.session_state['show_results'] = False
    
    # ═══════════════════════════════════════════════════════════════
    # AFFICHAGE RÉSULTATS
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.get('show_results') and st.session_state.get('last_prediction'):
        
        last = st.session_state['last_prediction']
        predictions = last['predictions']
        composition = last['composition']
        co2_result = last.get('co2_result')  # ✅ NOUVEAU
        cement_type = last.get('cement_type', 'CEM I')  # ✅ NOUVEAU
        formulation_name = last['name']
        
        # ───────────────────────────────────────────────────────────
        # MÉTRIQUES PRINCIPALES (4 colonnes avec CO₂)
        # ───────────────────────────────────────────────────────────
        
        st.markdown("### 📈 Propriétés Prédites + Empreinte Carbone")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            resistance = predictions['Resistance']
            grade_r = "excellent" if resistance >= 50 else ("bon" if resistance >= 35 else "moyen")
            
            metric_card(
                title="Résistance",
                value=resistance,
                unit="MPa",
                icon="💪",
                quality_grade=grade_r
            )
        
        with col_m2:
            diffusion = predictions['Diffusion_Cl']
            grade_d = "excellent" if diffusion < 5 else ("bon" if diffusion < 8 else "moyen")
            
            metric_card(
                title="Diffusion Cl⁻",
                value=diffusion,
                unit="×10⁻¹²",
                icon="🧂",
                quality_grade=grade_d
            )
        
        with col_m3:
            carbonatation = predictions['Carbonatation']
            grade_c = "excellent" if carbonatation < 10 else ("bon" if carbonatation < 15 else "moyen")
            
            metric_card(
                title="Carbonatation",
                value=carbonatation,
                unit="mm",
                icon="🌫️",
                quality_grade=grade_c
            )
        
        # ✅ NOUVELLE MÉTRIQUE CO₂
        with col_m4:
            if co2_result:
                co2_total = co2_result.co2_total_kg_m3
                classe_env, emoji, color = get_environmental_grade(co2_total)
                
                # Déterminer grade
                if co2_total < 250:
                    grade_co2 = "excellent"
                elif co2_total < 350:
                    grade_co2 = "bon"
                else:
                    grade_co2 = "moyen"
                
                metric_card(
                    title="Empreinte CO₂",
                    value=co2_total,
                    unit="kg/m³",
                    icon="🌍",
                    quality_grade=grade_co2
                )
                
                st.caption(f"{emoji} Classe: **{classe_env}**")
            else:
                st.metric("Empreinte CO₂", "N/A", help="Calcul non disponible")
        
        # ───────────────────────────────────────────────────────────
        # ✅ NOUVEAU : DÉTAILS CO₂
        # ───────────────────────────────────────────────────────────
        
        if co2_result:
            st.markdown("---")
            st.markdown("### 🌍 Détail Empreinte Carbone")
            
            col_co2_1, col_co2_2 = st.columns([1, 1])
            
            with col_co2_1:
                st.markdown("#### Répartition par Constituant")
                
                # Calculer pourcentages
                co2_calc_temp = CO2Calculator()
                breakdown = co2_calc_temp.get_breakdown_percentages(co2_result)
                
                # Afficher top contributeurs
                sorted_breakdown = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
                
                for constituent, percent in sorted_breakdown:
                    if percent > 1.0:  # Afficher seulement > 1%
                        co2_value = getattr(co2_result, f'co2_{constituent.lower()}', 0)
                        st.markdown(f"• **{constituent}** : {co2_value:.1f} kg ({percent:.1f}%)")
            
            with col_co2_2:
                st.markdown("#### Informations Ciment")
                
                st.markdown(f"**Type** : {cement_type}")
                st.markdown(f"**Facteur CO₂** : {co2_result.cement_co2_factor:.1f} kg CO₂/t")
                
                # Équivalence pédagogique
                arbres_annee = co2_total / 25  # 1 arbre absorbe ~25 kg/an
                st.markdown(f"**Équivalent** : {arbres_annee:.1f} arbres/an")
                
                # Suggestions réduction
                if co2_total > 300:
                    with st.expander("💡 Suggestions Réduction CO₂"):
                        if cement_type == 'CEM I':
                            st.info("Remplacer CEM I par CEM III/B → Réduction ~60%")
                        
                        if composition.get('Laitier', 0) < 50:
                            st.info("Ajouter laitier (20-30%) → Réduction ~20-30%")
                        
                        st.info("Réduire dosage ciment de 10% → Réduction ~10%")
        
        # ───────────────────────────────────────────────────────────
        # INDICATEURS TECHNIQUES
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### 📊 Indicateurs Techniques")
        
        col_i1, col_i2, col_i3 = st.columns(3)
        
        with col_i1:
            st.metric(
                label="Liant Total",
                value=f"{predictions['Liant_Total']:.0f} kg/m³"
            )
        
        with col_i2:
            ratio_el = predictions['Ratio_E_L']
            color_el = "🟢" if ratio_el <= 0.50 else ("🟡" if ratio_el <= 0.60 else "🔴")
            st.metric(
                label="Ratio E/L",
                value=f"{color_el} {ratio_el:.3f}"
            )
        
        with col_i3:
            taux_sub = predictions.get('Pct_Substitution', 0) * 100
            st.metric(
                label="Substitution",
                value=f"{taux_sub:.1f}%"
            )
        
        # ───────────────────────────────────────────────────────────
        # VALIDATION NORMATIVE
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### 🔍 Validation Normative (EN 206)")
        
        validation_report = validate_formulation(
            composition=composition,
            predictions=predictions
        )
        
        with st.expander("🔍 Détails des recommandations", expanded=True):
            for alert in validation_report.alerts[:5]:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"**{alert.severity.value.upper()}**")
                with col2:
                    st.markdown(f"**{alert.message}**")
                    st.caption(f"💡 {alert.recommendation}")
                    if alert.norm_ref:
                        st.caption(f"📖 {alert.norm_ref}")
                st.divider()
        
        col_v1, col_v2, col_v3 = st.columns(3)
        
        with col_v1:
            compliance_score = validation_report.compliance_score
            color_score = "🟢" if compliance_score >= 80 else ("🟡" if compliance_score >= 60 else "🔴")
            st.metric("Score Conformité", f"{color_score} {compliance_score:.0f}/100")
        
        with col_v2:
            st.metric("Classe Résistance", validation_report.resistance_class or "N/A")
        
        with col_v3:
            st.metric("Classe Exposition", validation_report.exposure_class or "N/A")
        
        # ───────────────────────────────────────────────────────────
        # VISUALISATIONS
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### 📊 Visualisations")
        
        tab_comp, tab_perf, tab_co2 = st.tabs(["Composition", "Performance", "🌍 Impact CO₂"])
        
        with tab_comp:
            fig_pie = plot_composition_pie(composition)
            st.plotly_chart(fig_pie, width='stretch')
        
        with tab_perf:
            fig_radar = plot_performance_radar(predictions, name=formulation_name)
            st.plotly_chart(fig_radar, width='stretch')
        
        # ✅ NOUVEAU : Tab CO₂
        with tab_co2:
            if co2_result:
                import plotly.graph_objects as go
                
                # Graphique répartition CO₂
                breakdown = co2_calc_temp.get_breakdown_percentages(co2_result)
                
                # Filtrer > 1%
                filtered_breakdown = {k: v for k, v in breakdown.items() if v > 1.0}
                
                fig_co2 = go.Figure(data=[
                    go.Pie(
                        labels=list(filtered_breakdown.keys()),
                        values=list(filtered_breakdown.values()),
                        hole=0.4,
                        marker=dict(colors=['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6'])
                    )
                ])
                
                fig_co2.update_layout(
                    title=f"Répartition Empreinte CO₂ - Total: {co2_total:.1f} kg/m³",
                    height=400
                )
                
                st.plotly_chart(fig_co2, width='stretch')
        
        # ───────────────────────────────────────────────────────────
        # ACTIONS
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### ⚡ Actions Rapides")
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            save_button = st.button("💾 Sauvegarder", width='stretch', type="primary")
        
        with col_act2:
            fav_button = st.button("⭐ Favoris", width='stretch')
        
        with col_act3:
            export_button = st.button("📥 Export CSV", width='stretch')
        
        # Traitement boutons (identique à avant)
        if save_button:
            db_manager = st.session_state.get('db_manager')
            
            if db_manager and db_manager.is_connected:
                try:
                    with st.spinner("💾 Sauvegarde..."):
                        success = db_manager.save_prediction(
                            formulation=composition,
                            predictions=predictions,
                            formulation_name=formulation_name,
                            user_id='anonyme'
                        )
                        
                        if success:
                            st.success("✅ Sauvegardée !")
                            st.balloons()
                            st.session_state['total_saves'] += 1
                        else:
                            st.error("❌ Échec")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
            else:
                st.warning("⚠️ DB non connectée")
        
        if fav_button:
            if not any(fav['name'] == formulation_name for fav in st.session_state['favorites']):
                st.session_state['favorites'].append({
                    'name': formulation_name,
                    'composition': composition,
                    'predictions': predictions,
                    'co2_result': co2_result,  # ✅ Inclure CO₂
                    'timestamp': datetime.now()
                })
                st.success(f"⭐ {formulation_name} ajouté")
            else:
                st.warning("⚠️ Déjà en favoris")
        
        if export_button:
            try:
                import pandas as pd
                
                export_data = {
                    'Nom': formulation_name,
                    'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    **composition,
                    **predictions,
                    'CO2_Total_kg_m3': co2_result.co2_total_kg_m3 if co2_result else 0,
                    'Cement_Type': cement_type
                }
                
                df = pd.DataFrame([export_data])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    "⬇️ Télécharger CSV",
                    data=csv,
                    file_name=f"{formulation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width='stretch'
                )
                
                st.success("📁 CSV prêt")
            except Exception as e:
                st.error(f"❌ Erreur export : {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # ÉTAT INITIAL
    # ═══════════════════════════════════════════════════════════════
    
    elif not st.session_state.get('show_results'):
        info_box(
            title="Mode d'emploi",
            content="""
            1. **Sélectionnez** composition et type de ciment
            2. **Cliquez** sur "🚀 Lancer la Prédiction + CO₂"
            3. **Analysez** résultats ML + empreinte carbone
            4. **Optimisez** avec suggestions réduction CO₂
            
            **Nouveau** : Calcul automatique empreinte CO₂ selon NF EN 15804
            """.strip(),
            icon="ℹ️",
            color="info"
        )
        
        # Dernière prédiction
        if st.session_state.get('last_prediction'):
            st.markdown("---")
            st.markdown("### 🕐 Dernière Prédiction")
            
            last = st.session_state['last_prediction']
            
            col_l1, col_l2, col_l3, col_l4 = st.columns(4)
            
            with col_l1:
                st.metric("Résistance", f"{last['predictions']['Resistance']:.1f} MPa")
            
            with col_l2:
                st.metric("Diffusion Cl⁻", f"{last['predictions']['Diffusion_Cl']:.2f}")
            
            with col_l3:
                st.metric("Carbonatation", f"{last['predictions']['Carbonatation']:.1f} mm")
            
            with col_l4:
                if last.get('co2_result'):
                    st.metric("CO₂", f"{last['co2_result'].co2_total_kg_m3:.1f} kg/m³")
            
            if st.button("🔄 Réafficher", width='stretch'):
                st.session_state['show_results'] = True
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

col_stat1, col_stat2, col_stat3 = st.columns(3)

with col_stat1:
    st.caption(f"🔬 **Prédictions** : {st.session_state.get('prediction_count', 0)}")

with col_stat2:
    st.caption(f"💾 **Sauvegardes** : {st.session_state.get('total_saves', 0)}")

with col_stat3:
    st.caption(f"⭐ **Favoris** : {len(st.session_state.get('favorites', []))}")

st.caption("🌍 **Nouveau** : Empreinte CO₂ calculée selon NF EN 15804 | 💡 Utilisez CEM III/B pour réduire de ~60%")