"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Formulateur - Prédiction des Propriétés du Béton
Fichier: pages/1_Formulateur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.1.0 - VERSION FINALE
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
- Saisie composition béton via sliders
- Prédiction temps réel (3 cibles)
- Validation normes EN 206
- Export résultats (PDF/CSV)
- Sauvegarde en base de données

CORRECTIFS v1.1.0:
✅ Persistance des résultats après clic bouton
✅ Boutons déplacés hors du bloc conditionnel
✅ Flag 'show_results' pour maintenir l'affichage
✅ Messages de succès/erreur clairs
✅ Compteurs (Prédictions, Sauvegardes, Favoris) fonctionnels
✅ Incrémentation automatique des compteurs
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

# Appliquer thème
apply_custom_theme(st.session_state.get('app_theme', 'Clair'))

# Sidebar
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
        📊 Formulateur - Prédiction des Propriétés
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Saisissez votre composition et obtenez instantanément les prédictions ML avec validation normative.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL : 2 COLONNES
# ═══════════════════════════════════════════════════════════════════════════════

col_input, col_results = st.columns([1, 1], gap="large")

# ───────────────────────────────────────────────────────────────────────────────
# COLONNE GAUCHE : SAISIE COMPOSITION
# ───────────────────────────────────────────────────────────────────────────────

with col_input:
    st.markdown("## ⚗️ Composition du Béton")
    
    # Formulaire de saisie
    composition = render_formulation_input(
        key_suffix="formulateur",
        layout="expanded",
        show_presets=True
    )
    
    st.markdown("---")
    
    # Nom de la formulation
    formulation_name = st.text_input(
        label="📝 Nom de la Formulation",
        value=f"Formulation_{datetime.now().strftime('%Y%m%d_%H%M')}",
        max_chars=100,
        help="Nom pour sauvegarder et retrouver cette formulation"
    )
    
    # Bouton principal
    predict_button = st.button(
        label="🚀 Lancer la Prédiction",
        type="primary",
        width='stretch'
    )

# ───────────────────────────────────────────────────────────────────────────────
# COLONNE DROITE : RÉSULTATS
# ───────────────────────────────────────────────────────────────────────────────

with col_results:
    st.markdown("## 🎯 Résultats de Prédiction")
    
    # ═══════════════════════════════════════════════════════════════
    # DÉCLENCHEMENT PRÉDICTION
    # ═══════════════════════════════════════════════════════════════
    
    if predict_button:
        with st.spinner("🔄 Calcul en cours..."):
            try:
                # Récupérer modèle et features
                model = st.session_state.get('model')
                features = st.session_state.get('features')
                
                if not model or not features:
                    st.error("❌ Modèle non chargé. Redémarrez l'application.")
                    st.stop()
                
                # Prédiction
                predictions = predict_concrete_properties(
                    composition=composition,
                    model=model,
                    feature_list=features,
                    validate=True
                )
                
                # Stocker dans session_state avec flag d'affichage
                st.session_state['last_prediction'] = {
                    'composition': composition,
                    'predictions': predictions,
                    'timestamp': datetime.now(),
                    'name': formulation_name
                }
                st.session_state['show_results'] = True
                
                # ✅ INCRÉMENTER COMPTEUR PRÉDICTIONS
                st.session_state['prediction_count'] += 1
                
                st.success("✅ Prédiction réussie !")
                
            except ValueError as e:
                st.error(f"**Erreur de validation** : {e}")
                st.session_state['show_results'] = False
            
            except Exception as e:
                logger.error(f"Erreur prédiction: {e}", exc_info=True)
                st.error(
                    f"**Erreur lors de la prédiction** : {e}  \n\n"
                    "Veuillez vérifier votre composition et réessayer."
                )
                st.session_state['show_results'] = False
    
    # ═══════════════════════════════════════════════════════════════
    # AFFICHAGE RÉSULTATS (persiste après rerun)
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.get('show_results') and st.session_state.get('last_prediction'):
        
        last = st.session_state['last_prediction']
        predictions = last['predictions']
        composition = last['composition']
        formulation_name = last['name']
        
        # ───────────────────────────────────────────────────────────
        # MÉTRIQUES PRINCIPALES
        # ───────────────────────────────────────────────────────────
        
        st.markdown("### 📈 Propriétés Prédites")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            # Déterminer grade résistance
            resistance = predictions['Resistance']
            if resistance >= 50:
                grade_r = "excellent"
            elif resistance >= 35:
                grade_r = "bon"
            elif resistance >= 25:
                grade_r = "moyen"
            else:
                grade_r = "faible"
            
            metric_card(
                title="Résistance",
                value=resistance,
                unit="MPa",
                icon="💪",
                quality_grade=grade_r,
                help_text="Résistance en compression à 28 jours"
            )
        
        with col_m2:
            # Grade diffusion chlorures
            diffusion = predictions['Diffusion_Cl']
            if diffusion < 5:
                grade_d = "excellent"
            elif diffusion < 8:
                grade_d = "bon"
            elif diffusion < 12:
                grade_d = "moyen"
            else:
                grade_d = "faible"
            
            metric_card(
                title="Diffusion Cl⁻",
                value=diffusion,
                unit="×10⁻¹² m²/s",
                icon="🧂",
                quality_grade=grade_d,
                help_text="Coefficient de diffusion des ions chlorures"
            )
        
        with col_m3:
            # Grade carbonatation
            carbonatation = predictions['Carbonatation']
            if carbonatation < 10:
                grade_c = "excellent"
            elif carbonatation < 15:
                grade_c = "bon"
            elif carbonatation < 20:
                grade_c = "moyen"
            else:
                grade_c = "faible"
            
            metric_card(
                title="Carbonatation",
                value=carbonatation,
                unit="mm",
                icon="🌫️",
                quality_grade=grade_c,
                help_text="Profondeur de carbonatation à 1 an"
            )
        
        # ───────────────────────────────────────────────────────────
        # INDICATEURS COMPLÉMENTAIRES
        # ───────────────────────────────────────────────────────────
        
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
        
        # Valider
        validation_report = validate_formulation(
            composition=composition,
            predictions=predictions
        )
        
        # Afficher alertes
        alert_banner(validation_report.alerts, max_display=5)
        
        # Score de conformité
        col_v1, col_v2, col_v3 = st.columns(3)
        
        with col_v1:
            compliance_score = validation_report.compliance_score
            color_score = (
                "🟢" if compliance_score >= 80 else
                ("🟡" if compliance_score >= 60 else "🔴")
            )
            st.metric(
                label="Score Conformité",
                value=f"{color_score} {compliance_score:.0f}/100"
            )
        
        with col_v2:
            st.metric(
                label="Classe Résistance",
                value=validation_report.resistance_class or "N/A"
            )
        
        with col_v3:
            st.metric(
                label="Classe Exposition",
                value=validation_report.exposure_class or "N/A"
            )
        
        # ───────────────────────────────────────────────────────────
        # VISUALISATIONS
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### 📊 Visualisations")
        
        tab_comp, tab_perf = st.tabs(["Composition", "Performance"])
        
        with tab_comp:
            fig_pie = plot_composition_pie(composition)
            st.plotly_chart(fig_pie, width='stretch')
        
        with tab_perf:
            fig_radar = plot_performance_radar(predictions, name=formulation_name)
            st.plotly_chart(fig_radar, width='stretch')
        
        # ───────────────────────────────────────────────────────────
        # ACTIONS
        # ───────────────────────────────────────────────────────────
        
        st.markdown("---")
        st.markdown("### ⚡ Actions Rapides")
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        # Bouton Sauvegarder
        with col_act1:
            save_button = st.button(
                "💾 Sauvegarder",
                width='stretch',
                type="primary",
                key="save_formulation_btn"
            )
        
        # Bouton Favoris
        with col_act2:
            fav_button = st.button(
                "⭐ Favoris",
                width='stretch',
                key="fav_btn"
            )
        
        # Bouton Export
        with col_act3:
            export_button = st.button(
                "📥 Export CSV",
                width='stretch',
                key="export_btn"
            )
        
        # ═══════════════════════════════════════════════════════════
        # TRAITEMENT SAUVEGARDE
        # ═══════════════════════════════════════════════════════════
        
        if save_button:
            db_manager = st.session_state.get('db_manager')
            
            if not db_manager:
                st.error("❌ Base de données non connectée - Impossible de sauvegarder")
                st.info("💡 Vérifiez votre fichier .env et relancez l'application")
                logger.error("DB Manager non disponible")
                
            elif not db_manager.is_connected:
                st.error("❌ Base de données hors ligne - Impossible de sauvegarder")
                st.info("💡 Vérifiez que PostgreSQL est démarré et accessible")
                logger.error("DB Manager non connecté")
                
            else:
                try:
                    with st.spinner("💾 Sauvegarde en cours..."):
                        logger.info(f"[SAVE] Tentative sauvegarde: {formulation_name}")
                        
                        success = db_manager.save_prediction(
                            formulation=composition,
                            predictions=predictions,
                            formulation_name=formulation_name,
                            user_id=st.session_state.get('user_id', 'anonyme')
                        )
                        
                        if success:
                            st.success("✅ Formulation sauvegardée avec succès !")
                            st.balloons()
                            logger.info(f"[SAVE] Succès: {formulation_name}")
                            
                            # ✅ INCRÉMENTER COMPTEUR SAUVEGARDES
                            st.session_state['total_saves'] += 1
                            
                        else:
                            st.error("❌ Échec de la sauvegarde")
                            st.warning("⚠️ La prédiction n'a pas pu être enregistrée en base")
                            logger.error(f"[SAVE] Échec: save_prediction = False")
                            
                            # Proposer export CSV en secours
                            st.info("💡 **Alternative** : Utilisez le bouton 'Export CSV' pour sauvegarder localement")
                
                except psycopg2.OperationalError as e:
                    st.error("❌ Erreur de connexion à la base de données")
                    st.code(f"Détails: {str(e)}", language="text")
                    logger.error(f"[SAVE] Erreur PostgreSQL: {e}", exc_info=True)
                    
                except Exception as e:
                    st.error(f"❌ Erreur inattendue lors de la sauvegarde")
                    st.code(f"Type: {type(e).__name__}\nMessage: {str(e)}", language="text")
                    logger.error(f"[SAVE] Exception: {e}", exc_info=True)
        
        # ═══════════════════════════════════════════════════════════
        # TRAITEMENT FAVORIS
        # ═══════════════════════════════════════════════════════════
        
        if fav_button:
            # Vérifier si déjà en favoris
            already_fav = any(
                fav['name'] == formulation_name 
                for fav in st.session_state['favorites']
            )
            
            if already_fav:
                st.warning(f"⚠️ {formulation_name} est déjà dans vos favoris")
            else:
                st.session_state['favorites'].append({
                    'name': formulation_name,
                    'composition': composition,
                    'predictions': predictions,
                    'timestamp': datetime.now()
                })
                st.success(f"⭐ {formulation_name} ajouté aux favoris")
                logger.info(f"[FAV] Ajout: {formulation_name}")
        
        # ═══════════════════════════════════════════════════════════
        # TRAITEMENT EXPORT CSV
        # ═══════════════════════════════════════════════════════════
        
        if export_button:
            try:
                import pandas as pd
                
                # Combiner composition + prédictions
                export_data = {
                    'Nom_Formulation': formulation_name,
                    'Date_Export': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    **composition,
                    **predictions
                }
                
                df = pd.DataFrame([export_data])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    label="⬇️ Télécharger le CSV",
                    data=csv,
                    file_name=f"{formulation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width='stretch',
                    key="download_csv_btn"
                )
                
                st.success("📁 Fichier CSV prêt au téléchargement")
                logger.info(f"[EXPORT] CSV généré: {formulation_name}")
                
            except Exception as e:
                st.error(f"❌ Erreur lors de l'export : {str(e)}")
                logger.error(f"[EXPORT] Erreur: {e}", exc_info=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ÉTAT INITIAL (AVANT PRÉDICTION)
    # ═══════════════════════════════════════════════════════════════
    
    elif not st.session_state.get('show_results'):
        
        info_box(
            title="Mode d'emploi",
            content="""
            1. **Sélectionnez** une formulation prédéfinie ou personnalisez les paramètres
            2. **Ajustez** les sliders pour définir votre composition
            3. **Cliquez** sur "🚀 Lancer la Prédiction"
            4. **Analysez** les résultats et la validation normative
            5. **Sauvegardez** ou exportez votre formulation
            
            Les prédictions sont basées sur un modèle **XGBoost** entraîné sur 
            1030 formulations avec un **R² > 0.93** sur la résistance.
            """.strip(),
            icon="ℹ️",
            color="info"
        )
        
        # Afficher dernière prédiction si disponible
        if st.session_state.get('last_prediction'):
            st.markdown("---")
            st.markdown("### 🕐 Dernière Prédiction")
            
            last = st.session_state['last_prediction']
            
            st.markdown(f"**Nom** : {last['name']}")
            st.markdown(f"**Date** : {last['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            
            with col_l1:
                st.metric(
                    "Résistance",
                    f"{last['predictions']['Resistance']:.1f} MPa"
                )
            
            with col_l2:
                st.metric(
                    "Diffusion Cl⁻",
                    f"{last['predictions']['Diffusion_Cl']:.2f}"
                )
            
            with col_l3:
                st.metric(
                    "Carbonatation",
                    f"{last['predictions']['Carbonatation']:.1f} mm"
                )
            
            # Bouton pour réafficher les résultats
            if st.button("🔄 Réafficher les résultats complets", width='stretch'):
                st.session_state['show_results'] = True
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

# Statistiques session
col_stat1, col_stat2, col_stat3 = st.columns(3)

with col_stat1:
    total_preds = st.session_state.get('prediction_count', 0)
    st.caption(f"🔬 **Prédictions** : {total_preds}")

with col_stat2:
    total_saves = st.session_state.get('total_saves', 0)
    st.caption(f"💾 **Sauvegardes** : {total_saves}")

with col_stat3:
    total_favs = len(st.session_state.get('favorites', []))
    st.caption(f"⭐ **Favoris** : {total_favs}")

st.caption(
    "💡 **Conseil** : Pour comparer plusieurs formulations, utilisez le module **Comparateur**"
)