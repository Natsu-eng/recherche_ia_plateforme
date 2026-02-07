"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/tables.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Tableaux interactifs et stylisés
Version: 1.0.0 - Production Ready
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st  # type: ignore
import pandas as pd
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go  # type: ignore


def render_formulation_table(
    formulation: Dict[str, float],
    predictions: Dict[str, float],
    show_units: bool = True
) -> None:
    """
    Affiche un tableau élégant de formulation avec prédictions.
    
    Args:
        formulation: Composition béton
        predictions: Résultats prédictions ML
        show_units: Afficher les unités
    """
    # Créer DataFrame pour affichage
    data = []
    
    # 1. COMPOSITION
    for param, value in formulation.items():
        unit = "kg/m³" if param != "Age" else "jours"
        data.append({
            "Catégorie": "📦 Composition",
            "Paramètre": param,
            "Valeur": f"{value:,.1f} {unit}" if show_units else f"{value:,.1f}",
            "Type": "Input"
        })
    
    # 2. PRÉDICTIONS
    pred_mapping = {
        "Resistance": ("🎯 Résistance", "MPa"),
        "Diffusion_Cl": ("🔬 Diffusion Cl⁻", "×10⁻¹² m²/s"),
        "Carbonatation": ("🏗️ Carbonatation", "mm"),
        "Ratio_E_L": ("💧 Ratio E/L", ""),
        "Liant_Total": ("🧱 Liant Total", "kg/m³")
    }
    
    for pred_key, (display_name, unit) in pred_mapping.items():
        if pred_key in predictions:
            value = predictions[pred_key]
            display = f"{value:,.2f} {unit}" if show_units and unit else f"{value:,.2f}"
            data.append({
                "Catégorie": "📊 Prédictions",
                "Paramètre": display_name,
                "Valeur": display,
                "Type": "Output"
            })
    
    df = pd.DataFrame(data)
    
    # Style CSS pour le tableau
    st.markdown("""
    <style>
        .imt-table {
            width: 100%;
            border-collapse: collapse;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin: 1rem 0;
        }
        
        .imt-table th {
            background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
            color: white;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            border: none;
        }
        
        .imt-table td {
            padding: 10px 16px;
            border-bottom: 1px solid #E0E0E0;
        }
        
        .imt-table tr:hover {
            background-color: #f5f7fa;
        }
        
        .input-row {
            background-color: #f8f9fa;
        }
        
        .output-row {
            background-color: #fff;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Affichage tableau
    for _, row in df.iterrows():
        row_class = "input-row" if row["Type"] == "Input" else "output-row"
        st.markdown(f"""
        <div class="{row_class}" style="
            padding: 10px 16px;
            margin: 2px 0;
            border-left: 4px solid {'#1976D2' if row['Type'] == 'Input' else '#388E3C'};
            background: {'#f8f9fa' if row['Type'] == 'Input' else 'white'};
            border-radius: 5px;
        ">
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <strong>{row['Paramètre']}</strong>
                    <div style="color: #666; font-size: 0.85rem;">
                        {row['Catégorie']}
                    </div>
                </div>
                <div style="font-weight: 600; color: #333;">
                    {row['Valeur']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_comparison_table(
    formulations: List[Dict[str, float]],
    names: List[str],
    predictions: List[Dict[str, float]]
) -> pd.DataFrame:
    """
    Affiche un tableau comparatif de plusieurs formulations.
    
    Args:
        formulations: Liste de compositions
        names: Noms des formulations
        predictions: Liste de prédictions correspondantes
    
    Returns:
        DataFrame pour export
    """
    # Préparer données
    data = []
    
    for i, (form, name, pred) in enumerate(zip(formulations, names, predictions)):
        row = {"Formulation": name}
        
        # Composition
        for param, value in form.items():
            row[param] = f"{value:.0f}"
        
        # Prédictions
        for pred_key, pred_value in pred.items():
            if pred_key not in ["Ratio_E_L", "Liant_Total"]:
                row[pred_key] = f"{pred_value:.1f}"
            else:
                row[pred_key] = f"{pred_value:.2f}"
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Afficher avec Streamlit
    st.markdown(f"### 📊 Comparaison de {len(formulations)} formulations")
    
    # Sélection colonnes à afficher
    columns = ["Formulation", "Ciment", "Eau", "Resistance", "Diffusion_Cl", "Carbonatation", "Ratio_E_L"]
    available_cols = [col for col in columns if col in df.columns]
    
    # Tableau stylisé
    st.dataframe(
        df[available_cols],
        column_config={
            "Formulation": st.column_config.TextColumn("Nom", width="medium"),
            "Ciment": st.column_config.NumberColumn("Ciment (kg/m³)", format="%d"),
            "Eau": st.column_config.NumberColumn("Eau (L/m³)", format="%d"),
            "Resistance": st.column_config.NumberColumn("Résistance (MPa)", format="%.1f"),
            "Diffusion_Cl": st.column_config.NumberColumn("Diffusion Cl⁻", format="%.2f"),
            "Carbonatation": st.column_config.NumberColumn("Carbonatation (mm)", format="%.1f"),
            "Ratio_E_L": st.column_config.NumberColumn("Ratio E/L", format="%.2f")
        },
        hide_index=True,
        use_container_width=True
    )
    
    return df


def render_progress_timeline(steps: List[Dict[str, Any]], current_step: int) -> None:
    """
    Affiche une timeline de progression.
    
    Args:
        steps: Liste d'étapes {title, description, icon}
        current_step: Étape actuelle (0-indexed)
    """
    st.markdown("### 📋 Progression")
    
    timeline_html = '<div style="display: flex; flex-direction: column; gap: 20px; margin: 2rem 0;">'
    
    for i, step in enumerate(steps):
        is_completed = i < current_step
        is_current = i == current_step
        
        # Couleur selon état
        if is_completed:
            bg_color = "#E8F5E9"
            border_color = "#388E3C"
            icon_color = "#2E7D32"
            checkmark = "✅"
        elif is_current:
            bg_color = "#FFF3E0"
            border_color = "#FF6F00"
            icon_color = "#E65100"
            checkmark = "🔄"
        else:
            bg_color = "#F5F5F5"
            border_color = "#9E9E9E"
            icon_color = "#757575"
            checkmark = "⏳"
        
        timeline_html += f"""
        <div style="
            background: {bg_color};
            border: 2px solid {border_color};
            border-left: 6px solid {border_color};
            border-radius: 10px;
            padding: 1.25rem;
            display: flex;
            align-items: center;
            gap: 15px;
        ">
            <div style="
                background: {icon_color};
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
            ">
                {checkmark}
            </div>
            <div style="flex: 1;">
                <div style="font-weight: 700; font-size: 1.1rem; color: #333;">
                    Étape {i+1}: {step['title']}
                </div>
                <div style="color: #666; margin-top: 5px;">
                    {step.get('description', '')}
                </div>
            </div>
            <div style="font-size: 0.9rem; color: {icon_color}; font-weight: 600;">
                {is_completed and 'Terminé' or is_current and 'En cours' or 'À venir'}
            </div>
        </div>
        """
    
    timeline_html += '</div>'
    st.markdown(timeline_html, unsafe_allow_html=True)


def create_download_buttons(
    df: pd.DataFrame,
    filename: str = "formulation"
) -> None:
    """
    Crée des boutons de téléchargement pour exporter les données.
    
    Args:
        df: DataFrame à exporter
        filename: Nom du fichier (sans extension)
    """
    st.markdown("### 📥 Exporter les résultats")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name=f"{filename}.csv",
                mime="text/csv",
                key="download_csv"
            )
    
    with col2:
        if st.button("📊 Excel", use_container_width=True):
            # Note: nécessite openpyxl ou xlsxwriter
            try:
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Formulations')
                st.download_button(
                    label="Télécharger Excel",
                    data=buffer.getvalue(),
                    file_name=f"{filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )
            except ImportError:
                st.error("⚠️ Installez openpyxl : `pip install openpyxl`")
    
    with col3:
        if st.button("📝 JSON", use_container_width=True):
            json_str = df.to_json(orient="records", indent=2)
            st.download_button(
                label="Télécharger JSON",
                data=json_str,
                file_name=f"{filename}.json",
                mime="application/json",
                key="download_json"
            )
    
    with col4:
        if st.button("📋 Copier", use_container_width=True):
            st.info("Utilisez Ctrl+C / Cmd+C pour copier le tableau")


__all__ = [
    "render_formulation_table",
    "render_comparison_table",
    "render_progress_timeline",
    "create_download_buttons"
]