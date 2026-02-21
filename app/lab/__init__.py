"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/lab - Laboratoire Niveau Recherche
Version: 1.0.0 - Expert Level
═══════════════════════════════════════════════════════════════════════════════

Moteurs d'analyse avancée:
- Monte Carlo vectorisé + CO₂
- Surfaces 3D + CO₂
- DOE (à venir)
- Optimisation multi-objectifs (à venir)
"""

from .monte_carlo_engine import (
    MonteCarloEngine,
    MonteCarloResult,
    MonteCarloStats,
    quick_monte_carlo,
    export_monte_carlo_csv
)

from .surface_engine import (
    SurfaceEngine,
    SurfaceData,
    MultiSurfaceData,
    plot_surface_with_co2
)

__version__ = '1.0.0'

__all__ = [
    # Monte Carlo
    'MonteCarloEngine',
    'MonteCarloResult',
    'MonteCarloStats',
    'quick_monte_carlo',
    'export_monte_carlo_csv',
    
    # Surfaces 3D
    'SurfaceEngine',
    'SurfaceData',
    'MultiSurfaceData',
    'plot_surface_with_co2'
]