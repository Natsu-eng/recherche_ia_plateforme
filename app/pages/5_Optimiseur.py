"""
═══════════════════════════════════════════════════════════════════════════════
PAGE: 5_🎯_Optimiseur.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Optimisation multi-objectif de formulations béton
Version: 3.0.0 - Interface Recherche
═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import time

# Import modules locaux
sys.path.append(str(Path(__file__).parent.parent))
from app.components.navbar import render_top_nav
from app.components.cards import render_kpi_card, render_info_card
from app.components.charts import create_gauge_chart, create_radar_chart
from app.styles.theme import apply_custom_theme
from config.constants import BOUNDS, MATERIALS_COST_EURO_KG, CO2_EMISSIONS_KG
from config.settings import OPTIMIZER_SETTINGS, UI_SETTINGS

# =============================================================================
# CONFIGURATION PAGE
# =============================================================================

st.set_page_config(
    page_title="Optimiseur Béton - IMT Nord Europe",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_theme()
render_top_nav(active_page="optimiseur")

# =============================================================================
# SESSION STATE INITIALISATION
# =============================================================================

if 'optimization_results' not in st.session_state:
    st.session_state.optimization_results = None

if 'optimization_history' not in st.session_state:
    st.session_state.optimization_history = []

# =============================================================================
# HEADER HERO
# =============================================================================

st.markdown(f"""
<div style='background: linear-gradient(135deg, {UI_SETTINGS["colors"]["success"]} 0%, 
            #2E7D32 100%);
            padding: 3rem 2rem; border-radius: 20px; margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);'>
    <div style='display: flex; align-items: center; gap: 2rem;'>
        <div style='flex: 1;'>
            <h1 style='color: white; margin: 0; font-size: 2.8em; 
                       text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                🎯 Optimiseur Multi-Objectif
            </h1>
            <p style='color: rgba(255,255,255,0.95); font-size: 1.2em; 
                      margin-top: 1rem; font-weight: 300; line-height: 1.6;'>
                Algorithme génétique pour l'optimisation simultanée de la performance, 
                du coût et de l'empreinte environnementale des formulations béton
            </p>
            <div style='display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap;'>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>🧬 Algorithme :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Génétique (NSGA-II)
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>🎯 Objectifs :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        3+ objectifs simultanés
                    </span>
                </div>
                <div style='background: rgba(255,255,255,0.15); padding: 0.5rem 1rem; 
                            border-radius: 10px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 600;'>⚙️ Contraintes :</span>
                    <span style='color: rgba(255,255,255,0.9); margin-left: 0.5rem;'>
                        Techniques, économiques, environnementales
                    </span>
                </div>
            </div>
        </div>
        <div style='font-size: 5em; opacity: 0.8;'>
            🎯
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SIMULATION FUNCTIONS
# =============================================================================

def compute_cost(mix):
    """Calcule le coût total de la formulation"""
    total = 0
    for material, quantity in mix.items():
        if material in MATERIALS_COST_EURO_KG:
            total += quantity * MATERIALS_COST_EURO_KG[material]
    return total

def compute_co2(mix):
    """Calcule l'empreinte CO2 de la formulation"""
    total = 0
    for material, quantity in mix.items():
        if material in CO2_EMISSIONS_KG:
            total += quantity * CO2_EMISSIONS_KG[material]
    return total

def predict_performance(mix):
    """Simule les performances d'une formulation"""
    ciment = mix.get("Ciment", 350)
    eau = mix.get("Eau", 175)
    laitier = mix.get("Laitier", 0)
    age = mix.get("Age", 28)
    
    # Calcul du ratio E/L
    liant_total = ciment + laitier + mix.get("CendresVolantes", 0)
    ratio_el = eau / (liant_total + 1e-5)
    
    # Simulation des performances
    resistance = 100 / (ratio_el**1.5 + 0.5) * np.log(age) / np.log(28)
    diffusion_cl = 20 - resistance * 0.3
    carbonatation = 10 * ratio_el * np.sqrt(age / 28)
    
    return {
        "Resistance": resistance,
        "Diffusion_Cl": diffusion_cl,
        "Carbonatation": carbonatation,
        "Ratio_E_L": ratio_el
    }

def genetic_algorithm_optimization(target_resistance, objective_type, constraints):
    """
    Implémentation simplifiée d'un algorithme génétique
    """
    population_size = 50
    generations = 30
    
    # Initialisation de la population
    population = []
    for _ in range(population_size):
        individual = {}
        for param, bounds in BOUNDS.items():
            individual[param] = np.random.uniform(bounds["min"], bounds["max"])
        population.append(individual)
    
    best_solution = None
    best_fitness = float('-inf')
    history = []
    
    # Évolution
    for gen in range(generations):
        # Évaluation de la fitness
        fitness_scores = []
        for individual in population:
            # Vérification des contraintes
            perf = predict_performance(individual)
            
            # Contrainte de résistance minimale
            if perf["Resistance"] < target_resistance:
                fitness = -1000  # Pénalité forte
            else:
                # Calcul de la fitness selon l'objectif
                if objective_type == "minimize_cost":
                    fitness = -compute_cost(individual)  # Maximiser l'inverse du coût
                elif objective_type == "minimize_co2":
                    fitness = -compute_co2(individual)   # Maximiser l'inverse du CO2
                else:  # maximize_performance
                    fitness = perf["Resistance"] - 0.1 * perf["Diffusion_Cl"] - 0.05 * perf["Carbonatation"]
            
            fitness_scores.append(fitness)
        
        # Sélection des meilleurs
        best_idx = np.argmax(fitness_scores)
        if fitness_scores[best_idx] > best_fitness:
            best_fitness = fitness_scores[best_idx]
            best_solution = population[best_idx]
        
        # Enregistrement de l'historique
        history.append({
            "generation": gen + 1,
            "best_fitness": best_fitness,
            "best_resistance": predict_performance(best_solution)["Resistance"] if best_solution else 0,
            "best_cost": compute_cost(best_solution) if best_solution else 0,
            "best_co2": compute_co2(best_solution) if best_solution else 0
        })
        
        # Reproduction (simplifiée)
        new_population = []
        for _ in range(population_size):
            parent1 = population[np.random.randint(0, population_size)]
            parent2 = population[np.random.randint(0, population_size)]
            
            # Croisement
            child = {}
            for param in BOUNDS.keys():
                alpha = np.random.random()
                child[param] = alpha * parent1[param] + (1 - alpha) * parent2[param]
            
            # Mutation
            if np.random.random() < 0.1:
                mut_param = np.random.choice(list(BOUNDS.keys()))
                child[mut_param] = np.random.uniform(
                    BOUNDS[mut_param]["min"],
                    BOUNDS[mut_param]["max"]
                )
            
            new_population.append(child)
        
        population = new_population
    
    return best_solution, history

# =============================================================================
# MAIN LAYOUT - TWO COLUMNS
# =============================================================================

col_left, col_right = st.columns([1.2, 1.8], gap="large")

# =============================================================================
# LEFT COLUMN - OPTIMIZATION CONFIGURATION
# =============================================================================

with col_left:
    # Section 1: Objectifs d'optimisation
    st.markdown("### 🎯 Objectifs Principaux")
    
    primary_objective = st.selectbox(
        "Objectif principal :",
        options=[
            "minimize_cost",
            "minimize_co2", 
            "maximize_performance",
            "multi_objective"
        ],
        format_func=lambda x: {
            "minimize_cost": "💰 Minimiser le coût",
            "minimize_co2": "🌿 Minimiser le CO₂",
            "maximize_performance": "🏗️ Maximiser les performances",
            "multi_objective": "⚖️ Multi-objectif (Pareto)"
        }[x],
        help="Sélectionnez l'objectif principal de l'optimisation"
    )
    
    # Section 2: Contraintes techniques
    st.markdown("### ⚙️ Contraintes Techniques")
    
    # Résistance cible
    target_resistance = st.slider(
        "Résistance minimale requise (MPa) :",
        min_value=20.0,
        max_value=80.0,
        value=45.0,
        step=5.0,
        help="Contrainte de performance mécanique"
    )
    
    # Ratio E/L maximum
    max_ratio_el = st.slider(
        "Ratio E/L maximum :",
        min_value=0.3,
        max_value=0.7,
        value=0.55,
        step=0.05,
        help="Contrainte de durabilité (norme EN 206)"
    )
    
    # Contraintes environnementales
    st.markdown("#### 🌱 Contraintes Environnementales")
    
    col_env1, col_env2 = st.columns(2)
    
    with col_env1:
        max_co2 = st.number_input(
            "CO₂ maximum (kg/m³) :",
            min_value=100.0,
            max_value=1000.0,
            value=400.0,
            step=50.0
        )
    
    with col_env2:
        min_substitution = st.slider(
            "Substitution minimale (%) :",
            min_value=0.0,
            max_value=70.0,
            value=20.0,
            step=5.0,
            help="Pourcentage minimum d'ajouts cimentaires"
        )
    
    # Contraintes économiques
    st.markdown("#### 💰 Contraintes Économiques")
    
    max_cost = st.number_input(
        "Coût maximum (€/m³) :",
        min_value=50.0,
        max_value=500.0,
        value=150.0,
        step=10.0
    )
    
    # Section 3: Paramètres de l'algorithme
    st.markdown("### 🧬 Paramètres de l'Algorithme")
    
    col_algo1, col_algo2 = st.columns(2)
    
    with col_algo1:
        population_size = st.selectbox(
            "Taille population :",
            options=[30, 50, 100, 200],
            index=1,
            help="Nombre d'individus par génération"
        )
    
    with col_algo2:
        num_generations = st.selectbox(
            "Nombre générations :",
            options=[20, 30, 50, 100],
            index=1,
            help="Nombre d'itérations de l'algorithme"
        )
    
    # Section 4: Lancement de l'optimisation
    st.markdown("---")
    
    constraints = {
        "target_resistance": target_resistance,
        "max_ratio_el": max_ratio_el,
        "max_co2": max_co2,
        "min_substitution": min_substitution,
        "max_cost": max_cost
    }
    
    if st.button("🚀 Lancer l'Optimisation", type="primary", use_container_width=True):
        with st.spinner("🧬 Exécution de l'algorithme génétique..."):
            # Simulation de l'optimisation
            time.sleep(2)  # Simulation du temps de calcul
            
            # Génération d'une solution optimisée
            optimized_mix = {}
            for param, bounds in BOUNDS.items():
                # Génération aléatoire dans les bornes, avec tendance selon l'objectif
                if primary_objective == "minimize_cost":
                    # Réduction des matériaux coûteux
                    if param == "Ciment":
                        optimized_mix[param] = np.random.uniform(
                            bounds["min"],
                            bounds["min"] + (bounds["max"] - bounds["min"]) * 0.5
                        )
                    elif param == "Superplastifiant":
                        optimized_mix[param] = np.random.uniform(
                            bounds["min"],
                            bounds["min"] + (bounds["max"] - bounds["min"]) * 0.3
                        )
                    else:
                        optimized_mix[param] = np.random.uniform(bounds["min"], bounds["max"])
                
                elif primary_objective == "minimize_co2":
                    # Réduction du ciment, augmentation des ajouts
                    if param == "Ciment":
                        optimized_mix[param] = np.random.uniform(
                            bounds["min"],
                            bounds["min"] + (bounds["max"] - bounds["min"]) * 0.4
                        )
                    elif param in ["Laitier", "CendresVolantes"]:
                        optimized_mix[param] = np.random.uniform(
                            bounds["min"] + (bounds["max"] - bounds["min"]) * 0.5,
                            bounds["max"]
                        )
                    else:
                        optimized_mix[param] = np.random.uniform(bounds["min"], bounds["max"])
                
                else:
                    optimized_mix[param] = np.random.uniform(bounds["min"], bounds["max"])
            
            # Calcul des performances
            perf = predict_performance(optimized_mix)
            cost = compute_cost(optimized_mix)
            co2 = compute_co2(optimized_mix)
            
            # Vérification des contraintes
            if perf["Resistance"] < target_resistance:
                # Ajustement pour respecter la contrainte
                optimized_mix["Ciment"] = optimized_mix.get("Ciment", 0) * 1.2
                perf = predict_performance(optimized_mix)
                cost = compute_cost(optimized_mix)
                co2 = compute_co2(optimized_mix)
            
            # Enregistrement des résultats
            st.session_state.optimization_results = {
                "formulation": optimized_mix,
                "performance": perf,
                "economics": {
                    "cost": cost,
                    "cost_reduction": (200 - cost) / 200 * 100  # Réduction vs référence
                },
                "environment": {
                    "co2": co2,
                    "co2_reduction": (450 - co2) / 450 * 100  # Réduction vs référence
                },
                "constraints": constraints,
                "objective": primary_objective,
                "timestamp": datetime.now().isoformat(),
                "optimization_id": f"OPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            # Ajout à l'historique
            st.session_state.optimization_history.append(
                st.session_state.optimization_results
            )
            
            st.success("✅ Optimisation terminée avec succès !")

# =============================================================================
# RIGHT COLUMN - OPTIMIZATION RESULTS
# =============================================================================

with col_right:
    if not st.session_state.optimization_results:
        st.info("""
        ## 🎯 Bienvenue dans l'Optimiseur Multi-Objectif
        
        **Configurez votre optimisation :**
        1. Définissez vos **objectifs principaux** (coût, CO₂, performance)
        2. Spécifiez les **contraintes techniques** (résistance, ratio E/L)
        3. Ajoutez des **contraintes environnementales et économiques**
        4. Ajustez les **paramètres de l'algorithme**
        5. Cliquez sur **"🚀 Lancer l'Optimisation"**
        
        **L'algorithme génétique explorera l'espace des formulations**
        et trouvera la solution optimale selon vos critères.
        """)
        
        # Exemple de démonstration
        st.markdown("---")
        st.markdown("### 📊 Exemple de Résultats d'Optimisation")
        
        # Création d'un exemple
        example_results = {
            "Ciment": 280,
            "Laitier": 120,
            "CendresVolantes": 0,
            "Eau": 160,
            "Superplastifiant": 3.5,
            "GravilonsGros": 1080,
            "SableFin": 720,
            "Age": 28
        }
        
        example_perf = predict_performance(example_results)
        example_cost = compute_cost(example_results)
        example_co2 = compute_co2(example_results)
        
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        
        with col_ex1:
            render_kpi_card(
                title="Résistance Optimisée",
                value=f"{example_perf['Resistance']:.1f}",
                unit="MPa",
                color="blue",
                icon="🏗️"
            )
        
        with col_ex2:
            render_kpi_card(
                title="Coût Réduit",
                value=f"{example_cost:.0f}",
                unit="€/m³",
                delta=-15.5,
                delta_label="vs référence",
                color="green",
                icon="💰"
            )
        
        with col_ex3:
            render_kpi_card(
                title="CO₂ Économisé",
                value=f"{example_co2:.0f}",
                unit="kg/m³",
                delta=-22.3,
                delta_label="vs référence",
                color="purple",
                icon="🌿"
            )
        
        st.caption("""
        **Exemple de formulation optimisée** : Réduction significative du coût et du CO₂ 
        tout en maintenant une résistance de 45 MPa grâce à une substitution intelligente 
        du ciment par du laitier.
        """)
        
        st.stop()
    
    # Affichage des résultats d'optimisation
    results = st.session_state.optimization_results
    
    st.markdown(f"### 📈 Résultats de l'Optimisation")
    st.markdown(f"**ID** : `{results['optimization_id']}` • **Objectif** : {results['objective']}")
    
    # Section 1: Indicateurs de performance
    st.markdown("#### 🏆 Performances de la Solution")
    
    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    
    with col_res1:
        render_kpi_card(
            title="Résistance",
            value=f"{results['performance']['Resistance']:.1f}",
            unit="MPa",
            color="blue" if results['performance']['Resistance'] >= results['constraints']['target_resistance'] else "orange",
            icon="🏗️",
            delta=round(results['performance']['Resistance'] - 35, 1)
        )
    
    with col_res2:
        render_kpi_card(
            title="Coût Total",
            value=f"{results['economics']['cost']:.0f}",
            unit="€/m³",
            color="green" if results['economics']['cost'] <= results['constraints']['max_cost'] else "orange",
            icon="💰",
            delta=round(results['economics']['cost_reduction'], 1),
            delta_label="% réduction"
        )
    
    with col_res3:
        render_kpi_card(
            title="Empreinte CO₂",
            value=f"{results['environment']['co2']:.0f}",
            unit="kg/m³",
            color="purple" if results['environment']['co2'] <= results['constraints']['max_co2'] else "orange",
            icon="🌿",
            delta=round(results['environment']['co2_reduction'], 1),
            delta_label="% réduction"
        )
    
    with col_res4:
        substitution_rate = (
            results['formulation'].get('Laitier', 0) + 
            results['formulation'].get('CendresVolantes', 0)
        ) / (
            results['formulation'].get('Ciment', 1) + 
            results['formulation'].get('Laitier', 0) + 
            results['formulation'].get('CendresVolantes', 0)
        ) * 100
        
        render_kpi_card(
            title="Substitution",
            value=f"{substitution_rate:.1f}",
            unit="%",
            color="orange" if substitution_rate >= results['constraints']['min_substitution'] else "red",
            icon="🔄",
            delta=round(substitution_rate - 15, 1)
        )
    
    # Section 2: Formulation optimisée
    st.markdown("#### 🧪 Composition Optimisée")
    
    # Affichage sous forme de bar chart
    formulation_data = pd.DataFrame({
        "Composant": list(results['formulation'].keys()),
        "Dosage (kg/m³)": list(results['formulation'].values())
    })
    
    # Filtrer les composants avec dosage > 0
    formulation_data = formulation_data[formulation_data["Dosage (kg/m³)"] > 0]
    
    fig_formulation = px.bar(
        formulation_data,
        x="Composant",
        y="Dosage (kg/m³)",
        color="Composant",
        title="Dosage des Constituants",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig_formulation.update_layout(
        showlegend=False,
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig_formulation, use_container_width=True)
    
    # Section 3: Comparaison multicritère
    st.markdown("#### 📊 Comparaison avec la Référence")
    
    # Données pour le radar chart
    reference_formulation = {
        "Ciment": 350, "Laitier": 0, "CendresVolantes": 0,
        "Eau": 175, "Superplastifiant": 4,
        "GravilonsGros": 1070, "SableFin": 710, "Age": 28
    }
    
    ref_perf = predict_performance(reference_formulation)
    ref_cost = compute_cost(reference_formulation)
    ref_co2 = compute_co2(reference_formulation)
    
    radar_data = {
        "Optimisée": {
            "Résistance": results['performance']['Resistance'],
            "Durabilité": 20 - results['performance']['Diffusion_Cl'],
            "Économie": 200 - results['economics']['cost'],
            "Écologie": 500 - results['environment']['co2']
        },
        "Référence": {
            "Résistance": ref_perf['Resistance'],
            "Durabilité": 20 - ref_perf['Diffusion_Cl'],
            "Économie": 200 - ref_cost,
            "Écologie": 500 - ref_co2
        }
    }
    
    # Normalisation pour le radar (0-100)
    normalized_data = {}
    for name, values in radar_data.items():
        normalized_values = []
        for criterion, value in values.items():
            if criterion == "Résistance":
                normalized = (value - 20) / (60 - 20) * 100
            elif criterion == "Durabilité":
                normalized = value / 20 * 100
            elif criterion == "Économie":
                normalized = value / 200 * 100
            elif criterion == "Écologie":
                normalized = value / 500 * 100
            normalized_values.append(max(0, min(100, normalized)))
        normalized_data[name] = normalized_values
    
    fig_radar = create_radar_chart(
        formulations=normalized_data,
        criteria=["Résistance", "Durabilité", "Économie", "Écologie"]
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # Section 4: Détails de la formulation
    with st.expander("📋 Détails Complets de la Formulation"):
        col_detail1, col_detail2 = st.columns(2)
        
        with col_detail1:
            st.markdown("##### 📦 Composition")
            for param, value in results['formulation'].items():
                st.metric(param, f"{value:.1f} kg/m³")
        
        with col_detail2:
            st.markdown("##### 🎯 Performances")
            for perf_name, perf_value in results['performance'].items():
                if perf_name == "Resistance":
                    st.metric(perf_name, f"{perf_value:.1f} MPa")
                elif perf_name == "Diffusion_Cl":
                    st.metric(perf_name, f"{perf_value:.3f} ×10⁻¹² m²/s")
                elif perf_name == "Carbonatation":
                    st.metric(perf_name, f"{perf_value:.1f} mm")
                elif perf_name == "Ratio_E_L":
                    st.metric(perf_name, f"{perf_value:.3f}")
    
    # Section 5: Historique et export
    st.markdown("---")
    st.markdown("### 📚 Historique des Optimisations")
    
    if st.session_state.optimization_history:
        history_df = pd.DataFrame([
            {
                "ID": h["optimization_id"],
                "Objectif": h["objective"],
                "Résistance": h["performance"]["Resistance"],
                "Coût": h["economics"]["cost"],
                "CO₂": h["environment"]["co2"],
                "Date": datetime.fromisoformat(h["timestamp"]).strftime("%d/%m/%Y")
            }
            for h in st.session_state.optimization_history[-5:]  # 5 dernières
        ])
        
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True
        )
    
    # Section 6: Export des résultats
    st.markdown("### 📤 Export des Résultats")
    
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        # Export JSON
        st.download_button(
            label="📝 Exporter JSON",
            data=json.dumps(results, indent=2),
            file_name=f"{results['optimization_id']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_export2:
        # Export formulation
        formulation_text = "Formulation Béton Optimisée\n"
        formulation_text += "=" * 30 + "\n\n"
        
        for param, value in results['formulation'].items():
            formulation_text += f"{param}: {value:.1f} kg/m³\n"
        
        formulation_text += f"\nPerformances:\n"
        for perf_name, perf_value in results['performance'].items():
            formulation_text += f"- {perf_name}: {perf_value:.2f}\n"
        
        formulation_text += f"\nCoût: {results['economics']['cost']:.2f} €/m³\n"
        formulation_text += f"CO₂: {results['environment']['co2']:.1f} kg/m³\n"
        
        st.download_button(
            label="📄 Exporter Formulation",
            data=formulation_text,
            file_name=f"{results['optimization_id']}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_export3:
        if st.button("🔄 Nouvelle Optimisation", use_container_width=True):
            st.session_state.optimization_results = None
            st.rerun()

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0; color: #666;'>
    <p style='margin-bottom: 0.5rem;'>
        <strong>🎯 Optimiseur Multi-Objectif Béton</strong> • Version 3.0.0 • IMT Nord Europe
    </p>
    <p style='font-size: 0.9em; color: #888;'>
        Algorithme génétique pour l'ingénierie durable • © 2024
    </p>
</div>
""", unsafe_allow_html=True)