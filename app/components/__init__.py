"""
═══════════════════════════════════════════════════════════════════════════════
PACKAGE: app/components
Description: Composants UI réutilisables pour Streamlit
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

from .sidebar import render_sidebar
from .cards import metric_card, formulation_card, alert_banner
from .forms import render_formulation_input, render_target_selector
from .charts import (
    plot_composition_pie,
    plot_parallel_coordinates,
    plot_sensitivity,
    plot_performance_radar
)

__all__ = [
    # Sidebar
    'render_sidebar',
    
    # Cards
    'metric_card',
    'formulation_card',
    'alert_banner',
    
    # Forms
    'render_formulation_input',
    'render_target_selector',
    
    # Charts
    'plot_composition_pie',
    'plot_parallel_coordinates',
    'plot_sensitivity',
    'plot_performance_radar'
]