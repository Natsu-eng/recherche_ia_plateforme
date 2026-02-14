"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Comparateur - Benchmark de Formulations
Fichier: app/pages/3_Comparateur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
- Chargement jusqu'à 10 formulations
- Tableau comparatif multi-critères
- Coordonnées parallèles
- Graphiques radar
- Export CSV/Excel
"""

import streamlit as st
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE, PRESET_FORMULATIONS, LABELS_MAP
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.forms import render_formulation_input
from app.components.cards import info_box
from app.components.charts import plot_parallel_coordinates, plot_performance_radar
from app.core.predictor import predict_concrete_properties
from app.core.analyzer import ConcreteAnalyzer

from app.core.session_manager import initialize_session

# Charge tout ce qu'il faut
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
        ⚖️ Comparateur de Formulations
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Comparez jusqu'à 10 formulations côte à côte pour identifier la plus adaptée.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# GESTION DES FORMULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

col_manage1, col_manage2, col_manage3 = st.columns([2, 1, 1])

with col_manage1:
    st.markdown(f"**Formulations chargées** : {len(st.session_state['comparison_formulations'])} / 10")

with col_manage2:
    if st.button("🗑️ Tout Effacer", type="secondary", width="stretch"):
        st.session_state['comparison_formulations'] = []
        st.rerun()

with col_manage3:
    if st.button("📊 Charger Toutes Présets", width="stretch"):
        if len(st.session_state['comparison_formulations']) + len(PRESET_FORMULATIONS) <= 10:
            for name, data in PRESET_FORMULATIONS.items():
                composition = {k: v for k, v in data.items() if k in ['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']}
                st.session_state['comparison_formulations'].append({
                    'name': name,
                    'composition': composition
                })
            st.rerun()
        else:
            st.warning("⚠️ Limite de 10 formulations atteinte")

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
            
            selected_preset_add = st.selectbox(
                "Sélectionner",
                options=preset_names,
                key="preset_add_selector"
            )
            
            if st.button("➕ Ajouter cette Formulation", key="add_preset", type="primary"):
                preset_data = PRESET_FORMULATIONS[selected_preset_add]
                composition = {k: v for k, v in preset_data.items() if k in ['Ciment', 'Laitier', 'CendresVolantes', 'Eau', 'Superplastifiant', 'GravilonsGros', 'SableFin', 'Age']}
                
                st.session_state['comparison_formulations'].append({
                    'name': selected_preset_add,
                    'composition': composition
                })
                st.success(f"✅ {selected_preset_add} ajoutée")
                st.rerun()
        
        # ─── TAB CUSTOM ───
        with tab_custom:
            st.markdown("#### Formulation Personnalisée")
            
            custom_name = st.text_input(
                "Nom",
                value=f"Formulation_{len(st.session_state['comparison_formulations']) + 1}",
                key="custom_name_input"
            )
            
            custom_composition = render_formulation_input(
                key_suffix="comparator_custom",
                layout="compact",
                show_presets=False
            )
            
            if st.button("➕ Ajouter", key="add_custom", type="primary"):
                st.session_state['comparison_formulations'].append({
                    'name': custom_name,
                    'composition': custom_composition
                })
                st.success(f"✅ {custom_name} ajoutée")
                st.rerun()
        
        # ─── TAB HISTORY ───
        with tab_history:
            st.markdown("#### Depuis l'Historique")
            
            db_manager = st.session_state.get('db_manager')
            
            if db_manager:
                recent = db_manager.get_recent_predictions(limit=10)
                
                if recent:
                    for i, record in enumerate(recent):
                        col_h1, col_h2 = st.columns([3, 1])
                        
                        with col_h1:
                            st.markdown(f"**{record['formulation_name']}** - {record['created_at'].strftime('%Y-%m-%d %H:%M')}")
                            st.caption(f"R: {record['resistance_predicted']:.1f} MPa | E/L: {record['ratio_e_l']:.3f}")
                        
                        with col_h2:
                            if st.button("➕", key=f"add_history_{i}"):
                                # Reconstruire composition
                                composition_hist = {
                                    'Ciment': record.get('ciment', 0),
                                    'Eau': record.get('eau', 0),
                                    'SableFin': record.get('sable', 0),
                                    'GravilonsGros': record.get('gravier', 0),
                                    'Superplastifiant': record.get('adjuvants', 0),
                                    'Age': record.get('age', 28),
                                    'Laitier': 0,
                                    'CendresVolantes': 0
                                }
                                
                                st.session_state['comparison_formulations'].append({
                                    'name': record['formulation_name'],
                                    'composition': composition_hist
                                })
                                st.rerun()
                else:
                    st.info("Aucun historique disponible")
            else:
                st.warning("Base de données non connectée")

else:
    st.info("✋ Limite de 10 formulations atteinte. Supprimez-en pour ajouter de nouvelles.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# COMPARAISON
# ═══════════════════════════════════════════════════════════════════════════════

if len(st.session_state['comparison_formulations']) >= 2:
    
    if st.button("🚀 Comparer les Formulations", type="primary", width="stretch"):
        
        with st.spinner("🔄 Calcul des prédictions..."):
            try:
                model = st.session_state.get('model')
                features = st.session_state.get('features')
                
                # Prédire pour chaque formulation
                results = []
                
                for formulation in st.session_state['comparison_formulations']:
                    name = formulation['name']
                    composition = formulation['composition']
                    
                    predictions = predict_concrete_properties(
                        composition=composition,
                        model=model,
                        feature_list=features,
                        validate=False
                    )
                    
                    # Combiner composition + prédictions
                    result = {
                        'Nom': name,
                        **composition,
                        **predictions
                    }
                    
                    results.append(result)
                
                df_comparison = pd.DataFrame(results)
                
                st.success(f"✅ {len(results)} formulations comparées")
                
                # ───────────────────────────────────────────────────────
                # TABLEAU COMPARATIF
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 📊 Tableau Comparatif")
                
                # Colonnes à afficher
                display_cols = [
                    'Nom',
                    'Ciment', 'Laitier', 'CendresVolantes', 'Eau',
                    'Ratio_E_L', 'Liant_Total',
                    'Resistance', 'Diffusion_Cl', 'Carbonatation'
                ]
                
                df_display = df_comparison[[col for col in display_cols if col in df_comparison.columns]]
                
                # Renommer pour affichage
                rename_map = {
                    'Resistance': 'Résistance (MPa)',
                    'Diffusion_Cl': 'Diffusion Cl⁻',
                    'Carbonatation': 'Carbonatation (mm)',
                    'Ratio_E_L': 'Ratio E/L',
                    'Liant_Total': 'Liant Total (kg)'
                }
                
                df_display = df_display.rename(columns=rename_map)
                
                # Highlight meilleurs/pires
                st.dataframe(
                    df_display.style.highlight_max(
                        subset=['Résistance (MPa)'],
                        color='lightgreen'
                    ).highlight_min(
                        subset=['Diffusion Cl⁻', 'Carbonatation (mm)'],
                        color='lightgreen'
                    ).format({
                        'Résistance (MPa)': '{:.2f}',
                        'Diffusion Cl⁻': '{:.2f}',
                        'Carbonatation (mm)': '{:.2f}',
                        'Ratio E/L': '{:.3f}'
                    }),
                    width="stretch",
                    height=400
                )
                
                st.markdown("---")
                
                # ───────────────────────────────────────────────────────
                # GRAPHIQUES
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 📈 Visualisations")
                
                tab_parallel, tab_bars, tab_radar = st.tabs([
                    "Coordonnées Parallèles",
                    "Barres Comparatives",
                    "Radars"
                ])
                
                with tab_parallel:
                    fig_parallel = plot_parallel_coordinates(df_comparison, color_by='Resistance')
                    st.plotly_chart(fig_parallel, width="stretch")
                
                with tab_bars:
                    # Graphiques en barres pour chaque cible
                    col_b1, col_b2, col_b3 = st.columns(3)
                    
                    with col_b1:
                        fig_r = go.Figure(data=[
                            go.Bar(
                                x=df_comparison['Nom'],
                                y=df_comparison['Resistance'],
                                marker_color=COLOR_PALETTE['primary']
                            )
                        ])
                        fig_r.update_layout(
                            title="Résistance (MPa)",
                            height=350
                        )
                        st.plotly_chart(fig_r, width="stretch")
                    
                    with col_b2:
                        fig_d = go.Figure(data=[
                            go.Bar(
                                x=df_comparison['Nom'],
                                y=df_comparison['Diffusion_Cl'],
                                marker_color=COLOR_PALETTE['success']
                            )
                        ])
                        fig_d.update_layout(
                            title="Diffusion Cl⁻",
                            height=350
                        )
                        st.plotly_chart(fig_d, width="stretch")
                    
                    with col_b3:
                        fig_c = go.Figure(data=[
                            go.Bar(
                                x=df_comparison['Nom'],
                                y=df_comparison['Carbonatation'],
                                marker_color=COLOR_PALETTE['warning']
                            )
                        ])
                        fig_c.update_layout(
                            title="Carbonatation (mm)",
                            height=350
                        )
                        st.plotly_chart(fig_c, width="stretch")
                
                with tab_radar:
                    # Afficher radars pour top 3
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
                            
                            fig_radar = plot_performance_radar(
                                predictions=predictions_radar,
                                name=row['Nom']
                            )
                            
                            st.plotly_chart(fig_radar, width="stretch")
                
                st.markdown("---")
                
                # ───────────────────────────────────────────────────────
                # CLASSEMENT
                # ───────────────────────────────────────────────────────
                
                st.markdown("### 🏆 Classements")
                
                col_rank1, col_rank2, col_rank3 = st.columns(3)
                
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
                        file_name=f"comparaison_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        width="stretch"
                    )
                
                with col_export2:
                    # Excel (nécessite openpyxl)
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_comparison.to_excel(writer, index=False, sheet_name='Comparaison')
                    
                    st.download_button(
                        "📥 Télécharger Excel",
                        data=buffer.getvalue(),
                        file_name=f"comparaison_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch"
                    )
            
            except Exception as e:
                logger.error(f"Erreur comparaison: {e}", exc_info=True)
                st.error(f"❌ Erreur : {e}")

elif len(st.session_state['comparison_formulations']) == 1:
    st.info("ℹ️ Ajoutez au moins une autre formulation pour effectuer une comparaison.")

else:
    info_box(
        "Mode d'emploi",
        """
        1. **Ajoutez** 2 à 10 formulations (prédéfinies, personnalisées ou depuis l'historique)
        2. **Cliquez** sur "🚀 Comparer les Formulations"
        3. **Analysez** le tableau comparatif et les graphiques
        4. **Exportez** les résultats en CSV ou Excel
        
        Les formulations seront comparées sur :
        - Résistance en compression
        - Diffusion des chlorures
        - Profondeur de carbonatation
        - Ratio E/L et liant total
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
            st.caption(
                f"Ciment: {comp.get('Ciment', 0):.0f} | "
                f"Eau: {comp.get('Eau', 0):.0f} | "
                f"Age: {comp.get('Age', 0):.0f}j"
            )
        
        with col_form2:
            if st.button("🗑️", key=f"remove_{i}"):
                st.session_state['comparison_formulations'].pop(i)
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("💡 **Conseil** : Utilisez les coordonnées parallèles pour identifier visuellement les tendances")