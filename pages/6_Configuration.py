"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Configuration - Diagnostics et Paramètres
Fichier: app/pages/6_Configuration.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import logging
from pathlib import Path
import sys
import psutil
import pandas as pd

from config.settings import (
    APP_SETTINGS,
    MODEL_SETTINGS,
    DATABASE_SETTINGS,
    POSTGRES_SETTINGS
)
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Configuration - Béton IA",
    page_icon="⚙️",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']};">
        ⚙️ Configuration & Diagnostics
    </h1>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# ONGLETS
# ═══════════════════════════════════════════════════════════════════════════════

tab_app, tab_model, tab_db, tab_system = st.tabs([
    "📱 Application",
    "🤖 Modèle ML",
    "🗄️ Base de Données",
    "💻 Système"
])

# ───────────────────────────────────────────────────────────────────────────────
# TAB 1 : APPLICATION
# ───────────────────────────────────────────────────────────────────────────────

with tab_app:
    st.markdown("### 📱 Paramètres Application")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Informations Générales")
        
        st.markdown(f"**Nom** : {APP_SETTINGS['app_name']}")
        st.markdown(f"**Version** : {APP_SETTINGS['version']}")
        st.markdown(f"**Date Release** : {APP_SETTINGS['release_date']}")
        st.markdown(f"**Institution** : {APP_SETTINGS['institution']}")
        st.markdown(f"**Campus** : {APP_SETTINGS['campus']}")
    
    with col2:
        st.markdown("#### Contact")
        
        st.markdown(f"**Email** : {APP_SETTINGS['email']}")
        st.markdown(f"**Téléphone** : {APP_SETTINGS['phone']}")
        st.markdown(f"**Website** : {APP_SETTINGS['website']}")
    
    st.markdown("---")
    
    st.markdown("#### 🎛️ Fonctionnalités Actives")
    
    features_status = {
        "Prédictions": APP_SETTINGS.get('enable_predictions', True),
        "Comparaisons": APP_SETTINGS.get('enable_comparisons', True),
        "Optimisation": APP_SETTINGS.get('enable_optimization', True),
        "Laboratoire": APP_SETTINGS.get('enable_laboratory', True),
        "Analytics": APP_SETTINGS.get('enable_analytics', True),
        "Exports": APP_SETTINGS.get('enable_exports', True)
    }
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    for i, (feature, enabled) in enumerate(features_status.items()):
        col = [col_f1, col_f2, col_f3][i % 3]
        with col:
            icon = "✅" if enabled else "❌"
            st.markdown(f"{icon} **{feature}**")
    
    st.markdown("---")
    
    st.markdown("#### 📊 Limites")
    
    limits = {
        "Prédictions par session": APP_SETTINGS.get('max_predictions_per_session', 100),
        "Formulations en comparaison": APP_SETTINGS.get('max_formulations_comparison', 10),
        "Taille batch max": APP_SETTINGS.get('max_batch_size', 50),
        "Upload fichier (MB)": APP_SETTINGS.get('max_file_upload_mb', 10)
    }
    
    for limit_name, limit_value in limits.items():
        st.markdown(f"• **{limit_name}** : {limit_value}")

# ───────────────────────────────────────────────────────────────────────────────
# TAB 2 : MODÈLE ML
# ───────────────────────────────────────────────────────────────────────────────

with tab_model:
    st.markdown("### 🤖 Configuration Modèle ML")
    
    # Vérifier chargement modèle
    model = st.session_state.get('model')
    features = st.session_state.get('features')
    metadata = st.session_state.get('metadata')
    
    if model and features and metadata:
        st.success("✅ Modèle chargé avec succès")
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.markdown("#### 📁 Chemins")
            
            st.markdown(f"**Modèle** : `{MODEL_SETTINGS['model_path']}`")
            st.markdown(f"**Features** : `{MODEL_SETTINGS['features_path']}`")
            st.markdown(f"**Métadonnées** : `{MODEL_SETTINGS['metadata_path']}`")
            
            # Vérifier existence fichiers
            model_exists = Path(MODEL_SETTINGS['model_path']).exists()
            st.markdown(f"Fichier modèle : {'✅ Existant' if model_exists else '❌ Manquant'}")
        
        with col_m2:
            st.markdown("#### 🎯 Cibles Prédiction")
            
            for target in MODEL_SETTINGS['targets']:
                st.markdown(f"• **{target}** ({MODEL_SETTINGS['units'].get(target, 'N/A')})")
        
        st.markdown("---")
        
        st.markdown("#### 📈 Performances (Test Set)")
        
        perf_data = metadata.get('performance', {})
        
        col_p1, col_p2, col_p3 = st.columns(3)
        
        with col_p1:
            r2_resistance = perf_data.get('Resistance', 0)
            st.metric("R² Résistance", f"{r2_resistance:.3f}")
        
        with col_p2:
            r2_diffusion = perf_data.get('Diffusion_Cl', 0)
            st.metric("R² Diffusion Cl⁻", f"{r2_diffusion:.3f}")
        
        with col_p3:
            r2_carb = perf_data.get('Carbonatation', 0)
            st.metric("R² Carbonatation", f"{r2_carb:.3f}")
        
        st.markdown("---")
        
        st.markdown("#### 🧬 Features")
        
        st.markdown(f"**Nombre de features** : {len(features)}")
        
        with st.expander("📋 Liste complète des features"):
            for i, feat in enumerate(features, 1):
                st.markdown(f"{i}. `{feat}`")
        
        st.markdown("---")
        
        st.markdown("#### 🧪 Test Unitaire")
        
        if st.button("▶️ Tester Modèle (C25/30)", type="primary"):
            with st.spinner("Test en cours..."):
                try:
                    from app.core.predictor import predict_concrete_properties
                    
                    test_comp = {
                        "Ciment": 280.0,
                        "Laitier": 0.0,
                        "CendresVolantes": 0.0,
                        "Eau": 180.0,
                        "Superplastifiant": 0.0,
                        "GravilonsGros": 1100.0,
                        "SableFin": 750.0,
                        "Age": 28.0
                    }
                    
                    result = predict_concrete_properties(
                        composition=test_comp,
                        model=model,
                        feature_list=features
                    )
                    
                    st.success("✅ Test réussi !")
                    
                    col_t1, col_t2, col_t3 = st.columns(3)
                    
                    with col_t1:
                        st.metric("Résistance", f"{result['Resistance']:.2f} MPa")
                        st.caption("Attendu : ~25.8 MPa")
                    
                    with col_t2:
                        st.metric("Diffusion Cl⁻", f"{result['Diffusion_Cl']:.2f}")
                        st.caption("Attendu : ~7.76")
                    
                    with col_t3:
                        st.metric("Carbonatation", f"{result['Carbonatation']:.2f} mm")
                        st.caption("Attendu : ~16.7 mm")
                
                except Exception as e:
                    st.error(f"❌ Erreur test : {e}")
    
    else:
        st.error("❌ Modèle non chargé. Vérifiez les logs au démarrage.")

# ───────────────────────────────────────────────────────────────────────────────
# TAB 3 : BASE DE DONNÉES
# ───────────────────────────────────────────────────────────────────────────────

with tab_db:
    st.markdown("### 🗄️ Base de Données PostgreSQL")
    
    db_manager = st.session_state.get('db_manager')
    
    if db_manager:
        st.success("✅ Connexion active")
        
        col_db1, col_db2 = st.columns(2)
        
        with col_db1:
            st.markdown("#### Configuration")
            
            # Masquer mot de passe
            db_url = POSTGRES_SETTINGS['database_url']
            db_url_masked = db_url.split('@')[1] if '@' in db_url else db_url
            
            st.markdown(f"**Host** : `{db_url_masked}`")
            st.markdown(f"**Pool size** : {POSTGRES_SETTINGS['pool_size']}")
            st.markdown(f"**Max overflow** : {POSTGRES_SETTINGS['max_overflow']}")
        
        with col_db2:
            st.markdown("#### Statistiques")
            
            try:
                stats = db_manager.get_live_stats()
                
                st.metric("Prédictions totales", f"{stats.get('total_predictions', 0):,}")
                st.metric("Formulations uniques", f"{stats.get('formulations_analyzed', 0):,}")
                st.metric("Utilisateurs actifs (24h)", f"{stats.get('active_users', 0)}")
            
            except Exception as e:
                st.warning(f"⚠️ Impossible de récupérer les stats : {e}")
        
        st.markdown("---")
        
        st.markdown("#### 🧪 Test Connexion")
        
        if st.button("🔄 Tester Connexion", type="primary"):
            with st.spinner("Test..."):
                try:
                    result = db_manager.execute_query("SELECT 1 as test", fetch=True)
                    if result and result[0]['test'] == 1:
                        st.success("✅ Connexion fonctionnelle")
                    else:
                        st.error("❌ Réponse inattendue")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
    
    else:
        st.warning("⚠️ Base de données non connectée")
        
        st.markdown("#### Configuration attendue")
        st.code(f"DATABASE_URL={POSTGRES_SETTINGS['database_url']}", language="bash")
        
        st.markdown(
            """
            **Pour activer la base de données** :
            
            1. Installer PostgreSQL
            2. Créer la base `concrete_ai_platform`
            3. Configurer `.env` avec l'URL de connexion
            4. Redémarrer l'application
            """
        )

# ───────────────────────────────────────────────────────────────────────────────
# TAB 4 : SYSTÈME
# ───────────────────────────────────────────────────────────────────────────────

with tab_system:
    st.markdown("### 💻 Informations Système")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("#### Python")
        
        st.markdown(f"**Version** : {sys.version.split()[0]}")
        st.markdown(f"**Exécutable** : `{sys.executable}`")
        st.markdown(f"**Path** : `{sys.prefix}`")
    
    with col_s2:
        st.markdown("#### Streamlit")
        
        st.markdown(f"**Version** : {st.__version__}")
    
    st.markdown("---")
    
    st.markdown("#### 📊 Ressources")
    
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        cpu_percent = psutil.cpu_percent(interval=1)
        st.metric("CPU", f"{cpu_percent}%")
    
    with col_r2:
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        st.metric("RAM", f"{mem_percent}%")
    
    with col_r3:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        st.metric("Disque", f"{disk_percent}%")
    
    st.markdown("---")
    
    st.markdown("#### 📦 Packages Installés")
    
    if st.button("📋 Afficher Packages"):
        import importlib.metadata
        pkg_resources = importlib.metadata
        
        installed = [f"{pkg.key}=={pkg.version}" for pkg in pkg_resources.working_set]
        installed_sorted = sorted(installed)
        
        st.text_area(
            "Packages",
            value="\n".join(installed_sorted),
            height=300
        )

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("💡 Pour toute assistance technique, contactez support@imt-nord-europe.fr")