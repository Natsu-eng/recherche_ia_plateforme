"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Analyse de Données — Historique & Tendances
Fichier: pages/5_Analyse_de_Données.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Corrigé & Production Ready
═══════════════════════════════════════════════════════════════════════════════

CORRECTIONS v1.0.0 (depuis v1.1.0):
  ✅ width='stretch' → use_container_width=True sur st.dataframe,
     st.plotly_chart et st.download_button (partout)
  ✅ numeric_cols défini au niveau du bloc principal (après chargement df)
     et non plus seulement dans tab_corr → plus de NameError dans l'export Excel
  ✅ Formatage de date robuste (isoformat au lieu de strftime sur NaT)
"""

import streamlit as st
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import info_box

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Analytics - Béton IA",
    page_icon="📈",
    layout="wide",
)

apply_custom_theme(st.session_state.get("app_theme", "Clair"))
render_sidebar(db_manager=st.session_state.get("db_manager"))

from app.components.navbar import render_navbar
render_navbar(current_page="Analyse de Données")

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color:{COLOR_PALETTE['primary']};border-bottom:3px solid {COLOR_PALETTE['accent']};padding-bottom:0.5rem;">
        📈 Analyse de Données — Historique & Tendances
    </h1>
    <p style="font-size:1.1rem;color:{COLOR_PALETTE['secondary']};margin-top:0.5rem;">
        Visualisez l'historique de vos prédictions et identifiez les tendances.
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION DB
# ═══════════════════════════════════════════════════════════════════════════════

db_manager = st.session_state.get("db_manager")

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
        index=1,
    )

with col_filter2:
    min_resistance = st.number_input(
        "Résistance Min (MPa)", min_value=0.0, max_value=100.0, value=0.0, step=5.0
    )

with col_filter3:
    limit = st.number_input(
        "Nombre Max", min_value=10, max_value=1000, value=100, step=10
    )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

with st.spinner("🔄 Chargement de l'historique…"):
    try:
        days_filter = {"7 derniers jours": 7, "30 derniers jours": 30}.get(period, 36500)

        # Requête paramétrisée (protection injection SQL)
        query = """
        SELECT
            id,
            nom_formulation,
            resistance_predite,
            diffusion_cl_predite,
            carbonatation_predite,
            ratio_eau_liaison,
            ciment, laitier, cendres, eau, sable, gravier, adjuvants,
            jours_cure AS age,
            horodatage  AS created_at
        FROM predictions
        WHERE resistance_predite >= %s
          AND resistance_predite IS NOT NULL
          AND horodatage > NOW() - INTERVAL '%s days'
        ORDER BY horodatage DESC
        LIMIT %s
        """
        params  = (min_resistance, days_filter, limit)
        results = db_manager.execute_query(query, params=params, fetch=True)

        if not results:
            st.info("ℹ️ Aucune donnée disponible avec ces filtres.")
            st.info("💡 Essayez d'élargir la période ou de baisser le seuil de résistance")
            try:
                count_result = db_manager.execute_query(
                    "SELECT COUNT(*) AS total FROM predictions", fetch=True
                )
                if count_result:
                    st.info(f"📊 Total de prédictions en base : {count_result[0]['total']}")
            except Exception:
                pass
            st.stop()

        # ── Construction DataFrame ───────────────────────────────────────────
        df = pd.DataFrame(results).rename(columns={
            "nom_formulation":      "Formulation",
            "resistance_predite":   "Résistance",
            "diffusion_cl_predite": "Diffusion_Cl",
            "carbonatation_predite":"Carbonatation",
            "ratio_eau_liaison":    "Ratio_EL",
            "created_at":           "Date",
        })

        # Conversion Decimal → float (PostgreSQL retourne Decimal)
        _numeric_raw = [
            "Résistance", "Diffusion_Cl", "Carbonatation", "Ratio_EL",
            "ciment", "laitier", "cendres", "eau", "sable", "gravier", "adjuvants", "age",
        ]
        for col in _numeric_raw:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Diffusion_Cl"]  = df["Diffusion_Cl"].fillna(0.0)
        df["Carbonatation"] = df["Carbonatation"].fillna(0.0)
        df["Ratio_EL"]      = df["Ratio_EL"].fillna(0.5)

        # ✅ numeric_cols défini ici au niveau du bloc principal →
        # accessible dans TOUS les onglets ET dans l'export Excel
        numeric_cols = [
            c for c in [
                "Résistance", "Diffusion_Cl", "Carbonatation",
                "Ratio_EL", "ciment", "eau", "sable", "gravier", "age",
            ]
            if c in df.columns
        ]

        st.success(f"✅ {len(df)} prédictions chargées")

    except Exception as e:
        logger.error("Erreur chargement: %s", e, exc_info=True)
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
    st.metric("📊 Prédictions", f"{len(df):,}")

with col_stat2:
    st.metric(
        "💪 Résistance Moyenne",
        f"{df['Résistance'].mean():.1f} MPa",
        delta=f"σ = {df['Résistance'].std():.1f}",
    )

with col_stat3:
    st.metric(
        "🧂 Diffusion Cl⁻ Moy.",
        f"{df['Diffusion_Cl'].mean():.2f}",
        delta=f"σ = {df['Diffusion_Cl'].std():.2f}",
    )

with col_stat4:
    st.metric(
        "🌫️ Carbonatation Moy.",
        f"{df['Carbonatation'].mean():.1f} mm",
        delta=f"σ = {df['Carbonatation'].std():.1f}",
    )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUES
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📈 Visualisations")

tab_trends, tab_distrib, tab_corr, tab_time = st.tabs([
    "Tendances", "Distributions", "Corrélations", "Évolution Temporelle"
])

# ─── TENDANCES ────────────────────────────────────────────────────────────────
with tab_trends:
    st.markdown("### 📊 Tendances des Cibles")

    fig_trends = go.Figure()
    fig_trends.add_trace(go.Scatter(
        x=df.index, y=df["Résistance"],
        mode="lines+markers", name="Résistance (MPa)",
        line=dict(color=COLOR_PALETTE["primary"], width=2), marker=dict(size=5),
    ))
    fig_trends.add_trace(go.Scatter(
        x=df.index, y=df["Diffusion_Cl"],
        mode="lines+markers", name="Diffusion Cl⁻",
        yaxis="y2",
        line=dict(color=COLOR_PALETTE["success"], width=2), marker=dict(size=5),
    ))
    fig_trends.update_layout(
        title="Évolution des Propriétés",
        xaxis_title="Index (ordre chronologique inverse)",
        yaxis_title="Résistance (MPa)",
        yaxis2=dict(title="Diffusion Cl⁻", overlaying="y", side="right"),
        height=500, hovermode="x unified",
    )
    st.plotly_chart(fig_trends, use_container_width=True)   # ✅

# ─── DISTRIBUTIONS ────────────────────────────────────────────────────────────
with tab_distrib:
    st.markdown("### 📊 Distributions")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        fig_r = px.histogram(
            df, x="Résistance", nbins=30,
            title="Distribution Résistance",
            color_discrete_sequence=[COLOR_PALETTE["primary"]],
        )
        fig_r.update_layout(height=350)
        st.plotly_chart(fig_r, use_container_width=True)   # ✅

    with col_d2:
        fig_d = px.histogram(
            df, x="Diffusion_Cl", nbins=30,
            title="Distribution Diffusion Cl⁻",
            color_discrete_sequence=[COLOR_PALETTE["success"]],
        )
        fig_d.update_layout(height=350)
        st.plotly_chart(fig_d, use_container_width=True)   # ✅

    with col_d3:
        fig_c = px.histogram(
            df, x="Carbonatation", nbins=30,
            title="Distribution Carbonatation",
            color_discrete_sequence=[COLOR_PALETTE["warning"]],
        )
        fig_c.update_layout(height=350)
        st.plotly_chart(fig_c, use_container_width=True)   # ✅

    st.markdown("#### 📋 Statistiques Détaillées")
    stats_cols = [c for c in ["Résistance", "Diffusion_Cl", "Carbonatation", "Ratio_EL"] if c in df.columns]
    st.dataframe(df[stats_cols].describe().T.round(2), use_container_width=True)   # ✅

# ─── CORRÉLATIONS ─────────────────────────────────────────────────────────────
with tab_corr:
    st.markdown("### 🔗 Matrice de Corrélation")

    if len(numeric_cols) < 2:
        st.warning("⚠️ Pas assez de colonnes numériques pour calculer les corrélations")
    else:
        df_corr = df[numeric_cols].corr(method="pearson")

        fig_corr = px.imshow(
            df_corr, text_auto=".2f", aspect="auto",
            color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
            labels=dict(color="Corrélation"),
        )
        fig_corr.update_layout(title="Matrice de Corrélation (Pearson)", height=600)
        st.plotly_chart(fig_corr, use_container_width=True)   # ✅

        # Top corrélations
        st.markdown("#### 🔝 Corrélations Fortes")
        corr_matrix = df_corr.where(~np.eye(len(df_corr), dtype=bool))
        corr_pairs = (
            corr_matrix.stack()
            .reset_index()
            .rename(columns={"level_0": "Variable 1", "level_1": "Variable 2", 0: "Corrélation"})
        )
        corr_pairs["pair"] = corr_pairs.apply(
            lambda x: tuple(sorted([x["Variable 1"], x["Variable 2"]])), axis=1
        )
        corr_pairs = corr_pairs.drop_duplicates("pair").drop(columns="pair")
        corr_pairs = corr_pairs[corr_pairs["Corrélation"].abs() > 0.1]

        if not corr_pairs.empty:
            top_corr = (
                corr_pairs.sort_values("Corrélation", key=abs, ascending=False)
                .head(10)
            )
            top_corr["Corrélation"] = top_corr["Corrélation"].round(3)
            st.dataframe(top_corr, use_container_width=True)   # ✅
        else:
            st.info("ℹ️ Aucune corrélation significative détectée")

# ─── ÉVOLUTION TEMPORELLE ─────────────────────────────────────────────────────
with tab_time:
    st.markdown("### 📅 Évolution dans le Temps")

    if "Date" in df.columns and len(df) > 0 and df["Date"].notna().any():
        df_sorted = df.sort_values("Date")

        df_daily = (
            df_sorted.groupby(df_sorted["Date"].dt.date)
            .agg(
                Résistance_Moy=("Résistance", "mean"),
                Nombre=("Résistance", "count"),
                Diffusion_Moy=("Diffusion_Cl", "mean"),
                Carbonatation_Moy=("Carbonatation", "mean"),
            )
            .reset_index()
            .rename(columns={"Date": "Date"})
        )

        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(
            x=df_daily["Date"], y=df_daily["Résistance_Moy"],
            mode="lines+markers", name="Résistance Moy.",
            line=dict(color=COLOR_PALETTE["primary"], width=3), marker=dict(size=8),
        ))
        fig_time.update_layout(
            title="Résistance Moyenne par Jour",
            xaxis_title="Date", yaxis_title="Résistance (MPa)",
            height=400, hovermode="x unified",
        )
        st.plotly_chart(fig_time, use_container_width=True)   # ✅

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            fig_count = px.bar(
                df_daily, x="Date", y="Nombre",
                title="Nombre de Prédictions par Jour",
                color_discrete_sequence=[COLOR_PALETTE["accent"]],
            )
            fig_count.update_layout(height=300)
            st.plotly_chart(fig_count, use_container_width=True)   # ✅

        with col_t2:
            df_trend = df_sorted[["Date", "Résistance"]].copy()
            df_trend["Timestamp"] = df_trend["Date"].astype("int64") // 10**9

            if len(df_trend) > 2:
                z = np.polyfit(df_trend["Timestamp"], df_trend["Résistance"], 1)
                p = np.poly1d(z)
                df_trend["Tendance"] = p(df_trend["Timestamp"])

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_trend["Date"], y=df_trend["Résistance"],
                    mode="markers", name="Données",
                    marker=dict(size=6, opacity=0.5),
                ))
                fig_trend.add_trace(go.Scatter(
                    x=df_trend["Date"], y=df_trend["Tendance"],
                    mode="lines", name="Tendance",
                    line=dict(color="red", width=2, dash="dash"),
                ))
                fig_trend.update_layout(title="Tendance Résistance", height=300)
                st.plotly_chart(fig_trend, use_container_width=True)   # ✅
    else:
        st.info("ℹ️ Pas de données temporelles disponibles")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# TABLEAU DÉTAILLÉ
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📋 Historique Détaillé")

display_cols = [
    c for c in ["Formulation", "Résistance", "Diffusion_Cl",
                "Carbonatation", "Ratio_EL", "ciment", "eau", "Date"]
    if c in df.columns
]
df_display = df[display_cols].copy()

# ✅ Formatage date robuste (évite strftime sur NaT)
if "Date" in df_display.columns:
    df_display["Date"] = df_display["Date"].apply(
        lambda d: d.strftime("%Y-%m-%d %H:%M") if pd.notna(d) else ""
    )

format_map = {
    "Résistance":   "{:.2f}",
    "Diffusion_Cl": "{:.2f}",
    "Carbonatation":"{:.2f}",
    "Ratio_EL":     "{:.3f}",
    "ciment":       "{:.0f}",
    "eau":          "{:.0f}",
}
active_format = {k: v for k, v in format_map.items() if k in df_display.columns}

highlight_max_cols = [c for c in ["Résistance"] if c in df_display.columns]
highlight_min_cols = [c for c in ["Diffusion_Cl", "Carbonatation"] if c in df_display.columns]

styled = df_display.style.format(active_format)
if highlight_max_cols:
    styled = styled.highlight_max(subset=highlight_max_cols, color="lightgreen")
if highlight_min_cols:
    styled = styled.highlight_min(subset=highlight_min_cols, color="lightgreen")

st.dataframe(styled, use_container_width=True, height=400)   # ✅

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📥 Export des Données")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    csv = df.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S")
    st.download_button(
        "📥 Télécharger CSV",
        data=csv,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,   # ✅
    )

with col_export2:
    try:
        from io import BytesIO
        buffer = BytesIO()

        # ✅ numeric_cols accessible ici car défini au niveau bloc principal
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Historique")
            if numeric_cols:
                df[numeric_cols].describe().to_excel(writer, sheet_name="Statistiques")

        st.download_button(
            "📥 Télécharger Excel",
            data=buffer.getvalue(),
            file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,   # ✅
        )
    except Exception as e:
        st.error(f"❌ Erreur export Excel : {e}")

with col_export3:
    json_data = df.to_json(orient="records", date_format="iso", indent=2)
    st.download_button(
        "📥 Télécharger JSON",
        data=json_data,
        file_name=f"historique_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True,   # ✅
    )

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

col_foot1, col_foot2, col_foot3, col_foot4 = st.columns(4)

with col_foot1:
    st.caption(f"📊 **Période** : {period}")
with col_foot2:
    st.caption(f"🔍 **Filtre résistance** : ≥ {min_resistance} MPa")
with col_foot3:
    date_min = df["Date"].min()
    date_max = df["Date"].max()
    fmt_min  = date_min.strftime("%Y-%m-%d") if pd.notna(date_min) else "N/A"
    fmt_max  = date_max.strftime("%Y-%m-%d") if pd.notna(date_max) else "N/A"
    st.caption(f"📅 **Plage** : {fmt_min} → {fmt_max}")
with col_foot4:
    st.caption(f"📈 **Chargées** : {len(df)}/{int(limit)}")

st.caption("💡 **Astuce** : Utilisez les filtres en haut pour affiner l'analyse")