"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Analyse de Données - Historique & Tendances
Fichier: pages/5_Analyse_de_Données.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.1.0 - CORRECTIFS BD
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
- Historique complet des prédictions
- Graphiques de tendances
- Statistiques descriptives
- Corrélations
- Export massif

CORRECTIFS v1.1.0:
✅ Initialisation session_state
✅ Gestion DB améliorée
✅ Requêtes SQL sécurisées (paramétrisées)
✅ Gestion erreurs robuste
✅ width='stretch' (pas deprecated)
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
import numpy as np

from app.core.session_manager import initialize_session

# ✅ INITIALISER SESSION
initialize_session()

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
# VÉRIFICATION DB
# ═══════════════════════════════════════════════════════════════════════════════

db_manager = st.session_state.get('db_manager')

if not db_manager:
    st.warning("⚠️ Base de données non connectée. Impossible de charger l'historique.")
    st.info("💡 Vérifiez votre configuration dans le fichier .env")
    st.stop()

if not db_manager.is_connected:
    st.error("❌ Base de données hors ligne.")
    st.info("💡 Vérifiez que PostgreSQL est démarré")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# FILTRES
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("### 🔍 Filtres")

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

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

with st.spinner("🔄 Chargement de l'historique..."):
    try:
        # Déterminer intervalle
        if period == "7 derniers jours":
            days_filter = 7
        elif period == "30 derniers jours":
            days_filter = 30
        else:
            days_filter = 36500  # ~100 ans (tout)
        
        # ✅ REQUÊTE SÉCURISÉE (paramétrisée)
        query = """
        SELECT 
            id,
            nom_formulation,
            resistance_predite,
            diffusion_cl_predite,
            carbonatation_predite,
            ratio_eau_liaison,
            ciment,
            laitier,
            cendres,
            eau,
            sable,
            gravier,
            adjuvants,
            jours_cure as age,
            horodatage as created_at
        FROM predictions
        WHERE resistance_predite >= %s
          AND resistance_predite IS NOT NULL
          AND horodatage > NOW() - INTERVAL '%s days'
        ORDER BY horodatage DESC
        LIMIT %s
        """
        
        # ✅ PARAMÈTRES SÉCURISÉS
        params = (min_resistance, days_filter, limit)
        
        results = db_manager.execute_query(query, params=params, fetch=True)
        
        if not results or len(results) == 0:
            st.info(f"ℹ️ Aucune donnée disponible avec ces filtres.")
            st.info(f"💡 Essayez d'élargir la période ou de baisser le seuil de résistance")
            
            # Afficher stats DB
            try:
                count_query = "SELECT COUNT(*) as total FROM predictions"
                count_result = db_manager.execute_query(count_query, fetch=True)
                if count_result:
                    total = count_result[0]['total']
                    st.info(f"📊 Total de prédictions en base : {total}")
            except:
                pass
            
            st.stop()
        
        # ─────────────────────────────────────────────
        # Création DataFrame
        # ─────────────────────────────────────────────

        df = pd.DataFrame(results)

        # Renommer colonnes pour affichage
        df = df.rename(columns={
            'nom_formulation': 'Formulation',
            'resistance_predite': 'Résistance',
            'diffusion_cl_predite': 'Diffusion_Cl',
            'carbonatation_predite': 'Carbonatation',
            'ratio_eau_liaison': 'Ratio_EL',
            'created_at': 'Date'
        })

        # ─────────────────────────────────────────────
        # ✅ CORRECTION CRITIQUE : Decimal → float
        # (PostgreSQL retourne Decimal)
        # ─────────────────────────────────────────────

        numeric_columns = [
            'Résistance',
            'Diffusion_Cl',
            'Carbonatation',
            'Ratio_EL',
            'ciment',
            'laitier',
            'cendres',
            'eau',
            'sable',
            'gravier',
            'adjuvants',
            'age'
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)

        # ─────────────────────────────────────────────
        # Conversion Date
        # ─────────────────────────────────────────────

        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        
        # Gérer valeurs nulles
        df['Diffusion_Cl'] = df['Diffusion_Cl'].fillna(0)
        df['Carbonatation'] = df['Carbonatation'].fillna(0)
        df['Ratio_EL'] = df['Ratio_EL'].fillna(0.5)
        
        st.success(f"✅ {len(df)} prédictions chargées")
    
    except Exception as e:
        logger.error(f"Erreur chargement: {e}", exc_info=True)
        st.error(f"❌ Erreur lors du chargement : {type(e).__name__}")
        st.code(str(e), language="text")
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
    mean_r = df['Résistance'].mean()
    std_r = df['Résistance'].std()
    st.metric(
        "💪 Résistance Moyenne",
        f"{mean_r:.1f} MPa",
        delta=f"σ = {std_r:.1f}"
    )

with col_stat3:
    mean_d = df['Diffusion_Cl'].mean()
    std_d = df['Diffusion_Cl'].std()
    st.metric(
        "🧂 Diffusion Cl⁻ Moy.",
        f"{mean_d:.2f}",
        delta=f"σ = {std_d:.2f}"
    )

with col_stat4:
    mean_c = df['Carbonatation'].mean()
    std_c = df['Carbonatation'].std()
    st.metric(
        "🌫️ Carbonatation Moy.",
        f"{mean_c:.1f} mm",
        delta=f"σ = {std_c:.1f}"
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
        line=dict(color=COLOR_PALETTE['primary'], width=2),
        marker=dict(size=5)
    ))
    
    # Axe secondaire pour Diffusion
    fig_trends.add_trace(go.Scatter(
        x=df.index,
        y=df['Diffusion_Cl'],
        mode='lines+markers',
        name='Diffusion Cl⁻',
        yaxis='y2',
        line=dict(color=COLOR_PALETTE['success'], width=2),
        marker=dict(size=5)
    ))
    
    fig_trends.update_layout(
        title="Évolution des Propriétés",
        xaxis_title="Index Prédiction (ordre chronologique inverse)",
        yaxis_title="Résistance (MPa)",
        yaxis2=dict(
            title="Diffusion Cl⁻ (×10⁻¹² m²/s)",
            overlaying='y',
            side='right'
        ),
        height=500,
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig_trends, width='stretch')

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
            color_discrete_sequence=[COLOR_PALETTE['primary']],
            labels={'Résistance': 'Résistance (MPa)'}
        )
        fig_hist_r.update_layout(height=350)
        st.plotly_chart(fig_hist_r, width='stretch')
    
    with col_d2:
        fig_hist_d = px.histogram(
            df,
            x='Diffusion_Cl',
            nbins=30,
            title="Distribution Diffusion Cl⁻",
            color_discrete_sequence=[COLOR_PALETTE['success']],
            labels={'Diffusion_Cl': 'Diffusion Cl⁻'}
        )
        fig_hist_d.update_layout(height=350)
        st.plotly_chart(fig_hist_d, width='stretch')
    
    with col_d3:
        fig_hist_c = px.histogram(
            df,
            x='Carbonatation',
            nbins=30,
            title="Distribution Carbonatation",
            color_discrete_sequence=[COLOR_PALETTE['warning']],
            labels={'Carbonatation': 'Carbonatation (mm)'}
        )
        fig_hist_c.update_layout(height=350)
        st.plotly_chart(fig_hist_c, width='stretch')
    
    # Stats descriptives
    st.markdown("#### 📋 Statistiques Détaillées")
    
    stats_cols = ['Résistance', 'Diffusion_Cl', 'Carbonatation', 'Ratio_EL']
    df_stats = df[stats_cols].describe().T
    df_stats = df_stats.round(2)
    
    st.dataframe(df_stats, width='stretch')

# ─── TAB CORRÉLATIONS ───
with tab_corr:
    st.markdown("### 🔗 Matrice de Corrélation")
    
    # Sélectionner colonnes numériques disponibles
    numeric_cols = []
    for col in ['Résistance', 'Diffusion_Cl', 'Carbonatation', 
               'Ratio_EL', 'ciment', 'eau', 'sable', 'gravier', 'age']:
        if col in df.columns:
            numeric_cols.append(col)
    
    if len(numeric_cols) < 2:
        st.warning("⚠️ Pas assez de colonnes numériques pour calculer les corrélations")
    else:
        # Calcul corrélation
        df_corr = df[numeric_cols].corr(method='pearson')

        # Heatmap
        fig_corr = px.imshow(
            df_corr,
            text_auto='.2f',
            aspect='auto',
            color_continuous_scale='RdBu_r',
            zmin=-1,
            zmax=1,
            labels=dict(color="Corrélation")
        )

        fig_corr.update_layout(
            title="Matrice de Corrélation (Pearson)",
            height=600
        )

        st.plotly_chart(fig_corr, width='stretch')

        # ─────────────────────────────────────────────
        # 🔝 Extraction optimisée des top corrélations
        # ─────────────────────────────────────────────

        st.markdown("#### 🔝 Corrélations Fortes")

        # Matrice sans diagonale
        corr_matrix = df_corr.where(~np.eye(len(df_corr), dtype=bool))

        # Transformer en format long
        corr_pairs = (
            corr_matrix
            .stack()
            .reset_index()
            .rename(columns={
                'level_0': 'Variable 1',
                'level_1': 'Variable 2',
                0: 'Corrélation'
            })
        )

        # Supprimer doublons (A-B et B-A)
        corr_pairs['pair'] = corr_pairs.apply(
            lambda x: tuple(sorted([x['Variable 1'], x['Variable 2']])),
            axis=1
        )
        corr_pairs = corr_pairs.drop_duplicates('pair').drop(columns='pair')

        # Filtrer corrélations significatives
        corr_pairs = corr_pairs[abs(corr_pairs['Corrélation']) > 0.1]

        if not corr_pairs.empty:
            corr_pairs = (
                corr_pairs
                .sort_values('Corrélation', key=abs, ascending=False)
                .head(10)
            )

            corr_pairs['Corrélation'] = corr_pairs['Corrélation'].round(3)

            st.dataframe(
                corr_pairs,
                width='stretch'
            )
        else:
            st.info("ℹ️ Aucune corrélation significative détectée")

# ─── TAB ÉVOLUTION TEMPORELLE ───
with tab_time:
    st.markdown("### 📅 Évolution dans le Temps")
    
    if 'Date' in df.columns and len(df) > 0:
        # Trier par date
        df_sorted = df.sort_values('Date')
        
        # Grouper par jour
        df_daily = df_sorted.groupby(df_sorted['Date'].dt.date).agg({
            'Résistance': ['mean', 'count'],
            'Diffusion_Cl': 'mean',
            'Carbonatation': 'mean'
        }).reset_index()
        
        # Aplatir colonnes
        df_daily.columns = ['Date', 'Résistance_Moy', 'Nombre', 'Diffusion_Moy', 'Carbonatation_Moy']
        
        # Graphique principal
        fig_time = go.Figure()
        
        fig_time.add_trace(go.Scatter(
            x=df_daily['Date'],
            y=df_daily['Résistance_Moy'],
            mode='lines+markers',
            name='Résistance Moy.',
            line=dict(color=COLOR_PALETTE['primary'], width=3),
            marker=dict(size=8)
        ))
        
        fig_time.update_layout(
            title="Résistance Moyenne par Jour",
            xaxis_title="Date",
            yaxis_title="Résistance (MPa)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_time, width='stretch')
        
        # Nombre de prédictions par jour
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            fig_count = px.bar(
                df_daily,
                x='Date',
                y='Nombre',
                title="Nombre de Prédictions par Jour",
                color_discrete_sequence=[COLOR_PALETTE['accent']]
            )
            fig_count.update_layout(height=300)
            st.plotly_chart(fig_count, width='stretch')
        
        with col_t2:
            # Tendance globale
            df_trend = df_sorted[['Date', 'Résistance']].copy()
            df_trend['Timestamp'] = df_trend['Date'].astype('int64') // 10**9
            
            if len(df_trend) > 2:
                import numpy as np
                z = np.polyfit(df_trend['Timestamp'], df_trend['Résistance'], 1)
                p = np.poly1d(z)
                df_trend['Tendance'] = p(df_trend['Timestamp'])
                
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_trend['Date'],
                    y=df_trend['Résistance'],
                    mode='markers',
                    name='Données',
                    marker=dict(size=6, opacity=0.5)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=df_trend['Date'],
                    y=df_trend['Tendance'],
                    mode='lines',
                    name='Tendance',
                    line=dict(color='red', width=2, dash='dash')
                ))
                fig_trend.update_layout(
                    title="Tendance Résistance",
                    height=300
                )
                st.plotly_chart(fig_trend, width='stretch')
    else:
        st.info("ℹ️ Pas de données temporelles disponibles")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# TABLEAU DÉTAILLÉ
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📋 Historique Détaillé")

# Colonnes à afficher
display_cols = []
for col in ['Formulation', 'Résistance', 'Diffusion_Cl', 
           'Carbonatation', 'Ratio_EL', 'ciment', 'eau', 'Date']:
    if col in df.columns:
        display_cols.append(col)

df_display = df[display_cols].copy()

# Formatter les dates
if 'Date' in df_display.columns:
    df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d %H:%M')

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
        'Ratio_EL': '{:.3f}',
        'ciment': '{:.0f}',
        'eau': '{:.0f}'
    }),
    width='stretch',
    height=400
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📥 Export des Données")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    csv = df.to_csv(index=False, date_format='%Y-%m-%d %H:%M:%S')
    st.download_button(
        "📥 Télécharger CSV",
        data=csv,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        width='stretch'
    )

with col_export2:
    try:
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Historique')
            
            # Stats
            df[numeric_cols].describe().to_excel(writer, sheet_name='Statistiques')
        
        st.download_button(
            "📥 Télécharger Excel",
            data=buffer.getvalue(),
            file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch'
        )
    except Exception as e:
        st.error(f"❌ Erreur export Excel: {str(e)}")

with col_export3:
    # Export JSON
    json_data = df.to_json(orient='records', date_format='iso', indent=2)
    st.download_button(
        "📥 Télécharger JSON",
        data=json_data,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        width='stretch'
    )

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

# Résumé stats
col_foot1, col_foot2, col_foot3, col_foot4 = st.columns(4)

with col_foot1:
    st.caption(f"📊 **Période** : {period}")

with col_foot2:
    st.caption(f"🔍 **Filtre résistance** : ≥ {min_resistance} MPa")

with col_foot3:
    date_min = df['Date'].min().strftime('%Y-%m-%d')
    date_max = df['Date'].max().strftime('%Y-%m-%d')
    st.caption(f"📅 **Plage** : {date_min} → {date_max}")

with col_foot4:
    st.caption(f"📈 **Chargées** : {len(df)}/{limit}")

st.caption("💡 **Astuce** : Utilisez les filtres en haut pour affiner l'analyse")