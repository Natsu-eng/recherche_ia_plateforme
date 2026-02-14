"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Analyse de Données - Historique & Tendances
Fichier: app/pages/5_Analyse_de_Données.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
- Historique complet des prédictions
- Graphiques de tendances
- Statistiques descriptives
- Corrélations
- Export massif
"""

import streamlit as st
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import info_box

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Analytics - Béton IA",
    page_icon="📈",
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
        📈 Analyse de Données - Historique & Tendances
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Visualisez l'historique de vos prédictions et identifiez les tendances.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

db_manager = st.session_state.get('db_manager')

if not db_manager:
    st.warning("⚠️ Base de données non connectée. Impossible de charger l'historique.")
    st.stop()

# Filtres
col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    period = st.selectbox(
        "📅 Période",
        options=["7 derniers jours", "30 derniers jours", "Tout l'historique"],
        index=1
    )

with col_filter2:
    min_resistance = st.number_input(
        "Résistance Min (MPa)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0
    )

with col_filter3:
    limit = st.number_input(
        "Nombre Max",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )

# Charger données
with st.spinner("🔄 Chargement de l'historique..."):
    try:
        # Requête SQL selon période
        if period == "7 derniers jours":
            days_filter = 7
        elif period == "30 derniers jours":
            days_filter = 30
        else:
            days_filter = 36500  # ~100 ans (tout)
        
        query = f"""
        SELECT 
            id,
            nom_formulation,
            resistance_predite,
            diffusion_cl_predite,
            carbonatation_predite,
            ratio_eau_liaison,
            ciment,
            eau,
            sable,
            gravier,
            jours_cure as age,
            horodatage as created_at
        FROM predictions
        WHERE resistance_predite >= {min_resistance}
          AND diffusion_cl_predite IS NOT NULL
          AND carbonatation_predite IS NOT NULL
          AND horodatage > NOW() - INTERVAL '{days_filter} days'
        ORDER BY horodatage DESC
        LIMIT {limit}
        """
        
        results = db_manager.execute_query(query, fetch=True)
        
        if not results:
            st.info("ℹ️ Aucune donnée disponible avec ces filtres.")
            st.stop()
        
        # Créer DataFrame
        df = pd.DataFrame(results)
        
        # Renommer colonnes
        df = df.rename(columns={
            'nom_formulation': 'Formulation',
            'resistance_predite': 'Résistance',
            'diffusion_cl_predite': 'Diffusion_Cl',
            'carbonatation_predite': 'Carbonatation',
            'ratio_eau_liaison': 'Ratio_EL',
            'created_at': 'Date'
        })
        
        st.success(f"✅ {len(df)} prédictions chargées")
    
    except Exception as e:
        logger.error(f"Erreur chargement: {e}", exc_info=True)
        st.error(f"❌ Erreur : {e}")
        st.stop()

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# STATISTIQUES DESCRIPTIVES
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📊 Statistiques Descriptives")

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.metric(
        "📊 Prédictions",
        f"{len(df):,}"
    )

with col_stat2:
    st.metric(
        "💪 Résistance Moyenne",
        f"{df['Résistance'].mean():.1f} MPa",
        delta=f"σ = {df['Résistance'].std():.1f}"
    )

with col_stat3:
    st.metric(
        "🧂 Diffusion Cl⁻ Moy.",
        f"{df['Diffusion_Cl'].mean():.2f}",
        delta=f"σ = {df['Diffusion_Cl'].std():.2f}"
    )

with col_stat4:
    st.metric(
        "🌫️ Carbonatation Moy.",
        f"{df['Carbonatation'].mean():.1f} mm",
        delta=f"σ = {df['Carbonatation'].std():.1f}"
    )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUES
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📈 Visualisations")

tab_trends, tab_distrib, tab_corr, tab_time = st.tabs([
    "Tendances",
    "Distributions",
    "Corrélations",
    "Évolution Temporelle"
])

# ─── TAB TENDANCES ───
with tab_trends:
    st.markdown("### 📊 Tendances des Cibles")
    
    # Graphique linéaire multi-lignes
    fig_trends = go.Figure()
    
    fig_trends.add_trace(go.Scatter(
        x=df.index,
        y=df['Résistance'],
        mode='lines+markers',
        name='Résistance (MPa)',
        line=dict(color=COLOR_PALETTE['primary'], width=2)
    ))
    
    # Axe secondaire pour Diffusion
    fig_trends.add_trace(go.Scatter(
        x=df.index,
        y=df['Diffusion_Cl'],
        mode='lines+markers',
        name='Diffusion Cl⁻',
        yaxis='y2',
        line=dict(color=COLOR_PALETTE['success'], width=2)
    ))
    
    fig_trends.update_layout(
        title="Évolution des Propriétés",
        xaxis_title="Index Prédiction",
        yaxis_title="Résistance (MPa)",
        yaxis2=dict(
            title="Diffusion Cl⁻ (×10⁻¹² m²/s)",
            overlaying='y',
            side='right'
        ),
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trends, width="stretch")

# ─── TAB DISTRIBUTIONS ───
with tab_distrib:
    st.markdown("### 📊 Distributions")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        fig_hist_r = px.histogram(
            df,
            x='Résistance',
            nbins=30,
            title="Distribution Résistance",
            color_discrete_sequence=[COLOR_PALETTE['primary']]
        )
        st.plotly_chart(fig_hist_r, width="stretch")
    
    with col_d2:
        fig_hist_d = px.histogram(
            df,
            x='Diffusion_Cl',
            nbins=30,
            title="Distribution Diffusion Cl⁻",
            color_discrete_sequence=[COLOR_PALETTE['success']]
        )
        st.plotly_chart(fig_hist_d, width="stretch")
    
    with col_d3:
        fig_hist_c = px.histogram(
            df,
            x='Carbonatation',
            nbins=30,
            title="Distribution Carbonatation",
            color_discrete_sequence=[COLOR_PALETTE['warning']]
        )
        st.plotly_chart(fig_hist_c, width="stretch")

# ─── TAB CORRÉLATIONS ───
with tab_corr:
    st.markdown("### 🔗 Matrice de Corrélation")
    
    # Sélectionner colonnes numériques
    numeric_cols = ['Résistance', 'Diffusion_Cl', 'Carbonatation', 
                   'Ratio_EL', 'ciment', 'eau', 'age']
    
    df_corr = df[numeric_cols].corr()
    
    fig_corr = px.imshow(
        df_corr,
        text_auto='.2f',
        aspect='auto',
        color_continuous_scale='RdBu_r',
        zmin=-1,
        zmax=1
    )
    
    fig_corr.update_layout(
        title="Matrice de Corrélation (Pearson)",
        height=600
    )
    
    st.plotly_chart(fig_corr, width="stretch")
    
    # Top corrélations
    st.markdown("#### 🔝 Corrélations Fortes")
    
    # Extraire corrélations sans diagonale
    corr_pairs = []
    for i in range(len(df_corr.columns)):
        for j in range(i+1, len(df_corr.columns)):
            corr_pairs.append({
                'Var1': df_corr.columns[i],
                'Var2': df_corr.columns[j],
                'Corrélation': df_corr.iloc[i, j]
            })
    
    df_corr_pairs = pd.DataFrame(corr_pairs)
    df_corr_pairs = df_corr_pairs.sort_values('Corrélation', key=abs, ascending=False).head(10)
    
    st.dataframe(
        df_corr_pairs.style.background_gradient(
            cmap='RdYlGn',
            subset=['Corrélation'],
            vmin=-1,
            vmax=1
        ).format({'Corrélation': '{:.3f}'}),
        width="stretch"
    )

# ─── TAB ÉVOLUTION TEMPORELLE ───
with tab_time:
    st.markdown("### 📅 Évolution dans le Temps")
    
    if 'Date' in df.columns:
        # Convertir en datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Grouper par jour
        df_daily = df.groupby(df['Date'].dt.date).agg({
            'Résistance': 'mean',
            'Diffusion_Cl': 'mean',
            'Carbonatation': 'mean'
        }).reset_index()
        
        fig_time = go.Figure()
        
        fig_time.add_trace(go.Scatter(
            x=df_daily['Date'],
            y=df_daily['Résistance'],
            mode='lines+markers',
            name='Résistance Moy.',
            line=dict(color=COLOR_PALETTE['primary'], width=3)
        ))
        
        fig_time.update_layout(
            title="Résistance Moyenne par Jour",
            xaxis_title="Date",
            yaxis_title="Résistance (MPa)",
            height=400
        )
        
        st.plotly_chart(fig_time, width="stretch")
    else:
        st.info("ℹ️ Pas de données temporelles disponibles")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# TABLEAU DÉTAILLÉ
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📋 Historique Détaillé")

# Colonnes à afficher
display_cols = ['Formulation', 'Résistance', 'Diffusion_Cl', 
               'Carbonatation', 'Ratio_EL', 'Date']

df_display = df[[col for col in display_cols if col in df.columns]]

st.dataframe(
    df_display.style.highlight_max(
        subset=['Résistance'],
        color='lightgreen'
    ).highlight_min(
        subset=['Diffusion_Cl', 'Carbonatation'],
        color='lightgreen'
    ).format({
        'Résistance': '{:.2f}',
        'Diffusion_Cl': '{:.2f}',
        'Carbonatation': '{:.2f}',
        'Ratio_EL': '{:.3f}'
    }),
    width="stretch",
    height=400
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📥 Export des Données")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Télécharger CSV",
        data=csv,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        width="stretch"
    )

with col_export2:
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Historique')
        
        # Stats
        df.describe().to_excel(writer, sheet_name='Statistiques')
    
    st.download_button(
        "📥 Télécharger Excel",
        data=buffer.getvalue(),
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch"
    )

with col_export3:
    # Export JSON
    json_data = df.to_json(orient='records', date_format='iso', indent=2)
    st.download_button(
        "📥 Télécharger JSON",
        data=json_data,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        width="stretch"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("💡 **Astuce** : Utilisez les filtres en haut pour affiner l'analyse")