"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Comparateur - Benchmark de Formulations + CO₂
Fichier: pages/3_Comparateur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.1.0 - AVEC MODULE CO₂
═══════════════════════════════════════════════════════════════════════════════

NOUVEAUTÉS v1.1.0:
✅ Calcul empreinte CO₂ pour chaque formulation
✅ Colonne CO₂ dans tableau comparatif
✅ Classement par empreinte carbone
✅ Graphique comparatif CO₂
✅ Export avec données environnementales
"""

import streamlit as st
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE, PRESET_FORMULATIONS
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.forms import render_formulation_input
from app.components.cards import info_box
from app.components.charts import plot_parallel_coordinates, plot_performance_radar
from app.core.predictor import predict_concrete_properties

# IMPORT MODULE CO₂
from app.core.co2_calculator import CO2Calculator, get_environmental_grade

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Comparateur - Béton IA",
    page_icon="⚖️",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

from app.components.navbar import render_navbar
render_navbar(current_page="Comparateur")

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

if 'comparison_formulations' not in st.session_state:
    st.session_state['comparison_formulations'] = []

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        ⚖️ Comparateur de Formulations + Empreinte CO₂
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Comparez jusqu'à 10 formulations sur performance + impact environnemental.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# NOUVEAU : Sélection type de ciment global
# ═══════════════════════════════════════════════════════════════════════════════

col_cement, col_manage1, col_manage2, col_manage3 = st.columns([2, 2, 1, 1])

with col_cement:
    st.markdown("### 🏭 Type de Ciment (Global)")
    
    from config.co2_database import CEMENT_CO2_KG_PER_TONNE
    cement_types = list(CEMENT_CO2_KG_PER_TONNE.keys())
    
    global_cement_type = st.selectbox(
        "Appliquer à toutes les formulations",
        options=cement_types,
        index=0,
        help="Type de ciment utilisé pour le calcul CO₂"
    )

with col_manage1:
    st.markdown(f"**Formulations** : {len(st.session_state['comparison_formulations'])} / 10")

with col_manage2:
    if st.button("🗑️ Effacer", type="secondary", width='stretch'):
        st.session_state['comparison_formulations'] = []
        st.rerun()

with col_manage3:
    if st.button("📊 Présets", width='stretch'):
        if len(st.session_state['comparison_formulations']) + len(PRESET_FORMULATIONS) <= 10:
            for name, data in PRESET_FORMULATIONS.items():
                composition = {k: v for k, v in data.items() if k in ['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']}
                st.session_state['comparison_formulations'].append({
                    'name': name,
                    'composition': composition
                })
            st.rerun()
        else:
            st.warning("⚠️ Limite 10 atteinte")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# AJOUT FORMULATION
# ═══════════════════════════════════════════════════════════════════════════════

if len(st.session_state['comparison_formulations']) < 10:
    with st.expander("➕ Ajouter une Formulation", expanded=len(st.session_state['comparison_formulations']) == 0):
        
        tab_preset, tab_custom, tab_history = st.tabs(["📚 Prédéfinies", "✏️ Personnalisée", "🕐 Historique"])
        
        # ─── TAB PRESETS ───
        with tab_preset:
            st.markdown("#### Formulations Prédéfinies")
            
            preset_names = list(PRESET_FORMULATIONS.keys())
            selected_preset_add = st.selectbox("Sélectionner", options=preset_names, key="preset_add")
            
            if st.button("➕ Ajouter", key="add_preset", type="primary"):
                preset_data = PRESET_FORMULATIONS[selected_preset_add]
                composition = {k: v for k, v in preset_data.items() if k in ['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']}
                
                st.session_state['comparison_formulations'].append({
                    'name': selected_preset_add,
                    'composition': composition
                })
                st.success(f"{selected_preset_add} ajoutée")
                st.rerun()
        
        # ─── TAB CUSTOM ───
        with tab_custom:
            st.markdown("#### Formulation Personnalisée")
            
            custom_name = st.text_input("Nom", value=f"Formulation_{len(st.session_state['comparison_formulations']) + 1}", key="custom_name")
            custom_composition = render_formulation_input(key_suffix="comparator_custom", layout="compact", show_presets=False)
            
            if st.button("➕ Ajouter", key="add_custom", type="primary"):
                st.session_state['comparison_formulations'].append({
                    'name': custom_name,
                    'composition': custom_composition
                })
                st.success(f"{custom_name} ajoutée")
                st.rerun()
        
        # ─── TAB HISTORY ───
        with tab_history:
            st.markdown("#### Depuis l'Historique")
            
            db_manager = st.session_state.get('db_manager')
            
            if db_manager and db_manager.is_connected:
                recent = db_manager.get_recent_predictions(limit=10)
                
                if recent:
                    for i, record in enumerate(recent):
                        col_h1, col_h2 = st.columns([3, 1])
                        
                        with col_h1:
                            st.markdown(f"**{record['formulation_name']}** - {record['created_at'].strftime('%Y-%m-%d %H:%M')}")
                            st.caption(f"R: {record['resistance_predicted']:.1f} MPa | E/L: {record['ratio_e_l']:.3f}")
                        
                        with col_h2:
                            if st.button("➕", key=f"add_history_{i}"):
                                composition_hist = {
                                    'Ciment': record.get('ciment', 0),
                                    'Eau': record.get('eau', 0),
                                    'SableFin': record.get('sable', 0),
                                    'GravilonsGros': record.get('gravier', 0),
                                    'Superplastifiant': record.get('adjuvants', 0),
                                    'Age': record.get('age', 28),
                                    'Laitier': record.get('laitier', 0),
                                    'CendresVolantes': record.get('cendres', 0),
                                    'Metakaolin': record.get('metakaolin', 0)
                                }
                                
                                st.session_state['comparison_formulations'].append({
                                    'name': record['formulation_name'],
                                    'composition': composition_hist
                                })
                                st.rerun()
                else:
                    st.info("Aucun historique")
            else:
                st.warning("DB non connectée")

else:
    st.info("✋ Limite 10 atteinte")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# COMPARAISON
# ═══════════════════════════════════════════════════════════════════════════════

if len(st.session_state['comparison_formulations']) >= 2:
    
    if st.button("🚀 Comparer les Formulations + CO₂", type="primary", width='stretch'):
        
        with st.spinner("🔄 Calcul des prédictions + empreintes CO₂..."):
            try:
                model = st.session_state.get('model')
                features = st.session_state.get('features')
                
                # Initialiser calculateur CO₂
                co2_calc = CO2Calculator()
                
                results = []
                
                # Barre de progression
                progress_bar = st.progress(0)
                
                for idx, formulation in enumerate(st.session_state['comparison_formulations']):
                    name = formulation['name']
                    composition = formulation['composition']
                    
                    # 1. Prédictions ML (avec correcteur MK si applicable)
                    if composition.get('Metakaolin', 0) > 0 and st.session_state.get('mk_corrector'):
                        from app.core.predictor import predict_with_mk
                        predictions = predict_with_mk(
                            composition=composition,
                            model=model,
                            feature_list=features,
                            mk_corrector=st.session_state['mk_corrector'],
                            validate=False
                        )
                    else:
                        predictions = predict_concrete_properties(
                            composition=composition,
                            model=model,
                            feature_list=features,
                            validate=False
                        )
                    
                    # 2. Calcul CO₂
                    co2_result = co2_calc.calculate(composition, global_cement_type)
                    
                    # Combiner tout
                    result = {
                        'Nom': name,
                        **composition,
                        **predictions,
                        # CO₂ (ajout au résultat)
                        'CO2_Total': co2_result.co2_total_kg_m3,
                        'CO2_Ciment': co2_result.co2_ciment,
                        'CO2_Classe': get_environmental_grade(co2_result.co2_total_kg_m3)[0]
                    }
                    
                    results.append(result)
                    
                    # Mise à jour progression
                    progress_bar.progress((idx + 1) / len(st.session_state['comparison_formulations']))
                
                df_comparison = pd.DataFrame(results)
                
                st.success(f"{len(results)} formulations comparées (ML + CO₂)")
                
                # ───────────────────────────────────────────────────────
                # TABLEAU COMPARATIF
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 📊 Tableau Comparatif")
                
                # Colonnes avec CO₂
                display_cols = [
                    'Nom',
                    'Ciment', 'Laitier', 'CendresVolantes', 'Eau',
                    'Ratio_E_L', 'Liant_Total',
                    'Resistance', 'Diffusion_Cl', 'Carbonatation',
                    'CO2_Total', 'CO2_Classe'  
                ]
                
                df_display = df_comparison[[col for col in display_cols if col in df_comparison.columns]]
                
                # Renommer
                rename_map = {
                    'Resistance': 'Résistance (MPa)',
                    'Diffusion_Cl': 'Diffusion Cl⁻',
                    'Carbonatation': 'Carbonatation (mm)',
                    'Ratio_E_L': 'Ratio E/L',
                    'Liant_Total': 'Liant (kg)',
                    'CO2_Total': 'CO₂ (kg/m³)',  
                    'CO2_Classe': 'Classe CO₂'    
                }
                
                df_display = df_display.rename(columns=rename_map)
                
                # Highlight meilleurs + CO₂ min
                st.dataframe(
                    df_display.style.highlight_max(
                        subset=['Résistance (MPa)'],
                        color='lightgreen'
                    ).highlight_min(
                        subset=['Diffusion Cl⁻', 'Carbonatation (mm)', 'CO₂ (kg/m³)'],  
                        color='lightgreen'
                    ).format({
                        'Résistance (MPa)': '{:.2f}',
                        'Diffusion Cl⁻': '{:.2f}',
                        'Carbonatation (mm)': '{:.2f}',
                        'Ratio E/L': '{:.3f}',
                        'CO₂ (kg/m³)': '{:.1f}'  
                    }),
                    width='stretch',
                    height=400
                )
                
                st.markdown("---")
                
                # ───────────────────────────────────────────────────────
                # GRAPHIQUES
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 📈 Visualisations")
                
                # Nouveau tab CO₂
                tab_parallel, tab_bars, tab_radar, tab_co2 = st.tabs([
                    "Coordonnées Parallèles",
                    "Barres Comparatives",
                    "Radars",
                    "🌍 Impact CO₂"  
                ])
                
                with tab_parallel:
                    fig_parallel = plot_parallel_coordinates(df_comparison, color_by='Resistance')
                    st.plotly_chart(fig_parallel, width='stretch')
                
                with tab_bars:
                    # 4 graphiques (ajout CO₂)
                    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                    
                    with col_b1:
                        fig_r = go.Figure(data=[go.Bar(x=df_comparison['Nom'], y=df_comparison['Resistance'], marker_color=COLOR_PALETTE['primary'])])
                        fig_r.update_layout(title="Résistance (MPa)", height=300, showlegend=False)
                        st.plotly_chart(fig_r, width='stretch')
                    
                    with col_b2:
                        fig_d = go.Figure(data=[go.Bar(x=df_comparison['Nom'], y=df_comparison['Diffusion_Cl'], marker_color=COLOR_PALETTE['success'])])
                        fig_d.update_layout(title="Diffusion Cl⁻", height=300, showlegend=False)
                        st.plotly_chart(fig_d, width='stretch')
                    
                    with col_b3:
                        fig_c = go.Figure(data=[go.Bar(x=df_comparison['Nom'], y=df_comparison['Carbonatation'], marker_color=COLOR_PALETTE['warning'])])
                        fig_c.update_layout(title="Carbonatation (mm)", height=300, showlegend=False)
                        st.plotly_chart(fig_c, width='stretch')
                    
                    # Graphique CO₂
                    with col_b4:
                        fig_co2_bar = go.Figure(data=[go.Bar(x=df_comparison['Nom'], y=df_comparison['CO2_Total'], marker_color='#2ecc71')])
                        fig_co2_bar.update_layout(title="CO₂ (kg/m³)", height=300, showlegend=False)
                        st.plotly_chart(fig_co2_bar, width='stretch')
                
                with tab_radar:
                    st.markdown("#### Top 3 Formulations (Résistance)")
                    
                    df_sorted = df_comparison.sort_values('Resistance', ascending=False).head(3)
                    cols_radar = st.columns(3)
                    
                    for i, (idx, row) in enumerate(df_sorted.iterrows()):
                        with cols_radar[i]:
                            predictions_radar = {
                                'Resistance': row['Resistance'],
                                'Diffusion_Cl': row['Diffusion_Cl'],
                                'Carbonatation': row['Carbonatation'],
                                'Ratio_E_L': row['Ratio_E_L']
                            }
                            
                            fig_radar = plot_performance_radar(predictions_radar, name=row['Nom'])
                            st.plotly_chart(fig_radar, width='stretch')
                
                # NOUVEAU TAB CO₂
                with tab_co2:
                    st.markdown("#### Comparaison Empreinte Carbone")
                    
                    # Graphique comparatif CO₂
                    fig_co2_comp = go.Figure()
                    
                    # Trier par CO₂
                    df_co2_sorted = df_comparison.sort_values('CO2_Total')
                    
                    # Colorier selon classe
                    colors = []
                    for co2 in df_co2_sorted['CO2_Total']:
                        if co2 < 200:
                            colors.append('#2ecc71')  # Vert
                        elif co2 < 280:
                            colors.append('#27ae60')
                        elif co2 < 350:
                            colors.append('#f39c12')  # Orange
                        else:
                            colors.append('#e74c3c')  # Rouge
                    
                    fig_co2_comp.add_trace(go.Bar(
                        x=df_co2_sorted['Nom'],
                        y=df_co2_sorted['CO2_Total'],
                        marker_color=colors,
                        text=df_co2_sorted['CO2_Total'].round(1),
                        textposition='outside'
                    ))
                    
                    fig_co2_comp.update_layout(
                        title=f"Empreinte CO₂ - Ciment: {global_cement_type}",
                        xaxis_title="Formulation",
                        yaxis_title="kg CO₂/m³",
                        height=400,
                        showlegend=False
                    )
                    
                    # Lignes de classe
                    fig_co2_comp.add_hline(y=200, line_dash="dash", line_color="green", annotation_text="Très Faible")
                    fig_co2_comp.add_hline(y=280, line_dash="dash", line_color="orange", annotation_text="Moyen")
                    fig_co2_comp.add_hline(y=350, line_dash="dash", line_color="red", annotation_text="Élevé")
                    
                    st.plotly_chart(fig_co2_comp, width='stretch')
                    
                    # Statistiques CO₂
                    col_co2_1, col_co2_2, col_co2_3 = st.columns(3)
                    
                    with col_co2_1:
                        st.metric("CO₂ Min", f"{df_comparison['CO2_Total'].min():.1f} kg/m³")
                    
                    with col_co2_2:
                        st.metric("CO₂ Moyen", f"{df_comparison['CO2_Total'].mean():.1f} kg/m³")
                    
                    with col_co2_3:
                        st.metric("CO₂ Max", f"{df_comparison['CO2_Total'].max():.1f} kg/m³")
                
                st.markdown("---")
                
                # ───────────────────────────────────────────────────────
                # CLASSEMENTS
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 🏆 Classements")
                
                # 4 classements (ajout CO₂)
                col_rank1, col_rank2, col_rank3, col_rank4 = st.columns(4)
                
                with col_rank1:
                    st.markdown("#### 💪 Résistance")
                    df_r = df_comparison[['Nom', 'Resistance']].sort_values('Resistance', ascending=False)
                    for i, row in enumerate(df_r.itertuples(), 1):
                        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
                        st.markdown(f"{emoji} **{i}.** {row.Nom} - {row.Resistance:.1f} MPa")
                
                with col_rank2:
                    st.markdown("#### 🧂 Durabilité Cl⁻")
                    df_d = df_comparison[['Nom', 'Diffusion_Cl']].sort_values('Diffusion_Cl', ascending=True)
                    for i, row in enumerate(df_d.itertuples(), 1):
                        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
                        st.markdown(f"{emoji} **{i}.** {row.Nom} - {row.Diffusion_Cl:.2f}")
                
                with col_rank3:
                    st.markdown("#### 🌫️ Durabilité CO₂")
                    df_c = df_comparison[['Nom', 'Carbonatation']].sort_values('Carbonatation', ascending=True)
                    for i, row in enumerate(df_c.itertuples(), 1):
                        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
                        st.markdown(f"{emoji} **{i}.** {row.Nom} - {row.Carbonatation:.1f} mm")
                
                # NOUVEAU : Classement CO₂
                with col_rank4:
                    st.markdown("#### 🌍 Impact CO₂")
                    df_co2_rank = df_comparison[['Nom', 'CO2_Total']].sort_values('CO2_Total', ascending=True)
                    for i, row in enumerate(df_co2_rank.itertuples(), 1):
                        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
                        st.markdown(f"{emoji} **{i}.** {row.Nom} - {row.CO2_Total:.1f} kg")
                
                st.markdown("---")
                
                # ───────────────────────────────────────────────────────
                # EXPORT
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 📥 Export")
                
                col_export1, col_export2 = st.columns(2)
                
                with col_export1:
                    csv = df_comparison.to_csv(index=False)
                    st.download_button(
                        "📥 Télécharger CSV",
                        data=csv,
                        file_name=f"comparaison_co2_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
                
                with col_export2:
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_comparison.to_excel(writer, index=False, sheet_name='Comparaison')
                    
                    st.download_button(
                        "📥 Télécharger Excel",
                        data=buffer.getvalue(),
                        file_name=f"comparaison_co2_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch'
                    )
            
            except Exception as e:
                logger.error(f"Erreur comparaison: {e}", exc_info=True)
                st.error(f"Erreur : {e}")

elif len(st.session_state['comparison_formulations']) == 1:
    st.info("ℹ️ Ajoutez au moins une autre formulation")

else:
    info_box(
        "Mode d'emploi",
        """
        1. **Choisissez** le type de ciment (CEM I, CEM III/B...)
        2. **Ajoutez** 2 à 10 formulations
        3. **Cliquez** sur "🚀 Comparer"
        4. **Analysez** performance + empreinte CO₂
        5. **Exportez** les résultats
        
        **Nouveau** : Comparaison environnementale automatique
        """,
        icon="ℹ️",
        color="info"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# LISTE FORMULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state['comparison_formulations']:
    st.markdown("---")
    st.markdown("### 📋 Formulations Chargées")
    
    for i, formulation in enumerate(st.session_state['comparison_formulations']):
        col_form1, col_form2 = st.columns([4, 1])
        
        with col_form1:
            st.markdown(f"**{i+1}. {formulation['name']}**")
            comp = formulation['composition']
            mk = comp.get('Metakaolin', 0)
            mk_display = f" | MK: {mk:.0f}" if mk > 0 else ""
            st.caption(f"Ciment: {comp.get('Ciment', 0):.0f} | Eau: {comp.get('Eau', 0):.0f} | Age: {comp.get('Age', 0):.0f}j{mk_display}")
        
        with col_form2:
            if st.button("🗑️", key=f"remove_{i}"):
                st.session_state['comparison_formulations'].pop(i)
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("🌍 **Impact CO₂** calculé selon NF EN 15804 | 💡 CEM III/B = Réduction ~60% vs CEM I")