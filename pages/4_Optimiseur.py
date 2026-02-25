"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Optimiseur — Algorithme Génétique + CO₂
Fichier: pages/4_Optimiseur.py
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import logging
import time
from datetime import datetime

from config.settings import APP_SETTINGS, OPTIMIZER_SETTINGS
from config.constants import COLOR_PALETTE, MATERIALS_COST_EURO_KG, EXPOSURE_CLASSES
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import metric_card, info_box
from app.components.charts import plot_composition_pie, plot_performance_radar, plot_cost_breakdown
from app.core.optimizer import optimize_mix, compute_cost
from app.core.validator import validate_formulation
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from config.co2_database import CEMENT_CO2_KG_PER_TONNE

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Optimiseur - Béton IA",
    page_icon="🎯",
    layout="wide",
)

apply_custom_theme(st.session_state.get("app_theme", "Clair"))
render_sidebar(db_manager=st.session_state.get("db_manager"))

from app.components.navbar import render_navbar
render_navbar(current_page="Optimiseur")

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION SESSION
# ═══════════════════════════════════════════════════════════════════════════════

if "optimization_history" not in st.session_state:
    st.session_state["optimization_history"] = []

if "opt_results" not in st.session_state:
    st.session_state["opt_results"] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color:{COLOR_PALETTE['primary']};border-bottom:3px solid {COLOR_PALETTE['accent']};padding-bottom:0.5rem;">
        🎯 Optimiseur — Formulation Optimale (Coût + CO₂)
    </h1>
    <p style="font-size:1.1rem;color:{COLOR_PALETTE['secondary']};margin-top:0.5rem;">
        Trouvez la formulation idéale selon vos objectifs économiques et environnementaux.
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PANNEAU GAUCHE — CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

col_config, col_results = st.columns([1, 1.5], gap="large")

with col_config:
    st.markdown("## ⚙️ Configuration")

    # ── Objectif ────────────────────────────────────────────────────────────
    st.markdown("### 🎯 Objectif d'Optimisation")
    objective = st.radio(
        "Choisir l'objectif principal",
        options=[
            "Minimiser le Coût",
            "Minimiser l'Empreinte CO₂",
            "Équilibre Coût / CO₂",
        ],
        help=(
            "Coût : algorithme sur critère économique\n"
            "CO₂ : algorithme sur critère carbone\n"
            "Équilibre : deux solutions côte à côte"
        ),
    )

    if "Coût" in objective and "CO₂" not in objective:
        objective_keys = ["minimize_cost"]
    elif "CO₂" in objective and "Coût" not in objective:
        objective_keys = ["minimize_co2"]
    else:
        objective_keys = ["minimize_cost", "minimize_co2"]

    mode_equilibre = len(objective_keys) == 2

    # ── Type de ciment ──────────────────────────────────────────────────────
    st.markdown("### 🏭 Type de Ciment")
    selected_cement = st.selectbox(
        "Choisir le type de ciment",
        options=list(CEMENT_CO2_KG_PER_TONNE.keys()),
        index=2,
        help="Impact majeur sur empreinte CO₂",
    )
    cement_co2_factor = CEMENT_CO2_KG_PER_TONNE[selected_cement]
    st.caption(f"📊 Facteur : {cement_co2_factor:.1f} kg CO₂/t")

    st.markdown("---")

    # ── Classe d'exposition ─────────────────────────────────────────────────
    st.markdown("### 📋 Classe d'Exposition Requise")
    required_exposure_opt = st.selectbox(
        "Classe exigée pour l'optimisation",
        options=list(EXPOSURE_CLASSES.keys()),
        index=0,
        key="required_exposure_opt",
        help="L'optimiseur cherchera une formulation conforme à cette classe",
    )
    specs_opt = EXPOSURE_CLASSES[required_exposure_opt]
    st.caption(f"**Exigences** : E/L ≤ {specs_opt['E_L_max']} | fc ≥ {specs_opt['fc_min']} MPa")

    st.markdown("---")

    # ── Contraintes ─────────────────────────────────────────────────────────
    st.markdown("### 📊 Contraintes")
    target_resistance = st.number_input(
        "Résistance Minimale (MPa)",
        min_value=10.0, max_value=90.0, value=30.0, step=5.0,
    )

    if mode_equilibre or "CO₂" in objective:
        max_co2 = st.number_input(
            "CO₂ Maximum (kg/m³) — Optionnel",
            min_value=0.0, max_value=500.0, value=0.0, step=50.0,
            help="0 = pas de limite",
        )
    else:
        max_co2 = 0.0

    st.markdown("---")

    with st.expander("🔧 Paramètres Avancés", expanded=False):
        population_size = st.slider("Taille Population", 50, 200, 100, 10)
        num_generations = st.slider("Générations",       20, 100,  50, 10)
        st.caption(f"⏱️ ~{population_size * num_generations * 0.002:.1f}s")

    st.markdown("---")

    optimize_button = st.button(
        "🚀 Lancer l'Optimisation", type="primary", use_container_width=True
    )

    # ── Bouton reset ─────────────────────────────────────────────────────────
    if st.session_state["opt_results"] and st.button(
        "🗑️ Effacer les résultats", use_container_width=True
    ):
        st.session_state["opt_results"] = {}
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PANNEAU DROIT — CALCUL (déclenché uniquement sur clic "Lancer")
# ═══════════════════════════════════════════════════════════════════════════════

with col_results:
    st.markdown("## 🎯 Résultats")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 : CALCUL (seulement quand optimize_button est True)
    # Les résultats sont sauvegardés en session → persistants après rerun
    # ─────────────────────────────────────────────────────────────────────────

    if optimize_button:
        with st.spinner("🔄 Optimisation en cours…"):
            progress_bar = st.progress(0)
            status_text  = st.empty()

            try:
                model    = st.session_state.get("model")
                features = st.session_state.get("features")
                co2_calc = CO2Calculator()

                for i in range(10):
                    progress_bar.progress((i + 1) * 10)
                    status_text.text(f"Génération {i + 1}/10…")
                    time.sleep(0.05)

                start_time = time.time()

                # ── Lance les optimisations ──────────────────────────────────
                # ✅ Réinitialiser les résultats précédents avant nouveau calcul
                st.session_state["opt_results"] = {}

                for obj_key in objective_keys:
                    res = optimize_mix(
                        model=model,
                        feature_list=features,
                        target_strength=target_resistance,
                        required_class=required_exposure_opt,
                        objective=obj_key,
                        random_state=42,
                    )

                    if res is None:
                        continue

                    co2_result  = co2_calc.calculate(res.mix, selected_cement)
                    composition = res.mix
                    predictions = res.targets
                    co2_total   = co2_result.co2_total_kg_m3

                    validation = validate_formulation(
                        composition=composition,
                        predictions=predictions,
                        required_class=required_exposure_opt,
                    )

                    label = {
                        "minimize_cost": "💰 Optimal Coût",
                        "minimize_co2":  "🌍 Optimal CO₂",
                    }.get(obj_key, obj_key)

                    # ✅ STOCKAGE EN SESSION → survivra au prochain rerun
                    st.session_state["opt_results"][obj_key] = {
                        "composition":        composition,
                        "predictions":        predictions,
                        "co2_result":         co2_result,
                        "co2_total":          co2_total,
                        "validation":         validation,
                        "cost":               res.cost,
                        "cement_type":        selected_cement,
                        "required_class":     required_exposure_opt,
                        "label":              label,
                        "timestamp":          datetime.now(),
                        "target_resistance":  target_resistance,
                    }

                    # Ajouter à l'historique
                    st.session_state["optimization_history"].append({
                        "timestamp":         datetime.now(),
                        "objective":         obj_key,
                        "target_resistance": target_resistance,
                        "cost":              res.cost,
                        "co2_total":         co2_total,
                        "cement_type":       selected_cement,
                        "resistance":        predictions["Resistance"],
                        "validation":        validation,
                    })

                elapsed_time = time.time() - start_time
                progress_bar.progress(100)
                status_text.text("✅ Optimisation terminée !")

                n = len(st.session_state["opt_results"])
                if n == 0:
                    st.error(f"Aucune solution trouvée pour R ≥ {target_resistance} MPa")
                    st.info("💡 Réduire la résistance cible ou assouplir les contraintes")
                else:
                    st.success(
                        f"{'Solution trouvée' if n == 1 else f'{n} solutions trouvées'} "
                        f"en {elapsed_time:.2f}s !"
                    )

            except Exception as e:
                logger.error("Erreur optimisation: %s", e, exc_info=True)
                st.error(f"Erreur : {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 : AFFICHAGE + ACTIONS
    # ✅ Ce bloc est HORS du `if optimize_button:` → s'exécute à chaque rerun
    # Les boutons Sauvegarder / Favoris / CSV fonctionnent correctement
    # ─────────────────────────────────────────────────────────────────────────

    opt_results = st.session_state.get("opt_results", {})

    if not opt_results:
        if not optimize_button:
            info_box(
                "Mode d'emploi",
                (
                    "1. **Choisissez** objectif (Coût / CO₂ / Équilibre)\n"
                    "2. **Sélectionnez** type de ciment\n"
                    "3. **Définissez** contraintes (résistance min, CO₂ max)\n"
                    "4. **Lancez** l'optimisation\n\n"
                    "**Mode Équilibre** : affiche deux solutions côte à côte !"
                ),
                icon="ℹ️",
                color="info",
            )
    else:
        # ── Colonnes selon nombre de solutions ──────────────────────────────
        result_cols = st.columns(len(opt_results))

        for col_idx, (obj_key, data) in enumerate(opt_results.items()):

            composition  = data["composition"]
            predictions  = data["predictions"]
            co2_result   = data["co2_result"]
            co2_total    = data["co2_total"]
            validation   = data["validation"]
            cost         = data["cost"]
            cement_type  = data["cement_type"]
            required_cls = data["required_class"]
            label        = data["label"]
            ts           = data["timestamp"]

            with result_cols[col_idx]:
                st.markdown(f"### {label}")
                st.caption(f"Calculé à {ts.strftime('%H:%M:%S')}")

                # ─── Composition ──────────────────────────────────────────
                st.markdown("#### 🧪 Composition")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown("**Liants**")
                    for k in ["Ciment", "Laitier", "CendresVolantes", "Eau"]:
                        st.markdown(f"• {k} : **{composition.get(k, 0):.1f}** kg/m³")
                with col_c2:
                    st.markdown("**Granulats**")
                    for k in ["GravilonsGros", "SableFin", "Superplastifiant"]:
                        st.markdown(f"• {k} : **{composition.get(k, 0):.1f}** kg/m³")
                    st.markdown(f"• Âge : **{composition.get('Age', 28):.0f}** j")

                # ─── Performances ─────────────────────────────────────────
                st.markdown("#### 📈 Performances")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    metric_card("Résistance",    predictions["Resistance"],    "MPa",     "💪", quality_grade="bon")
                    metric_card("Carbonatation", predictions["Carbonatation"], "mm",      "🌫️", quality_grade="bon")
                with col_p2:
                    metric_card("Diffusion Cl⁻", predictions["Diffusion_Cl"], "×10⁻¹²", "🧂", quality_grade="bon")
                    metric_card("Ratio E/L",     predictions["Ratio_E_L"],    "",        "💧", quality_grade="bon")

                # ─── Économie + Écologie ──────────────────────────────────
                st.markdown("#### 💰 Économie + 🌍 Écologie")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    st.metric("Coût", f"{cost:.2f} €/m³")
                with col_e2:
                    classe_co2, emoji_co2, _ = get_environmental_grade(co2_total)
                    st.metric("CO₂", f"{co2_total:.1f} kg/m³")
                    st.caption(f"{emoji_co2} {classe_co2}")
                with col_e3:
                    ratio_eco = cost / co2_total if co2_total > 0 else 0
                    st.metric("€ / kg CO₂", f"{ratio_eco:.3f}")

                # ─── Validation EN 206 ────────────────────────────────────
                st.markdown("#### 🔍 Validation EN 206")
                col_v1, col_v2, col_v3 = st.columns(3)
                with col_v1:
                    score     = validation.compliance_score
                    dot       = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
                    st.metric("Score", f"{dot} {score:.0f}/100")
                with col_v2:
                    st.metric("Classe R", validation.resistance_class or "N/A")
                with col_v3:
                    st.metric("Exposition", validation.achieved_class or "N/A")
                    st.caption("✅ Conforme" if validation.compliance_with_required else "❌ Non conforme")

                # ─── Visualisations ───────────────────────────────────────
                st.markdown("#### 📊 Visualisations")
                tab_pie, tab_cost, tab_co2_tab, tab_radar = st.tabs(
                    ["Composition", "Coûts", "🌍 CO₂", "Performance"]
                )
                with tab_pie:
                    fig_pie = plot_composition_pie(composition)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with tab_cost:
                    fig_cost = plot_cost_breakdown(composition)
                    st.plotly_chart(fig_cost, use_container_width=True)

                with tab_co2_tab:
                    import plotly.graph_objects as go
                    co2_calc_disp = CO2Calculator()
                    breakdown = co2_calc_disp.get_breakdown_percentages(co2_result)
                    filtered  = {k: v for k, v in breakdown.items() if v > 1}
                    fig_co2_pie = go.Figure(data=[go.Pie(
                        labels=list(filtered.keys()),
                        values=list(filtered.values()),
                        hole=0.4,
                        marker=dict(colors=["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]),
                    )])
                    fig_co2_pie.update_layout(
                        title=f"Répartition CO₂ — {co2_total:.1f} kg/m³", height=400
                    )
                    st.plotly_chart(fig_co2_pie, use_container_width=True)

                with tab_radar:
                    fig_radar = plot_performance_radar(predictions, name=label)
                    st.plotly_chart(fig_radar, use_container_width=True)

                # ─── ACTIONS — HORS du bloc optimize_button ───────────────
                st.markdown("#### ⚡ Actions")

                col_act1, col_act2 = st.columns(2)

                # ── Sauvegarde BDD ───────────────────────────────────────
                with col_act1:
                    if st.button(
                        "💾 Sauvegarder",
                        key=f"save_{obj_key}",        # clé unique
                        use_container_width=True,
                        type="primary",
                    ):
                        db = st.session_state.get("db_manager")
                        if db and db.is_connected:
                            try:
                                name_db = (
                                    f"Optimisée_{obj_key}_"
                                    f"{ts.strftime('%Y%m%d_%H%M')}"
                                )
                                success = db.save_prediction(
                                    composition, predictions, name_db
                                )
                                if success:
                                    st.session_state["total_saves"] = (
                                        st.session_state.get("total_saves", 0) + 1
                                    )
                                    st.success("Sauvegardée en BDD !")
                                    st.balloons()
                                else:
                                    st.error("❌ Échec sauvegarde")
                            except Exception as e:
                                st.error(f"❌ Erreur BDD : {e}")
                        else:
                            st.warning("⚠️ DB non connectée")

                # ── Ajouter aux favoris ──────────────────────────────────
                with col_act2:
                    fav_name = f"Optimisée_{obj_key}_{ts.strftime('%Y%m%d_%H%M')}"
                    favs     = st.session_state.get("favorites", [])
                    already  = any(f["name"] == fav_name for f in favs)

                    if st.button(
                        "⭐ Déjà en favoris" if already else "⭐ Favoris",
                        key=f"fav_{obj_key}",          
                        use_container_width=True,
                        disabled=already,
                    ):
                        favs.append({
                            "name":             fav_name,
                            "composition":      composition,
                            "predictions":      predictions,
                            "co2_result":       co2_result,
                            "required_class":   required_cls,
                            "achieved_class":   validation.achieved_class,
                            "compliance_score": validation.compliance_score,
                            "cost":             cost,
                            "cement_type":      cement_type,
                            "source":           "Optimiseur",
                            "objective":        obj_key,
                            "timestamp":        ts,
                        })
                        st.session_state["favorites"] = favs
                        st.success(f"⭐ Ajouté aux favoris !")
                        st.rerun()   # rafraîchit le label du bouton

                # ── Vers Formulateur ─────────────────────────────────────
                col_act3, col_act4 = st.columns(2)

                with col_act3:
                    if st.button(
                        "📊 Vers Formulateur",
                        key=f"to_form_{obj_key}",      # clé unique
                        use_container_width=True,
                    ):
                        st.session_state["imported_composition"] = composition
                        st.toast("Exportée vers le Formulateur", icon="📊")

                # ── Export CSV ───────────────────────────────────────────
                with col_act4:
                    import pandas as pd
                    export_data = {
                        **composition,
                        **predictions,
                        "Objectif":       obj_key,
                        "Cout_EUR_m3":    cost,
                        "CO2_kg_m3":      co2_total,
                        "Cement_Type":    cement_type,
                        "Classe_Exigee":  required_cls,
                        "Classe_Atteinte": validation.achieved_class or "N/A",
                        "Score_Conformite": validation.compliance_score,
                    }
                    csv_opt = pd.DataFrame([export_data]).to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "📥 CSV",
                        data=csv_opt,
                        file_name=f"optimal_{obj_key}_{ts.strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        key=f"dl_{obj_key}",           # clé unique
                        use_container_width=True,
                    )

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.get("optimization_history"):
    st.markdown("---")
    st.markdown("## 🕐 Historique des Optimisations")

    for opt in reversed(st.session_state["optimization_history"][-5:]):
        ts_label = opt["timestamp"].strftime("%Y-%m-%d %H:%M")
        obj_label = {"minimize_cost": "💰 Coût", "minimize_co2": "🌍 CO₂"}.get(
            opt["objective"], opt["objective"]
        )

        with st.expander(f"{ts_label} — {obj_label}", expanded=False):
            val = opt.get("validation")
            col_h1, col_h2, col_h3, col_h4 = st.columns(4)

            with col_h1:
                st.metric("Résistance", f"{opt.get('resistance', 0):.1f} MPa")
            with col_h2:
                st.metric("Coût", f"{opt.get('cost', 0):.2f} €/m³")
            with col_h3:
                st.metric("CO₂", f"{opt.get('co2_total', 0):.1f} kg/m³")
            with col_h4:
                if val:
                    verdict = "✅" if val.compliance_with_required else "❌"
                    st.caption(f"Classe : **{val.achieved_class or 'N/A'}** {verdict}")
                st.caption(f"Ciment : {opt.get('cement_type', 'N/A')}")

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.caption(f"🔬 **Optimisations** : {len(st.session_state.get('optimization_history', []))}")
with col_f2:
    st.caption(f"⭐ **Favoris** : {len(st.session_state.get('favorites', []))}")
with col_f3:
    st.caption(f"💾 **Sauvegardes** : {st.session_state.get('total_saves', 0)}")

st.caption(
    "🌍 Optimisation empreinte CO₂ | "
    "💡 CEM III/B recommandé pour béton bas-carbone"
)