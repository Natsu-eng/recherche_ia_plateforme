"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: Analyse Carbone - Impact Environnemental
Fichier: pages/7_Analyse_Carbone.py
Version: 1.0.0 - Auto-ajustement composition selon type ciment
═══════════════════════════════════════════════════════════════════════════════

NOUVEAUTÉ v1.2.0:
✅ Composition s'ajuste automatiquement selon type de ciment choisi
✅ Calcul dosage laitier/cendres selon proportions normatives
✅ Option verrouillage manuel
"""

import streamlit as st
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.settings import APP_SETTINGS
from config.constants import COLOR_PALETTE
from app.styles.theme import apply_custom_theme
from app.components.sidebar import render_sidebar
from app.components.cards import metric_card, info_box

# ✅ IMPORTS CO₂
from app.core.co2_calculator import CO2Calculator, get_environmental_grade
from config.co2_database import (
    CEMENT_CO2_KG_PER_TONNE,
    CEMENT_COMPOSITIONS,
    CO2_CLASSES,
    CO2_EQUIVALENTS,
    get_reduction_potential
)

from app.core.session_manager import initialize_session
initialize_session()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Analyse Carbone - Béton IA",
    page_icon="🌍",
    layout="wide"
)

apply_custom_theme(st.session_state.get('app_theme', 'Clair'))
render_sidebar(db_manager=st.session_state.get('db_manager'))

# ═══════════════════════════════════════════════════════════════════════════════
# ✅ FONCTION AJUSTEMENT COMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

def adjust_composition_for_cement(cement_type: str, total_liant: float = 350) -> dict:
    """
    Ajuste la composition selon le type de ciment.
    
    Args:
        cement_type: Type de ciment (ex: 'CEM III/B')
        total_liant: Dosage total de liant (kg/m³)
    
    Returns:
        Dict avec dosages ajustés {Ciment, Laitier, Cendres}
    """
    composition = CEMENT_COMPOSITIONS.get(cement_type, {})
    
    # Calcul dosages selon proportions
    clinker_pct = composition.get('Clinker', 1.0)
    laitier_pct = composition.get('Laitier', 0.0)
    cendres_pct = composition.get('CendresVolantes', 0.0)
    
    # Dosage effectif
    ciment_effectif = total_liant * clinker_pct
    laitier_effectif = total_liant * laitier_pct
    cendres_effectif = total_liant * cendres_pct
    
    return {
        'Ciment': round(ciment_effectif, 1),
        'Laitier': round(laitier_effectif, 1),
        'Cendres': round(cendres_effectif, 1),
        'Liant_Total': total_liant
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALISATION SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

if 'co2_last_cement_type' not in st.session_state:
    st.session_state['co2_last_cement_type'] = 'CEM I'

if 'co2_calc_liant_total' not in st.session_state:
    st.session_state['co2_calc_liant_total'] = 350

if 'co2_calc_ciment' not in st.session_state:
    st.session_state['co2_calc_ciment'] = 350

if 'co2_calc_laitier' not in st.session_state:
    st.session_state['co2_calc_laitier'] = 0

if 'co2_calc_cendres' not in st.session_state:
    st.session_state['co2_calc_cendres'] = 0

if 'co2_calc_eau' not in st.session_state:
    st.session_state['co2_calc_eau'] = 175

if 'co2_calc_sable' not in st.session_state:
    st.session_state['co2_calc_sable'] = 800

if 'co2_calc_gravier' not in st.session_state:
    st.session_state['co2_calc_gravier'] = 1000

if 'co2_calc_adjuvant' not in st.session_state:
    st.session_state['co2_calc_adjuvant'] = 0.0

if 'co2_manual_mode' not in st.session_state:
    st.session_state['co2_manual_mode'] = False

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"""
    <h1 style="color: {COLOR_PALETTE['primary']}; border-bottom: 3px solid {COLOR_PALETTE['accent']}; padding-bottom: 0.5rem;">
        🌍 Analyse Carbone - Impact Environnemental
    </h1>
    <p style="font-size: 1.1rem; color: {COLOR_PALETTE['secondary']}; margin-top: 0.5rem;">
        Calculez, comparez et optimisez l'empreinte carbone de vos formulations béton.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# ONGLETS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════════════════════

tab_calc, tab_compare, tab_optim, tab_educ = st.tabs([
    "🧮 Calculateur",
    "⚖️ Comparaison Ciments",
    "🎯 Optimisation",
    "📚 Éducation"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 : CALCULATEUR AVEC AUTO-AJUSTEMENT
# ═══════════════════════════════════════════════════════════════════════════════

with tab_calc:
    st.markdown("### 🧮 Calculateur CO₂ Interactif")
    
    col_input, col_results = st.columns([1, 1])
    
    # ───────────────────────────────────────────────────────────────
    # ENTRÉES AVEC AUTO-AJUSTEMENT
    # ───────────────────────────────────────────────────────────────
    
    with col_input:
        st.markdown("#### Composition (kg/m³)")
        
        # ✅ Type ciment
        cement_type = st.selectbox(
            "🏭 Type de Ciment",
            options=list(CEMENT_CO2_KG_PER_TONNE.keys()),
            index=list(CEMENT_CO2_KG_PER_TONNE.keys()).index(st.session_state['co2_last_cement_type']),
            key='cement_type_selector',
            help="La composition s'ajuste automatiquement selon le type choisi"
        )
        
        cement_factor = CEMENT_CO2_KG_PER_TONNE[cement_type]
        st.caption(f"📊 Facteur CO₂ : {cement_factor:.1f} kg CO₂/t")
        
        # ✅ DÉTECTION CHANGEMENT TYPE CIMENT
        cement_type_changed = (cement_type != st.session_state['co2_last_cement_type'])
        
        if cement_type_changed and not st.session_state['co2_manual_mode']:
            # Ajuster composition automatiquement
            adjusted = adjust_composition_for_cement(
                cement_type, 
                st.session_state['co2_calc_liant_total']
            )
            
            st.session_state['co2_calc_ciment'] = adjusted['Ciment']
            st.session_state['co2_calc_laitier'] = adjusted['Laitier']
            st.session_state['co2_calc_cendres'] = adjusted['Cendres']
            
            st.session_state['co2_last_cement_type'] = cement_type
            
            # Info utilisateur
            st.info(f"✨ Composition ajustée pour **{cement_type}** : "
                   f"Clinker={adjusted['Ciment']:.0f} kg, "
                   f"Laitier={adjusted['Laitier']:.0f} kg, "
                   f"Cendres={adjusted['Cendres']:.0f} kg")
        
        st.markdown("---")
        
        # ✅ Option mode manuel
        manual_mode = st.checkbox(
            "🔓 Mode manuel (désactiver ajustement auto)",
            value=st.session_state['co2_manual_mode'],
            help="Permet de saisir des dosages personnalisés"
        )
        st.session_state['co2_manual_mode'] = manual_mode
        
        st.markdown("---")
        
        # ✅ Liant Total (contrôle global)
        liant_total = st.number_input(
            "Liant Total (kg/m³)",
            min_value=200,
            max_value=600,
            value=int(st.session_state['co2_calc_liant_total']),
            step=10,
            key='input_liant_total',
            help="Dosage total de liant (ajuste proportions)"
        )
        
        # Si liant total change en mode auto → recalculer
        if liant_total != st.session_state['co2_calc_liant_total'] and not manual_mode:
            adjusted = adjust_composition_for_cement(cement_type, liant_total)
            st.session_state['co2_calc_ciment'] = adjusted['Ciment']
            st.session_state['co2_calc_laitier'] = adjusted['Laitier']
            st.session_state['co2_calc_cendres'] = adjusted['Cendres']
        
        st.session_state['co2_calc_liant_total'] = liant_total
        
        st.markdown("---")
        
        # ✅ Dosages détaillés
        col_dose1, col_dose2 = st.columns(2)
        
        with col_dose1:
            st.markdown("**Liants**")
            
            ciment = st.number_input(
                "Clinker (kg/m³)", 
                0, 600, 
                value=int(st.session_state['co2_calc_ciment']),
                step=10,
                key='input_ciment',
                disabled=(not manual_mode)
            )
            if manual_mode:
                st.session_state['co2_calc_ciment'] = ciment
            
            laitier = st.number_input(
                "Laitier (kg/m³)", 
                0, 400, 
                value=int(st.session_state['co2_calc_laitier']),
                step=10,
                key='input_laitier',
                disabled=(not manual_mode)
            )
            if manual_mode:
                st.session_state['co2_calc_laitier'] = laitier
            
            cendres = st.number_input(
                "Cendres (kg/m³)", 
                0, 200, 
                value=int(st.session_state['co2_calc_cendres']),
                step=10,
                key='input_cendres',
                disabled=(not manual_mode)
            )
            if manual_mode:
                st.session_state['co2_calc_cendres'] = cendres
            
            eau = st.number_input(
                "Eau (kg/m³)", 
                100, 250, 
                value=int(st.session_state['co2_calc_eau']),
                step=5,
                key='input_eau'
            )
            st.session_state['co2_calc_eau'] = eau
        
        with col_dose2:
            st.markdown("**Granulats**")
            
            sable = st.number_input(
                "Sable (kg/m³)", 
                500, 1000, 
                value=int(st.session_state['co2_calc_sable']),
                step=10,
                key='input_sable'
            )
            st.session_state['co2_calc_sable'] = sable
            
            gravier = st.number_input(
                "Gravier (kg/m³)", 
                800, 1200, 
                value=int(st.session_state['co2_calc_gravier']),
                step=10,
                key='input_gravier'
            )
            st.session_state['co2_calc_gravier'] = gravier
            
            adjuvant = st.number_input(
                "Superplast. (kg/m³)", 
                0.0, 15.0, 
                value=float(st.session_state['co2_calc_adjuvant']),
                step=0.5,
                key='input_adjuvant'
            )
            st.session_state['co2_calc_adjuvant'] = adjuvant
        
        # Vérification cohérence
        liant_reel = ciment + laitier + cendres
        if abs(liant_reel - liant_total) > 5:
            st.warning(f"⚠️ Incohérence : Liant total={liant_total} kg mais Σ(Clinker+Laitier+Cendres)={liant_reel:.0f} kg")
        
        st.markdown("---")
        
        # ✅ Options calcul
        col_opt1, col_opt2 = st.columns(2)
        
        with col_opt1:
            auto_calc = st.checkbox("Calcul automatique", value=False)
        
        with col_opt2:
            calc_button = st.button("🚀 Calculer CO₂", type="primary", use_container_width=True, disabled=auto_calc)
    
    # ───────────────────────────────────────────────────────────────
    # RÉSULTATS
    # ───────────────────────────────────────────────────────────────
    
    with col_results:
        st.markdown("#### Résultats")
        
        should_calculate = calc_button or auto_calc
        
        if should_calculate:
            try:
                calc = CO2Calculator()
                result = calc.calculate(
                    formulation={
                        'Ciment': ciment,
                        'Laitier': laitier,
                        'CendresVolantes': cendres,
                        'Eau': eau,
                        'SableFin': sable,
                        'GravilonsGros': gravier,
                        'Superplastifiant': adjuvant
                    },
                    cement_type=cement_type
                )
                
                co2_total = result.co2_total_kg_m3
                classe, emoji, color = get_environmental_grade(co2_total)
                
                # Affichage principal
                st.markdown(f"### {emoji} {co2_total:.1f} kg CO₂/m³")
                st.markdown(f"**Classe** : {classe}")
                
                # Métriques détaillées
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    st.metric("🏭 Ciment", f"{result.co2_ciment:.1f} kg")
                    pct_ciment = result.co2_ciment / co2_total * 100
                    st.caption(f"{pct_ciment:.0f}% du total")
                
                with col_m2:
                    st.metric("🪨 Granulats", f"{result.co2_sable + result.co2_gravier:.1f} kg")
                    pct_gran = (result.co2_sable + result.co2_gravier) / co2_total * 100
                    st.caption(f"{pct_gran:.0f}% du total")
                
                with col_m3:
                    st.metric("💧 Autres", f"{result.co2_eau + result.co2_adjuvants:.1f} kg")
                
                st.markdown("---")
                
                # Répartition graphique
                breakdown = calc.get_breakdown_percentages(result)
                filtered = {k: v for k, v in breakdown.items() if v > 1}
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(filtered.keys()),
                    values=list(filtered.values()),
                    hole=0.4,
                    marker=dict(colors=['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6'])
                )])
                
                fig_pie.update_layout(title=f"Répartition CO₂ - {co2_total:.1f} kg/m³", height=350)
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Équivalences
                st.markdown("#### 🌳 Équivalences Pédagogiques")
                
                arbres = co2_total / CO2_EQUIVALENTS['arbre_annee']
                voiture_km = co2_total / CO2_EQUIVALENTS['voiture_km']
                
                st.markdown(f"• **{arbres:.1f} arbres** / an pour compenser")
                st.markdown(f"• **{voiture_km:.0f} km** en voiture")
                
                # Suggestions
                if co2_total > 300:
                    st.markdown("---")
                    st.markdown("#### 💡 Suggestions Réduction")
                    
                    suggestions = calc.suggest_reduction(result, target_reduction_percent=30)
                    
                    for i, sugg in enumerate(suggestions['suggestions'][:3], 1):
                        st.info(f"**{i}.** {sugg['action']}  \n→ {sugg['reduction_potentielle']}")
            
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                logger.error(f"Erreur calcul CO₂: {e}", exc_info=True)
        
        else:
            info_box(
                "Mode d'emploi",
                """
                1. **Choisissez** le type de ciment
                2. La composition **s'ajuste automatiquement**
                3. Ajustez le **liant total** si besoin
                4. Mode manuel pour personnalisation complète
                
                **Le ciment représente 70-85% de l'empreinte totale**
                """,
                icon="ℹ️",
                color="info"
            )

# ═══════════════════════════════════════════════════════════════════════════════
# TABS 2, 3, 4 : INCHANGÉS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_compare:
    st.markdown("### ⚖️ Comparaison Types de Ciments")
    st.markdown("""**Question** : Quel impact a le choix du ciment ?  
    **Réponse** : Entre **50% et 70% de réduction** possible !""")
    
    st.markdown("#### 📋 Formulation de Référence")
    col_ref1, col_ref2 = st.columns(2)
    with col_ref1:
        st.markdown("• Ciment : 350 kg/m³\n• Eau : 175 kg/m³\n• Sable : 800 kg/m³")
    with col_ref2:
        st.markdown("• Gravier : 1000 kg/m³\n• Laitier : 0 kg/m³\n• Cendres : 0 kg/m³")
    
    ref_composition = {'Ciment': 350, 'Laitier': 0, 'CendresVolantes': 0, 'Eau': 175, 
                      'SableFin': 800, 'GravilonsGros': 1000, 'Superplastifiant': 0}
    
    if st.button("🔄 Comparer Tous les Ciments", type="primary"):
        calc = CO2Calculator()
        results_comparison = []
        
        for cement in CEMENT_CO2_KG_PER_TONNE.keys():
            result = calc.calculate(ref_composition, cement)
            results_comparison.append({
                'Ciment': cement, 'CO2_kg_m3': result.co2_total_kg_m3,
                'Facteur_CO2': CEMENT_CO2_KG_PER_TONNE[cement]
            })
        
        df_comp = pd.DataFrame(results_comparison).sort_values('CO2_kg_m3')
        
        colors_comp = ['#2ecc71' if co2<200 else '#27ae60' if co2<280 else '#f39c12' if co2<350 else '#e74c3c' 
                      for co2 in df_comp['CO2_kg_m3']]
        
        fig_comp = go.Figure(data=[go.Bar(x=df_comp['Ciment'], y=df_comp['CO2_kg_m3'], 
                                         marker_color=colors_comp, text=df_comp['CO2_kg_m3'].round(1), 
                                         textposition='outside')])
        fig_comp.update_layout(title="Comparaison Empreinte CO₂", xaxis_title="Type", 
                              yaxis_title="kg CO₂/m³", height=500, showlegend=False)
        fig_comp.add_hline(y=200, line_dash="dash", line_color="green", annotation_text="Très Faible")
        fig_comp.add_hline(y=280, line_dash="dash", line_color="orange", annotation_text="Moyen")
        fig_comp.add_hline(y=350, line_dash="dash", line_color="red", annotation_text="Élevé")
        
        st.plotly_chart(fig_comp, use_container_width=True)
        
        df_comp['Reduction_vs_CEM_I'] = (1 - df_comp['CO2_kg_m3'] / df_comp['CO2_kg_m3'].max()) * 100
        st.dataframe(df_comp.style.background_gradient(cmap='RdYlGn_r', subset=['CO2_kg_m3'])
                    .format({'CO2_kg_m3': '{:.1f}', 'Facteur_CO2': '{:.1f}', 'Reduction_vs_CEM_I': '{:.0f}%'}),
                    use_container_width=True, height=400)
        
        st.markdown("#### 🥇 Top 3 Recommandations")
        top3 = df_comp.head(3)
        for i, row in enumerate(top3.itertuples(), 1):
            emoji = "🥇" if i==1 else ("🥈" if i==2 else "🥉")
            st.success(f"{emoji} **{row.Ciment}** : {row.CO2_kg_m3:.1f} kg ({row.Reduction_vs_CEM_I:.0f}% vs CEM I)")

with tab_optim:
    st.info("⚠️ Optimisation - Disponible dans module Optimiseur principal")

with tab_educ:
    st.markdown("### 📚 Éducation & Références")
    st.markdown("#### 🎨 Classes Environnementales")
    df_classes = pd.DataFrame([
        {'Classe': 'Très Faible', 'Range': '0-200', 'Emoji': '🟢', 'Ex': 'CEM III/C'},
        {'Classe': 'Faible', 'Range': '200-280', 'Emoji': '🟢', 'Ex': 'CEM III/B'},
        {'Classe': 'Moyen', 'Range': '280-350', 'Emoji': '🟡', 'Ex': 'CEM II/B'},
        {'Classe': 'Élevé', 'Range': '350-420', 'Emoji': '🟠', 'Ex': 'CEM II/A'},
        {'Classe': 'Très Élevé', 'Range': '>420', 'Emoji': '🔴', 'Ex': 'CEM I'}
    ])
    st.dataframe(df_classes, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: st.caption("🌍 **Calculateur** : NF EN 15804")
with col_f2: st.caption("📊 **Source** : ATILH 2024")
with col_f3: st.caption("♻️ **Objectif** : RE2020 < 280 kg/m³")
st.caption("💡 **CEM III/B recommandé** (-63% vs CEM I)")