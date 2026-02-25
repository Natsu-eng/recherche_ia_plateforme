"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Configuration - Diagnostics et Paramètres
Fichier: pages/6_Configuration.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.1.0 - CORRECTIFS
═══════════════════════════════════════════════════════════════════════════════

CORRECTIFS v1.1.0:
✅ Initialisation session_state
✅ Gestion erreurs robuste
✅ width='stretch' (pas deprecated)
✅ Imports sécurisés
✅ Diagnostics DB améliorés
"""

import streamlit as st
import logging
from pathlib import Path
import sys
import pandas as pd

from config.settings import (
    APP_SETTINGS,
    MODEL_SETTINGS,
    POSTGRES_SETTINGS
)
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar

from app.core.session_manager import initialize_session

# ✅ INITIALISER SESSION
initialize_session()

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

from app.components.navbar import render_navbar
render_navbar(current_page="Configuration")

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        ⚙️ Configuration & Diagnostics
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Paramètres système, diagnostics et tests de santé.
    </p>
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
        
        st.markdown(f"**Nom** : {APP_SETTINGS.get('app_name', 'N/A')}")
        st.markdown(f"**Version** : {APP_SETTINGS.get('version', 'N/A')}")
        st.markdown(f"**Date Release** : {APP_SETTINGS.get('release_date', 'N/A')}")
        st.markdown(f"**Institution** : {APP_SETTINGS.get('institution', 'N/A')}")
        st.markdown(f"**Campus** : {APP_SETTINGS.get('campus', 'N/A')}")
    
    with col2:
        st.markdown("#### Contact")
        
        st.markdown(f"**Email** : {APP_SETTINGS.get('email', 'N/A')}")
        st.markdown(f"**Téléphone** : {APP_SETTINGS.get('phone', 'N/A')}")
        st.markdown(f"**Website** : {APP_SETTINGS.get('website', 'N/A')}")
    
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
    
    st.markdown("---")
    
    st.markdown("#### 📈 Statistiques Session")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        pred_count = st.session_state.get('prediction_count', 0)
        st.metric("🔬 Prédictions", pred_count)
    
    with col_stat2:
        save_count = st.session_state.get('total_saves', 0)
        st.metric("💾 Sauvegardes", save_count)
    
    with col_stat3:
        fav_count = len(st.session_state.get('favorites', []))
        st.metric("⭐ Favoris", fav_count)

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
            
            model_path = MODEL_SETTINGS.get('model_path', 'N/A')
            features_path = MODEL_SETTINGS.get('features_path', 'N/A')
            metadata_path = MODEL_SETTINGS.get('metadata_path', 'N/A')
            
            st.markdown(f"**Modèle** : `{model_path}`")
            st.markdown(f"**Features** : `{features_path}`")
            st.markdown(f"**Métadonnées** : `{metadata_path}`")
            
            # Vérifier existence fichiers
            if model_path != 'N/A':
                model_exists = Path(model_path).exists()
                st.markdown(f"Fichier modèle : {'✅ Existant' if model_exists else '❌ Manquant'}")
        
        with col_m2:
            st.markdown("#### 🎯 Cibles Prédiction")
            
            targets = MODEL_SETTINGS.get('targets', [])
            units = MODEL_SETTINGS.get('units', {})
            
            for target in targets:
                unit = units.get(target, 'N/A')
                st.markdown(f"• **{target}** ({unit})")
        
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
                        feature_list=features,
                        validate=False
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
                    st.error(f"❌ Erreur test : {str(e)}")
                    logger.error(f"Test modèle échoué: {e}", exc_info=True)
    
    else:
        st.error("❌ Modèle non chargé")
        st.info("💡 Vérifiez les logs au démarrage de l'application")
        
        # Diagnostics
        st.markdown("#### 🔍 Diagnostics")
        
        if not model:
            st.warning("⚠️ Objet modèle absent dans session_state")
        if not features:
            st.warning("⚠️ Liste features absente dans session_state")
        if not metadata:
            st.warning("⚠️ Métadonnées absentes dans session_state")

# ───────────────────────────────────────────────────────────────────────────────
# TAB 3 : BASE DE DONNÉES
# ───────────────────────────────────────────────────────────────────────────────

with tab_db:
    st.markdown("### 🗄️ Base de Données PostgreSQL")
    
    db_manager = st.session_state.get('db_manager')
    
    if db_manager and db_manager.is_connected:
        st.success("✅ Connexion active")
        
        col_db1, col_db2 = st.columns(2)
        
        with col_db1:
            st.markdown("#### Configuration")
            
            # Masquer mot de passe
            db_url = POSTGRES_SETTINGS.get('database_url', 'N/A')
            
            if '@' in db_url:
                # Extraire host après @
                db_url_masked = db_url.split('@')[1] if '@' in db_url else db_url
                # Extraire user avant :
                user_part = db_url.split('://')[1].split(':')[0] if '://' in db_url else 'N/A'
                
                st.markdown(f"**User** : `{user_part}`")
                st.markdown(f"**Host** : `{db_url_masked}`")
            else:
                st.markdown(f"**URL** : `{db_url}`")
            
            st.markdown(f"**Pool size** : {POSTGRES_SETTINGS.get('pool_size', 5)}")
            st.markdown(f"**Max overflow** : {POSTGRES_SETTINGS.get('max_overflow', 10)}")
        
        with col_db2:
            st.markdown("#### Statistiques")
            
            try:
                stats = db_manager.get_live_stats()
                
                st.metric("Prédictions totales", f"{stats.get('total_predictions', 0):,}")
                st.metric("Formulations uniques", f"{stats.get('formulations_analyzed', 0):,}")
                st.metric("Résistance moyenne", f"{stats.get('avg_resistance', 0):.1f} MPa")
            
            except Exception as e:
                st.warning(f"⚠️ Impossible de récupérer les stats : {str(e)}")
                logger.error(f"Erreur stats DB: {e}", exc_info=True)
        
        st.markdown("---")
        
        st.markdown("#### 🔍 Diagnostics Avancés")
        
        try:
            diag = db_manager.get_diagnostics()
            
            col_diag1, col_diag2 = st.columns(2)
            
            with col_diag1:
                st.markdown("**PostgreSQL Version**")
                st.code(diag.get('postgresql_version', 'N/A')[:80], language="text")
                
                st.markdown("**Database**")
                st.code(diag.get('database', 'N/A'), language="text")
            
            with col_diag2:
                st.markdown("**User**")
                st.code(diag.get('user', 'N/A'), language="text")
                
                st.markdown("**Prédictions**")
                st.code(f"{diag.get('predictions_count', 0)} enregistrements", language="text")
        
        except AttributeError:
            st.info("ℹ️ Méthode get_diagnostics() non disponible (ancienne version DB Manager)")
        except Exception as e:
            st.warning(f"⚠️ Erreur diagnostics: {str(e)}")
        
        st.markdown("---")
        
        st.markdown("#### 🧪 Test Connexion")
        
        if st.button("🔄 Tester Connexion", type="primary"):
            with st.spinner("Test..."):
                try:
                    result = db_manager.execute_query("SELECT 1 as test", fetch=True)
                    if result and len(result) > 0 and result[0].get('test') == 1:
                        st.success("✅ Connexion fonctionnelle")
                    else:
                        st.error("❌ Réponse inattendue")
                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")
                    logger.error(f"Test connexion DB: {e}", exc_info=True)
    
    else:
        if db_manager and not db_manager.is_connected:
            st.error("❌ Base de données déconnectée")
            
            error = db_manager.connection_error
            if error:
                st.error(f"**Erreur** : {error}")
        else:
            st.warning("⚠️ Base de données non initialisée")
        
        st.markdown("#### Configuration attendue")
        
        db_url = POSTGRES_SETTINGS.get('database_url', 'N/A')
        if '@' in db_url:
            # Masquer password
            parts = db_url.split('@')
            user = parts[0].split('://')[-1].split(':')[0]
            host = parts[1]
            db_url_display = f"postgresql://{user}:****@{host}"
        else:
            db_url_display = db_url
        
        st.code(f"DATABASE_URL={db_url_display}", language="bash")
        
        st.markdown(
            """
            **Pour activer la base de données** :
            
            1. Installer PostgreSQL
            2. Créer la base `concrete_ai_platform`
            3. Configurer `.env` avec l'URL de connexion
            4. Redémarrer l'application
            
            **Fichier .env** :
            ```
            DATABASE_URL=postgresql://user:password@localhost:5432/concrete_ai_platform
            ```
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
    
    try:
        import psutil
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            cpu_percent = psutil.cpu_percent(interval=1)
            st.metric("CPU", f"{cpu_percent}%")
        
        with col_r2:
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_used_gb = mem.used / (1024**3)
            mem_total_gb = mem.total / (1024**3)
            st.metric(
                "RAM", 
                f"{mem_percent}%",
                delta=f"{mem_used_gb:.1f} / {mem_total_gb:.1f} GB"
            )
        
        with col_r3:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            st.metric(
                "Disque", 
                f"{disk_percent}%",
                delta=f"{disk_used_gb:.0f} / {disk_total_gb:.0f} GB"
            )
    
    except ImportError:
        st.warning("⚠️ Module psutil non installé. Impossible d'afficher les ressources.")
        st.info("💡 Installez avec : `pip install psutil`")
    
    except Exception as e:
        st.error(f"❌ Erreur récupération ressources : {str(e)}")
    
    st.markdown("---")
    
    st.markdown("#### 📦 Packages Installés")
    
    if st.button("📋 Afficher Packages"):
        try:
            import pkg_resources # type: ignore
            
            installed = []
            for dist in pkg_resources.working_set:
                try:
                    installed.append(f"{dist.key}=={dist.version}")
                except:
                    installed.append(f"{dist.key}==unknown")
            
            installed_sorted = sorted(installed)
            
            st.text_area(
                "Packages",
                value="\n".join(installed_sorted),
                height=300
            )
            
            st.info(f"📊 Total : {len(installed_sorted)} packages")
        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            st.info("💡 Essayez : `pip list` dans votre terminal")

# ═══════════════════════════════════════════════════════════════════════════════
# ACTIONS RAPIDES
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

st.markdown("### ⚡ Actions Rapides")

col_act1, col_act2, col_act3 = st.columns(3)

with col_act1:
    if st.button("🔄 Recharger Session", width='stretch'):
        # Réinitialiser compteurs
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ Session réinitialisée")
        st.rerun()

with col_act2:
    if st.button("🧹 Vider Favoris", width='stretch'):
        st.session_state['favorites'] = []
        st.success("✅ Favoris vidés")

with col_act3:
    if st.button("📊 Afficher Session State", width='stretch'):
        st.json(dict(st.session_state))

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

col_footer1, col_footer2 = st.columns(2)

with col_footer1:
    st.caption("💡 **Conseil** : Surveillez régulièrement l'état de la connexion DB")

with col_footer2:
    st.caption(f"🔧 **Support** : {APP_SETTINGS.get('email', 'N/A')}")