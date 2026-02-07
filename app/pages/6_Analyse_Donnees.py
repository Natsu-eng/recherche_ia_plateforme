"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: 6_📈_Analyse_Donnees.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Import, exploration et analyse statistique de données béton
Version: 3.0.0 - Interface Recherche
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import sys
from pathlib import Path

# Import modules locaux
sys.path.append(str(Path(__file__).parent.parent))
from app.components.navbar import render_top_nav
from app.components.cards import render_kpi_card, render_info_card
from app.components.tables import create_download_buttons
from app.styles.theme import apply_custom_theme
from config.settings import UI_SETTINGS, EXPORT_SETTINGS

# =============================================================================
# CONFIGURATION PAGE
# =============================================================================

st.set_page_config(
    page_title="Analyse de Données - IMT Nord Europe",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_theme()
render_top_nav(active_page="analyse")

# =============================================================================
# SESSION STATE INITIALISATION
# =============================================================================

if 'uploaded_df' not in st.session_state:
    st.session_state.uploaded_df = None
if 'analysis_report' not in st.session_state:
    st.session_state.analysis_report = {}

# =============================================================================
# HEADER HERO
# =============================================================================

st.markdown(f"""
<div style='background: linear-gradient(135deg, #6A1B9A 0%, #8E24AA 100%);
            padding: 3rem 2rem; border-radius: 20px; margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);'>
    <div style='display: flex; align-items: center; gap: 2rem;'>
        <div style='flex: 1;'>
            <h1 style='color: white; margin: 0; font-size: 2.8em; 
                       text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                📈 Analyse Exploratoire de Données
            </h1>
            <p style='color: rgba(255,255,255,0.95); font-size: 1.2em; 
                      margin-top: 1rem; font-weight: 300; line-height: 1.6;'>
                Importez vos jeux de données expérimentaux béton et obtenez instantanément 
                des statistiques descriptives, visualisations et analyses de corrélation
            </p>
            <div style='display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap;'>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>📁 Formats :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        CSV, Excel, JSON
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>📊 Analyses :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Statistiques, Corrélations, Distributions
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>🔍 Visualisations :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Histogrammes, Nuages, Matrices
                    </span>
                </div>
            </div>
        </div>
        <div style='font-size: 5em; opacity: 0.8;'>
            📈
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def load_data(uploaded_file):
    """Charge un fichier CSV, Excel ou JSON en DataFrame."""
    try:
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        elif file_name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        else:
            st.error("Format non supporté. Utilisez CSV, Excel ou JSON.")
            return None
        
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement : {str(e)}")
        return None

def compute_statistical_report(df):
    """Calcule un rapport statistique complet."""
    report = {
        'basic_info': {
            'nb_lignes': len(df),
            'nb_colonnes': len(df.columns),
            'types_donnees': df.dtypes.to_dict(),
            'valeurs_manquantes': df.isnull().sum().to_dict()
        },
        'statistics': df.describe(include='all').to_dict(),
        'correlations': df.select_dtypes(include=[np.number]).corr().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
    }
    return report

# =============================================================================
# MAIN LAYOUT - TWO COLUMNS
# =============================================================================

col_left, col_right = st.columns([1.2, 1.8], gap="large")

# =============================================================================
# LEFT COLUMN - DATA UPLOAD & MANAGEMENT
# =============================================================================

with col_left:
    st.markdown("### 📤 Importation des Données")
    
    # Section 1: Upload de fichier
    uploaded_file = st.file_uploader(
        "Déposez votre fichier de données béton",
        type=['csv', 'xlsx', 'xls', 'json'],
        help="Formats acceptés : CSV, Excel (xlsx, xls), JSON"
    )
    
    if uploaded_file:
        if st.button("📥 Charger et Analyser", type="primary", use_container_width=True):
            with st.spinner("Analyse des données en cours..."):
                df = load_data(uploaded_file)
                if df is not None:
                    st.session_state.uploaded_df = df
                    st.session_state.analysis_report = compute_statistical_report(df)
                    st.success(f"✅ {len(df)} lignes × {len(df.columns)} colonnes chargées")
    
    # Section 2: Gestion des données
    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        
        st.markdown("---")
        st.markdown("### 🛠️ Prétraitement des Données")
        
        # Aperçu des données
        with st.expander("👁️ Aperçu des Données (10 premières lignes)"):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Nettoyage des données
        st.markdown("#### 🧹 Nettoyage")
        
        if st.button("Supprimer les doublons", use_container_width=True):
            initial_len = len(df)
            df = df.drop_duplicates()
            st.session_state.uploaded_df = df
            st.info(f"Doublons supprimés : {initial_len - len(df)} lignes")
        
        # Sélection des colonnes
        st.markdown("#### 🎯 Sélection des Variables")
        selected_columns = st.multiselect(
            "Choisissez les colonnes à analyser :",
            options=df.columns.tolist(),
            default=df.columns.tolist()[:min(8, len(df.columns))]
        )
        
        if selected_columns:
            df = df[selected_columns]
            st.session_state.uploaded_df = df

# =============================================================================
# RIGHT COLUMN - DATA ANALYSIS & VISUALIZATION
# =============================================================================

with col_right:
    if st.session_state.uploaded_df is None:
        st.info("""
        ## 📊 Commencez votre analyse exploratoire
        
        **Pour démarrer :**
        1. **Importez vos données** dans la colonne de gauche
        2. **Visualisez un aperçu** de votre jeu de données
        3. **Appliquez des prétraitements** si nécessaire
        4. **Explorez les analyses** automatiques générées ici
        
        **Analyses disponibles :**
        - 📋 **Statistiques descriptives** complètes
        - 🔗 **Matrices de corrélation** interactives
        - 📉 **Distributions** et histogrammes
        - ☁️ **Nuages de points** et relations
        - 📤 **Export** des résultats et rapports
        """)
        
        # Dataset d'exemple
        st.markdown("---")
        st.markdown("### 💡 Exemple de Jeu de Données")
        
        example_data = pd.DataFrame({
            'Ciment': np.random.uniform(200, 500, 50),
            'Eau': np.random.uniform(150, 200, 50),
            'Resistance': np.random.uniform(20, 60, 50),
            'Diffusion_Cl': np.random.uniform(5, 15, 50),
            'Carbonatation': np.random.uniform(5, 25, 50),
            'Classe': np.random.choice(['C25/30', 'C30/37', 'C35/45'], 50)
        })
        
        st.dataframe(example_data.head(), use_container_width=True)
        st.caption("Exemple de structure de données béton pour l'analyse")
        
        st.stop()
    
    # Affichage des analyses
    df = st.session_state.uploaded_df
    report = st.session_state.analysis_report
    
    st.markdown(f"### 🔍 Analyse du Jeu de Données")
    st.caption(f"**{len(df)} observations** × **{len(df.columns)} variables** | "
               f"**{df.select_dtypes(include=[np.number]).shape[1]} variables numériques**")
    
    # Section 1: Statistiques descriptives
    st.markdown("#### 📋 Statistiques Descriptives")
    
    with st.expander("Afficher les statistiques détaillées", expanded=True):
        st.dataframe(df.describe(), use_container_width=True)
    
    # Métriques clés
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        if 'Resistance' in df.columns:
            avg_res = df['Resistance'].mean()
            render_kpi_card("Résistance Moyenne", f"{avg_res:.1f}", "MPa", "blue", "🏗️")
    
    with col_stat2:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            avg_corr = df[numeric_cols].corr().abs().mean().mean()
            render_kpi_card("Corrélation Moyenne", f"{avg_corr:.2f}", "", "green", "🔗")
    
    with col_stat3:
        missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        render_kpi_card("Valeurs Manquantes", f"{missing_pct:.1f}", "%", "orange" if missing_pct > 5 else "green", "⚠️")
    
    with col_stat4:
        unique_ratio = df.nunique().mean() / len(df) * 100
        render_kpi_card("Diversité", f"{unique_ratio:.1f}", "%", "purple", "🎯")
    
    # Section 2: Visualisations
    st.markdown("#### 📊 Visualisations Interactives")
    
    viz_type = st.selectbox(
        "Type de visualisation :",
        ["Histogramme", "Nuage de points", "Matrice de corrélation", "Box Plot"],
        index=0
    )
    
    if viz_type == "Histogramme":
        col_hist = st.selectbox("Colonne pour l'histogramme :", 
                               df.select_dtypes(include=[np.number]).columns.tolist(),
                               index=0)
        
        fig_hist = px.histogram(df, x=col_hist, nbins=30, 
                               title=f"Distribution de {col_hist}",
                               color_discrete_sequence=['#1976D2'])
        st.plotly_chart(fig_hist, use_container_width=True)
    
    elif viz_type == "Nuage de points":
        col_x = st.selectbox("Axe X :", df.select_dtypes(include=[np.number]).columns.tolist(), index=0)
        col_y = st.selectbox("Axe Y :", df.select_dtypes(include=[np.number]).columns.tolist(), index=1)
        
        if 'Classe' in df.columns:
            color_col = 'Classe'
        else:
            color_col = None
        
        fig_scatter = px.scatter(df, x=col_x, y=col_y, color=color_col,
                                title=f"{col_y} en fonction de {col_x}",
                                trendline="ols" if color_col is None else None)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    elif viz_type == "Matrice de corrélation":
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmin=-1, zmax=1,
                text=corr_matrix.round(2).values,
                texttemplate='%{text}',
                hoverinfo='text'
            ))
            
            fig_corr.update_layout(title="Matrice de Corrélation",
                                  height=500)
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.warning("Pas assez de variables numériques pour la matrice de corrélation")
    
    elif viz_type == "Box Plot":
        box_col = st.selectbox("Variable à visualiser :", 
                              df.select_dtypes(include=[np.number]).columns.tolist(),
                              index=0)
        
        if 'Classe' in df.columns:
            fig_box = px.box(df, x='Classe', y=box_col, 
                            title=f"Distribution de {box_col} par Classe")
        else:
            fig_box = px.box(df, y=box_col, title=f"Distribution de {box_col}")
        
        st.plotly_chart(fig_box, use_container_width=True)
    
    # Section 3: Export des résultats
    st.markdown("---")
    st.markdown("### 📤 Export des Analyses")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Export DataFrame
        csv = df.to_csv(index=False)
        st.download_button(
            label="💾 Données (CSV)",
            data=csv,
            file_name=f"donnees_beton_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_exp2:
        # Export Statistiques
        stats_df = df.describe()
        stats_csv = stats_df.to_csv()
        st.download_button(
            label="📊 Statistiques (CSV)",
            data=stats_csv,
            file_name=f"statistiques_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_exp3:
        # Export Rapport
        report_json = pd.io.json.dumps(report, indent=2)
        st.download_button(
            label="📝 Rapport (JSON)",
            data=report_json,
            file_name=f"rapport_analyse_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0; color: #666;'>
    <p style='margin-bottom: 0.5rem;'>
        <strong>📈 Analyse Exploratoire de Données Béton</strong> • Version 3.0.0 • IMT Nord Europe
    </p>
    <p style='font-size: 0.9em; color: #888;'>
        Outil d'exploration et de visualisation de données expérimentales • © 2024
    </p>
</div>
""", unsafe_allow_html=True)