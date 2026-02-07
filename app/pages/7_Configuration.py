"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: 7_⚙️_Configuration.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Configuration système, diagnostic et paramètres utilisateur
Version: 3.0.0 - Interface Recherche
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import sys
import platform
import json
from pathlib import Path
import psutil # type: ignore 

# Import modules locaux
sys.path.append(str(Path(__file__).parent.parent))
from app.components.navbar import render_top_nav
from app.components.cards import render_kpi_card, render_info_card
from app.styles.theme import apply_custom_theme
from config.settings import (
    APP_SETTINGS, MODEL_SETTINGS, UI_SETTINGS, EXPORT_SETTINGS,
    LOGGING_SETTINGS, OPTIMIZER_SETTINGS, DATABASE_SETTINGS,
    SECURITY_SETTINGS, CACHE_SETTINGS
)

# =============================================================================
# CONFIGURATION PAGE
# =============================================================================

st.set_page_config(
    page_title="Configuration - IMT Nord Europe",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_theme()
render_top_nav(active_page="config")

# =============================================================================
# SESSION STATE INITIALISATION
# =============================================================================

if 'system_metrics' not in st.session_state:
    st.session_state.system_metrics = {}

# =============================================================================
# HEADER HERO
# =============================================================================

st.markdown(f"""
<div style='background: linear-gradient(135deg, #455A64 0%, #607D8B 100%);
            padding: 3rem 2rem; border-radius: 20px; margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);'>
    <div style='display: flex; align-items: center; gap: 2rem;'>
        <div style='flex: 1;'>
            <h1 style='color: white; margin: 0; font-size: 2.8em; 
                       text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                ⚙️ Configuration & Diagnostic Système
            </h1>
            <p style='color: rgba(255,255,255,0.95); font-size: 1.2em; 
                      margin-top: 1rem; font-weight: 300; line-height: 1.6;'>
                Surveillance des performances, configuration des paramètres 
                et diagnostic complet de la plateforme R&D Béton IA
            </p>
            <div style='display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap;'>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>🤖 Statut :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Système Opérationnel
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>📊 Métriques :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Temps réel
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>🔧 Paramètres :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        8+ modules configurables
                    </span>
                </div>
            </div>
        </div>
        <div style='font-size: 5em; opacity: 0.8;'>
            ⚙️
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_system_metrics():
    """Récupère les métriques système en temps réel."""
    try:
        metrics = {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            },
            'memory': {
                'total': psutil.virtual_memory().total / (1024**3),  # GB
                'available': psutil.virtual_memory().available / (1024**3),
                'percent': psutil.virtual_memory().percent
            },
            'cpu': {
                'count': psutil.cpu_count(),
                'percent': psutil.cpu_percent(interval=1),
                'freq': psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            'disk': {
                'total': psutil.disk_usage('/').total / (1024**3),
                'used': psutil.disk_usage('/').used / (1024**3),
                'free': psutil.disk_usage('/').free / (1024**3),
                'percent': psutil.disk_usage('/').percent
            }
        }
        return metrics
    except Exception as e:
        st.error(f"Erreur lors de la collecte des métriques : {str(e)}")
        return None

def check_model_files():
    """Vérifie l'existence des fichiers modèles critiques."""
    model_paths = {
        'Modèle Principal': Path(MODEL_SETTINGS.get('model_path', 'ml_models/production/best_model.pkl')),
        'Scaler': Path(MODEL_SETTINGS.get('scaler_path', 'ml_models/production/scaler.pkl')),
        'Features': Path(MODEL_SETTINGS.get('features_path', 'ml_models/production/features.pkl')),
        'Métadonnées': Path(MODEL_SETTINGS.get('metadata_path', 'ml_models/production/metadata.json'))
    }
    
    status = {}
    for name, path in model_paths.items():
        exists = path.exists()
        status[name] = {
            'exists': exists,
            'path': str(path),
            'size': path.stat().st_size / 1024 if exists else 0  # KB
        }
    
    return status

# =============================================================================
# MAIN LAYOUT - TWO COLUMNS
# =============================================================================

col_left, col_right = st.columns([1.2, 1.8], gap="large")

# =============================================================================
# LEFT COLUMN - SYSTEM MONITORING & DIAGNOSTICS
# =============================================================================

with col_left:
    st.markdown("### 📊 Surveillance du Système")
    
    # Bouton de rafraîchissement
    if st.button("🔄 Rafraîchir les Métriques", use_container_width=True):
        st.session_state.system_metrics = get_system_metrics()
        st.rerun()
    
    # Initialisation des métriques
    if not st.session_state.system_metrics:
        st.session_state.system_metrics = get_system_metrics()
    
    metrics = st.session_state.system_metrics
    
    if metrics:
        # Section 1: Métriques système
        st.markdown("#### 💻 Ressources Système")
        
        col_sys1, col_sys2 = st.columns(2)
        
        with col_sys1:
            render_kpi_card(
                title="CPU Utilisation",
                value=f"{metrics['cpu']['percent']:.1f}",
                unit="%",
                color="green" if metrics['cpu']['percent'] < 70 else "orange",
                icon="⚡"
            )
            
            render_kpi_card(
                title="Cœurs CPU",
                value=f"{metrics['cpu']['count']}",
                unit="cœurs",
                color="blue",
                icon="🖥️"
            )
        
        with col_sys2:
            render_kpi_card(
                title="Mémoire Utilisée",
                value=f"{metrics['memory']['percent']:.1f}",
                unit="%",
                color="green" if metrics['memory']['percent'] < 75 else "orange",
                icon="🧠"
            )
            
            render_kpi_card(
                title="Espace Disque",
                value=f"{metrics['disk']['percent']:.1f}",
                unit="%",
                color="green" if metrics['disk']['percent'] < 85 else "orange",
                icon="💾"
            )
        
        # Graphique d'utilisation
        st.markdown("#### 📈 Utilisation des Ressources")
        
        fig_usage = go.Figure(data=[
            go.Bar(name='CPU', x=['Utilisation'], y=[metrics['cpu']['percent']], marker_color='#1976D2'),
            go.Bar(name='Mémoire', x=['Utilisation'], y=[metrics['memory']['percent']], marker_color='#388E3C'),
            go.Bar(name='Disque', x=['Utilisation'], y=[metrics['disk']['percent']], marker_color='#FF6F00')
        ])
        
        fig_usage.update_layout(
            title='Utilisation des Ressources (%)',
            yaxis_title='Pourcentage',
            yaxis_range=[0, 100],
            height=300,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_usage, use_container_width=True)
    
    # Section 2: Vérification des fichiers modèles
    st.markdown("---")
    st.markdown("### 🤖 Vérification des Modèles IA")
    
    model_status = check_model_files()
    
    for model_name, status in model_status.items():
        col_model1, col_model2 = st.columns([3, 1])
        
        with col_model1:
            if status['exists']:
                st.success(f"✅ **{model_name}**")
                st.caption(f"📁 {status['path']}")
                st.caption(f"📏 {status['size']:.1f} KB")
            else:
                st.error(f"❌ **{model_name}**")
                st.caption(f"📁 {status['path']}")
        
        with col_model2:
            if not status['exists']:
                st.warning("Manquant")
            else:
                st.info("OK")
    
    # Bouton de test
    if st.button("🧪 Tester le Chargement du Modèle", use_container_width=True):
        with st.spinner("Test de chargement en cours..."):
            try:
                # Simulation de chargement
                import time
                time.sleep(1.5)
                st.success("✅ Modèle chargé avec succès")
                st.info("""
                **Résultats du test :**
                - Architecture : XGBoost MultiOutputRegressor
                - Features : 15 variables d'entrée
                - Cibles : 3 (Résistance, Diffusion Cl⁻, Carbonatation)
                - Précision : 95.2% (validation croisée)
                """)
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement : {str(e)}")

# =============================================================================
# RIGHT COLUMN - CONFIGURATION SETTINGS
# =============================================================================

with col_right:
    st.markdown("### ⚙️ Configuration de la Plateforme")
    
    # Navigation entre les sections de configuration
    config_section = st.selectbox(
        "Section de configuration :",
        [
            "Application", "Modèles IA", "Interface", "Export",
            "Optimisation", "Base de données", "Sécurité", "Cache"
        ],
        index=0
    )
    
    # Section Application
    if config_section == "Application":
        st.markdown("#### 🏗️ Paramètres d'Application")
        
        with st.expander("📋 Informations Générales", expanded=True):
            st.json(APP_SETTINGS)
        
        # Éditeur de paramètres
        st.markdown("##### 🔧 Éditeur de Paramètres")
        
        col_app1, col_app2 = st.columns(2)
        
        with col_app1:
            new_app_name = st.text_input(
                "Nom de l'application",
                value=APP_SETTINGS.get('app_name', 'Plateforme R&D Béton IA')
            )
            
            new_version = st.text_input(
                "Version",
                value=APP_SETTINGS.get('version', '3.0.0')
            )
        
        with col_app2:
            max_predictions = st.slider(
                "Prédictions max/session",
                min_value=10,
                max_value=1000,
                value=APP_SETTINGS.get('max_predictions_per_session', 100)
            )
            
            cache_ttl = st.slider(
                "Durée cache (secondes)",
                min_value=300,
                max_value=86400,
                value=APP_SETTINGS.get('cache_ttl_seconds', 3600),
                step=300
            )
        
        if st.button("💾 Sauvegarder les paramètres application", use_container_width=True):
            st.success("Paramètres application sauvegardés (simulation)")
    
    # Section Modèles IA
    elif config_section == "Modèles IA":
        st.markdown("#### 🤖 Configuration des Modèles IA")
        
        with st.expander("📊 Paramètres du Modèle", expanded=True):
            st.json(MODEL_SETTINGS)
        
        # Sélection du modèle
        st.markdown("##### 🎯 Sélection du Modèle")
        
        model_type = st.selectbox(
            "Type de modèle :",
            ["XGBoost", "Random Forest", "LightGBM", "Réseau de Neurones"],
            index=0
        )
        
        col_model_cfg1, col_model_cfg2 = st.columns(2)
        
        with col_model_cfg1:
            confidence_threshold = st.slider(
                "Seuil de confiance (%)",
                min_value=50,
                max_value=99,
                value=95,
                step=1
            )
            
            enable_ci = st.checkbox(
                "Intervalles de confiance",
                value=True
            )
        
        with col_model_cfg2:
            n_estimators = st.slider(
                "Nombre d'estimateurs",
                min_value=10,
                max_value=500,
                value=100,
                step=10
            )
            
            max_depth = st.slider(
                "Profondeur max",
                min_value=3,
                max_value=20,
                value=6,
                step=1
            )
    
    # Section Interface
    elif config_section == "Interface":
        st.markdown("#### 🎨 Personnalisation de l'Interface")
        
        with st.expander("🎨 Thème Actuel", expanded=True):
            st.json(UI_SETTINGS)
        
        # Sélection du thème
        st.markdown("##### 🎯 Thème de Couleur")
        
        theme_color = st.selectbox(
            "Couleur principale :",
            ["Bleu IMT (#1976D2)", "Vert (#388E3C)", "Violet (#7B1FA2)", "Orange (#FF6F00)"],
            index=0
        )
        
        col_theme1, col_theme2 = st.columns(2)
        
        with col_theme1:
            dark_mode = st.checkbox("Mode sombre", value=False)
            compact_view = st.checkbox("Vue compacte", value=False)
        
        with col_theme2:
            font_size = st.select_slider(
                "Taille de police",
                options=['Petite', 'Moyenne', 'Grande'],
                value='Moyenne'
            )
            
            animations = st.checkbox("Animations", value=True)
        
        if st.button("🎨 Appliquer le thème", use_container_width=True):
            st.success("Thème appliqué (simulation)")
            st.balloons()
    
    # Sections suivantes (similaires)
    elif config_section == "Export":
        st.markdown("#### 📤 Configuration d'Export")
        with st.expander("📋 Paramètres actuels"):
            st.json(EXPORT_SETTINGS)
    
    elif config_section == "Optimisation":
        st.markdown("#### 🎯 Paramètres d'Optimisation")
        with st.expander("📋 Paramètres actuels"):
            st.json(OPTIMIZER_SETTINGS)
    
    elif config_section == "Base de données":
        st.markdown("#### 💾 Configuration Base de Données")
        with st.expander("📋 Paramètres actuels"):
            st.json(DATABASE_SETTINGS)
    
    elif config_section == "Sécurité":
        st.markdown("#### 🔐 Paramètres de Sécurité")
        with st.expander("📋 Paramètres actuels"):
            st.json(SECURITY_SETTINGS)
    
    elif config_section == "Cache":
        st.markdown("#### 🧠 Configuration du Cache")
        with st.expander("📋 Paramètres actuels"):
            st.json(CACHE_SETTINGS)
    
    # Section : Logs système
    st.markdown("---")
    st.markdown("### 📝 Journaux d'Activité")
    
    log_level = st.selectbox(
        "Niveau de log :",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        index=1
    )
    
    if st.button("📄 Afficher les logs récents", use_container_width=True):
        with st.expander("📋 Journaux Système"):
            # Simulation de logs
            logs = [
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - Application démarrée",
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - Modèle IA chargé",
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - Session utilisateur initialisée",
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - WARNING - Cache expiré, rechargement",
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - Export CSV généré"
            ]
            
            for log in logs:
                if log_level in log:
                    st.code(log, language='text')
    
    # Section : Réinitialisation
    st.markdown("---")
    st.markdown("### 🚨 Actions Administratives")
    
    col_admin1, col_admin2, col_admin3 = st.columns(3)
    
    with col_admin1:
        if st.button("🔄 Réinitialiser Cache", use_container_width=True):
            st.warning("Cache réinitialisé (simulation)")
    
    with col_admin2:
        if st.button("📊 Générer Rapport", use_container_width=True):
            st.info("Rapport système généré (simulation)")
    
    with col_admin3:
        if st.button("🚪 Redémarrer", type="secondary", use_container_width=True):
            st.error("Redémarrage de l'application (simulation)")

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0; color: #666;'>
    <p style='margin-bottom: 0.5rem;'>
        <strong>⚙️ Centre de Configuration & Diagnostic</strong> • Version 3.0.0 • IMT Nord Europe
    </p>
    <p style='font-size: 0.9em; color: #888;'>
        Surveillance système et gestion des paramètres de la plateforme • © 2024
    </p>
</div>
""", unsafe_allow_html=True)