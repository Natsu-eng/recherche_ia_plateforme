"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Formulateur - Prédiction des Propriétés du Béton
Fichier: pages/1_Formulateur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Corrigé & Production Ready
═══════════════════════════════════════════════════════════════════════════════

CORRECTIONS v1.0.0 (depuis v1.2.0):
  ✅ width='stretch' → use_container_width=True (partout, API Streamlit correcte)
  ✅ co2_calc_temp scope corrigé → co2_calc_display défini au niveau bloc résultats
  ✅ validate_formulation() stocké en session → pas de recalcul à chaque rerun
  ✅ required_class transmis au rapport de validation ET aux favoris
  ✅ Verdict normatif EN PREMIER (avant métriques) — logique métier correcte
  ✅ verdict_card() utilisé depuis cards.py v1.0.0
  ✅ Compteurs session gérés par _SESSION_DEFAULTS (session_manager)
"""

import streamlit as st
import logging
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE, EXPOSURE_CLASSES
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.forms import render_formulation_input
from app.components.cards import metric_card, alert_banner, info_box, verdict_card
from app.components.charts import plot_composition_pie, plot_performance_radar
from app.core.predictor import predict_concrete_properties
from app.core.validator import validate_formulation
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from config.co2_database import CEMENT_CO2_KG_PER_TONNE

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Formulateur - Béton IA",
    page_icon="📊",
    layout="wide",
)

apply_custom_theme(st.session_state.get("app_theme", "Clair"))
render_sidebar(db_manager=st.session_state.get("db_manager"))

from app.components.navbar import render_navbar
render_navbar(current_page="Formulateur")

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color:{COLOR_PALETTE['primary']};border-bottom:3px solid {COLOR_PALETTE['accent']};padding-bottom:0.5rem;">
        📊 Formulateur — Prédiction des Propriétés + CO₂
    </h1>
    <p style="font-size:1.1rem;color:{COLOR_PALETTE['secondary']};margin-top:0.5rem;">
        Saisissez votre composition et obtenez les prédictions ML + empreinte carbone.
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

col_input, col_results = st.columns([1, 1], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# COLONNE GAUCHE — SAISIE
# ─────────────────────────────────────────────────────────────────────────────

with col_input:
    st.markdown("## ⚗️ Composition du Béton")

    composition = render_formulation_input(
        key_suffix="formulateur",
        layout="expanded",
        show_presets=True,
    )

    st.markdown("---")

    # ── Type de ciment ──────────────────────────────────────────────────────
    st.markdown("### 🏭 Type de Ciment")
    selected_cement = st.selectbox(
        "Choisir le type de ciment",
        options=list(CEMENT_CO2_KG_PER_TONNE.keys()),
        index=0,
        help="Le type de ciment impacte directement l'empreinte carbone",
    )
    cement_co2_factor = CEMENT_CO2_KG_PER_TONNE[selected_cement]
    st.caption(f"📊 Facteur CO₂ : {cement_co2_factor:.1f} kg CO₂/tonne")

    st.markdown("---")

    # ── Classe d'exposition requise ─────────────────────────────────────────
    st.markdown("### 📋 Classe d'Exposition Requise")
    required_exposure = st.selectbox(
        "Sélectionner la classe exigée par l'environnement",
        options=list(EXPOSURE_CLASSES.keys()),
        index=0,
        key="required_exposure",
        help="Selon EN 206 — XC1, XD2, XS3…",
    )
    specs = EXPOSURE_CLASSES[required_exposure]
    st.caption(f"**Exigences** : E/L ≤ {specs['E_L_max']} | fc ≥ {specs['fc_min']} MPa")

    st.markdown("---")

    formulation_name = st.text_input(
        label="📝 Nom de la Formulation",
        value=f"Formulation_{datetime.now().strftime('%Y%m%d_%H%M')}",
        max_chars=100,
    )

    # ✅ use_container_width=True (width='stretch' n'existe pas dans Streamlit)
    predict_button = st.button(
        label="🚀 Lancer la Prédiction + CO₂",
        type="primary",
        use_container_width=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# COLONNE DROITE — RÉSULTATS
# ─────────────────────────────────────────────────────────────────────────────

with col_results:
    st.markdown("## 🎯 Résultats")

    # ═════════════════════════════════════════════════════════════════════════
    # DÉCLENCHEMENT PRÉDICTION
    # ═════════════════════════════════════════════════════════════════════════

    if predict_button:
        with st.spinner("🔄 Calcul en cours…"):
            try:
                model    = st.session_state.get("model")
                features = st.session_state.get("features")

                if not model or not features:
                    st.error("❌ Modèle non chargé. Redémarrez l'application.")
                    st.stop()

                # 1. Prédiction ML
                if composition.get("Metakaolin", 0) > 0 and st.session_state.get("mk_corrector"):
                    from app.core.predictor import predict_with_mk
                    predictions = predict_with_mk(
                        composition=composition,
                        model=model,
                        feature_list=features,
                        mk_corrector=st.session_state["mk_corrector"],
                        validate=True,
                    )
                else:
                    predictions = predict_concrete_properties(
                        composition=composition,
                        model=model,
                        feature_list=features,
                        validate=True,
                    )

                # 2. Calcul CO₂
                co2_calc   = CO2Calculator()
                co2_result = co2_calc.calculate(composition, selected_cement)

                # 3. Validation normative EN 206 (avec required_class ✅)
                validation_report = validate_formulation(
                    composition=composition,
                    predictions=predictions,
                    required_class=required_exposure,
                )

                # 4. Stockage session — validation_report inclus ✅
                st.session_state["last_prediction"] = {
                    "composition":       composition,
                    "predictions":       predictions,
                    "co2_result":        co2_result,
                    "cement_type":       selected_cement,
                    "validation_report": validation_report,   # ✅ stocké → pas de recalcul
                    "required_class":    required_exposure,
                    "timestamp":         datetime.now(),
                    "name":              formulation_name,
                }
                st.session_state["show_results"]     = True
                st.session_state["prediction_count"] = (
                    st.session_state.get("prediction_count", 0) + 1
                )

                st.success("✅ Prédiction + CO₂ réussis !")

            except ValueError as e:
                st.error(f"**Erreur de validation** : {e}")
                st.session_state["show_results"] = False

            except Exception as e:
                logger.error("Erreur prédiction: %s", e, exc_info=True)
                st.error(f"**Erreur** : {e}")
                st.session_state["show_results"] = False

    # ═════════════════════════════════════════════════════════════════════════
    # AFFICHAGE RÉSULTATS
    # ═════════════════════════════════════════════════════════════════════════

    if st.session_state.get("show_results") and st.session_state.get("last_prediction"):

        last              = st.session_state["last_prediction"]
        predictions       = last["predictions"]
        composition       = last["composition"]
        co2_result        = last.get("co2_result")
        cement_type       = last.get("cement_type", "CEM I")
        formulation_name  = last["name"]
        required_class    = last.get("required_class", required_exposure)
        validation_report = last.get("validation_report")

        # Recalcul si rapport absent (rétro-compatibilité sessions anciennes)
        if validation_report is None:
            validation_report = validate_formulation(
                composition=composition,
                predictions=predictions,
                required_class=required_class,
            )

        # ✅ Calculateur CO₂ disponible dans tout le bloc résultats
        co2_calc_display = CO2Calculator()

        # ── BLOC 1 : Verdict normatif EN 206 (en PREMIER) ───────────────────
        st.markdown("### ⚖️ Verdict Normatif EN 206")
        verdict_card(validation_report)

        # ── BLOC 2 : Propriétés prédites + CO₂ ──────────────────────────────
        st.markdown("---")
        st.markdown("### 📈 Propriétés Prédites + Empreinte Carbone")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            resistance = predictions["Resistance"]
            grade_r    = "excellent" if resistance >= 50 else ("bon" if resistance >= 35 else "moyen")
            metric_card(title="Résistance",    value=resistance,   unit="MPa",    icon="💪",  quality_grade=grade_r)

        with col_m2:
            diffusion = predictions["Diffusion_Cl"]
            grade_d   = "excellent" if diffusion < 5 else ("bon" if diffusion < 8 else "moyen")
            metric_card(title="Diffusion Cl⁻", value=diffusion,    unit="×10⁻¹²", icon="🧂",  quality_grade=grade_d)

        with col_m3:
            carbonatation = predictions["Carbonatation"]
            grade_c       = "excellent" if carbonatation < 10 else ("bon" if carbonatation < 15 else "moyen")
            metric_card(title="Carbonatation", value=carbonatation, unit="mm",     icon="🌫️", quality_grade=grade_c)

        with col_m4:
            if co2_result:
                co2_total  = co2_result.co2_total_kg_m3
                classe_env, emoji_co2, _ = get_environmental_grade(co2_total)
                grade_co2  = "excellent" if co2_total < 250 else ("bon" if co2_total < 350 else "moyen")
                metric_card(title="Empreinte CO₂", value=co2_total, unit="kg/m³", icon="🌍", quality_grade=grade_co2)
                st.caption(f"{emoji_co2} Classe : **{classe_env}**")
            else:
                st.metric("Empreinte CO₂", "N/A")

        # ── BLOC 3 : Indicateurs techniques ──────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Indicateurs Techniques")

        col_i1, col_i2, col_i3 = st.columns(3)

        with col_i1:
            st.metric("Liant Total", f"{predictions['Liant_Total']:.0f} kg/m³")

        with col_i2:
            ratio_el   = predictions["Ratio_E_L"]
            color_el   = "🟢" if ratio_el <= 0.50 else ("🟡" if ratio_el <= 0.60 else "🔴")
            st.metric("Ratio E/L", f"{color_el} {ratio_el:.3f}")

        with col_i3:
            taux_sub   = predictions.get("Pct_Substitution", 0) * 100
            st.metric("Substitution", f"{taux_sub:.1f} %")

        # ── BLOC 4 : Détails CO₂ ─────────────────────────────────────────────
        if co2_result:
            st.markdown("---")
            st.markdown("### 🌍 Détail Empreinte Carbone")

            co2_total = co2_result.co2_total_kg_m3   # ✅ scope local propre

            col_co2_1, col_co2_2 = st.columns(2)

            with col_co2_1:
                st.markdown("**Répartition par Constituant**")
                # ✅ co2_calc_display défini au niveau bloc — pas de NameError
                breakdown = co2_calc_display.get_breakdown_percentages(co2_result)
                for constituent, percent in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                    if percent > 1.0:
                        co2_val = getattr(co2_result, f"co2_{constituent.lower()}", 0)
                        st.markdown(f"• **{constituent}** : {co2_val:.1f} kg ({percent:.1f} %)")

            with col_co2_2:
                st.markdown("**Informations Ciment**")
                st.markdown(f"**Type** : {cement_type}")
                st.markdown(f"**Facteur CO₂** : {co2_result.cement_co2_factor:.1f} kg CO₂/t")
                arbres = co2_total / 25.0
                st.markdown(f"**Équivalent** : {arbres:.1f} arbre(s) / an")

                if co2_total > 300:
                    with st.expander("💡 Suggestions Réduction CO₂"):
                        if cement_type == "CEM I":
                            st.info("→ Remplacer CEM I par CEM III/B → Réduction ~60 %")
                        if composition.get("Laitier", 0) < 50:
                            st.info("→ Ajouter laitier (20–30 %) → Réduction ~20–30 %")
                        st.info("→ Réduire dosage ciment de 10 % → Réduction ~10 %")

        # ── BLOC 5 : Alertes détaillées ──────────────────────────────────────
        st.markdown("---")
        with st.expander(
            f"🔍 Détail des recommandations ({len(validation_report.alerts)} alertes)",
            expanded=False,
        ):
            _ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3}
            sorted_alerts = sorted(
                validation_report.alerts,
                key=lambda a: _ORDER.get(a.severity.value, 9),
            )
            for alert in sorted_alerts[:8]:
                col_al1, col_al2 = st.columns([1, 5])
                with col_al1:
                    st.markdown(f"**{alert.severity.value.upper()}**")
                with col_al2:
                    st.markdown(f"**{alert.message}**")
                    st.caption(f"💡 {alert.recommendation}")
                    if alert.norm_ref:
                        st.caption(f"📖 {alert.norm_ref}")
                st.divider()

        # ── BLOC 6 : Visualisations ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Visualisations")

        tab_comp, tab_perf, tab_co2 = st.tabs(["🥧 Composition", "🕸️ Performance", "🌍 Impact CO₂"])

        with tab_comp:
            fig_pie = plot_composition_pie(composition)
            st.plotly_chart(fig_pie, use_container_width=True)   # ✅

        with tab_perf:
            fig_radar = plot_performance_radar(predictions, name=formulation_name)
            st.plotly_chart(fig_radar, use_container_width=True)  # ✅

        with tab_co2:
            if co2_result:
                import plotly.graph_objects as go

                # ✅ co2_calc_display disponible ici (défini en haut du bloc résultats)
                breakdown_tab = co2_calc_display.get_breakdown_percentages(co2_result)
                filtered      = {k: v for k, v in breakdown_tab.items() if v > 1.0}

                fig_co2 = go.Figure(data=[go.Pie(
                    labels=list(filtered.keys()),
                    values=list(filtered.values()),
                    hole=0.4,
                    marker=dict(colors=["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]),
                )])
                fig_co2.update_layout(
                    title=f"Répartition Empreinte CO₂ — Total : {co2_result.co2_total_kg_m3:.1f} kg/m³",
                    height=400,
                )
                st.plotly_chart(fig_co2, use_container_width=True)  # ✅
            else:
                st.info("Calcul CO₂ non disponible.")

        # ── BLOC 7 : Actions rapides ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("### ⚡ Actions Rapides")

        col_act1, col_act2, col_act3 = st.columns(3)

        with col_act1:
            save_button = st.button("💾 Sauvegarder", use_container_width=True, type="primary")  # ✅
        with col_act2:
            fav_button  = st.button("⭐ Favoris",     use_container_width=True)                  # ✅
        with col_act3:
            export_button = st.button("📥 Export CSV", use_container_width=True)                 # ✅

        # ── Sauvegarde ─────────────────────────────────────────────────────
        if save_button:
            db_manager = st.session_state.get("db_manager")
            if db_manager and db_manager.is_connected:
                try:
                    with st.spinner("💾 Sauvegarde…"):
                        success = db_manager.save_prediction(
                            formulation=composition,
                            predictions=predictions,
                            formulation_name=formulation_name,
                            user_id="anonyme",
                        )
                    if success:
                        st.success("✅ Sauvegardée !")
                        st.balloons()
                        st.session_state["total_saves"] = (
                            st.session_state.get("total_saves", 0) + 1
                        )
                    else:
                        st.error("❌ Échec sauvegarde")
                except Exception as e:
                    st.error(f"❌ Erreur BDD : {e}")
            else:
                st.warning("⚠️ DB non connectée")

        # ── Favoris ────────────────────────────────────────────────────────
        if fav_button:
            favs = st.session_state.get("favorites", [])
            if not any(f["name"] == formulation_name for f in favs):
                favs.append({
                    "name":             formulation_name,
                    "composition":      composition,
                    "predictions":      predictions,
                    "co2_result":       co2_result,
                    "required_class":   required_class,          # ✅
                    "achieved_class":   validation_report.achieved_class,
                    "compliance_score": validation_report.compliance_score,
                    "timestamp":        datetime.now(),
                })
                st.session_state["favorites"] = favs
                st.success(f"⭐ '{formulation_name}' ajouté aux favoris")
            else:
                st.warning("⚠️ Déjà en favoris")

        # ── Export CSV ─────────────────────────────────────────────────────
        if export_button:
            try:
                import pandas as pd

                export_data = {
                    "Nom":              formulation_name,
                    "Date":             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Classe_Exigee":    required_class,
                    "Classe_Atteinte":  validation_report.achieved_class or "N/A",
                    "Conforme":         validation_report.compliance_with_required,
                    "Score_Conformite": validation_report.compliance_score,
                    **composition,
                    **predictions,
                    "CO2_Total_kg_m3":  co2_result.co2_total_kg_m3 if co2_result else 0,
                    "Cement_Type":      cement_type,
                }
                df  = pd.DataFrame([export_data])
                csv = df.to_csv(index=False, encoding="utf-8-sig")

                st.download_button(
                    label="⬇️ Télécharger CSV",
                    data=csv,
                    file_name=f"{formulation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,  # ✅
                )
                st.success("📁 CSV prêt")
            except Exception as e:
                st.error(f"❌ Erreur export : {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # ÉTAT INITIAL
    # ═════════════════════════════════════════════════════════════════════════

    elif not st.session_state.get("show_results"):
        info_box(
            title="Mode d'emploi",
            content=(
                "1. **Sélectionnez** composition et type de ciment\n"
                "2. **Choisissez** la classe d'exposition requise\n"
                "3. **Cliquez** sur \"🚀 Lancer la Prédiction + CO₂\"\n"
                "4. **Analysez** résultats ML + empreinte carbone\n\n"
                "**Nouveau** : Calcul automatique empreinte CO₂ selon NF EN 15804"
            ),
            icon="ℹ️",
            color="info",
        )

        if st.session_state.get("last_prediction"):
            st.markdown("---")
            st.markdown("### 🕐 Dernière Prédiction")
            last = st.session_state["last_prediction"]

            col_l1, col_l2, col_l3, col_l4 = st.columns(4)
            with col_l1:
                st.metric("Résistance",    f"{last['predictions']['Resistance']:.1f} MPa")
            with col_l2:
                st.metric("Diffusion Cl⁻", f"{last['predictions']['Diffusion_Cl']:.2f}")
            with col_l3:
                st.metric("Carbonatation", f"{last['predictions']['Carbonatation']:.1f} mm")
            with col_l4:
                if last.get("co2_result"):
                    st.metric("CO₂", f"{last['co2_result'].co2_total_kg_m3:.1f} kg/m³")

            if last.get("validation_report"):
                vr = last["validation_report"]
                st.caption(
                    f"Classe exigée : **{last.get('required_class', '—')}** | "
                    f"Atteinte : **{vr.achieved_class or '—'}** | "
                    f"{'✅ Conforme' if vr.compliance_with_required else '❌ Non conforme'}"
                )

            if st.button("🔄 Réafficher les résultats", use_container_width=True):  # ✅
                st.session_state["show_results"] = True
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.caption(f"🔬 **Prédictions** : {st.session_state.get('prediction_count', 0)}")
with col_stat2:
    st.caption(f"💾 **Sauvegardes** : {st.session_state.get('total_saves', 0)}")
with col_stat3:
    st.caption(f"⭐ **Favoris** : {len(st.session_state.get('favorites', []))}")

st.caption(
    "🌍 Empreinte CO₂ calculée selon NF EN 15804 | "
    "💡 CEM III/B permet ~60 % de réduction"
)