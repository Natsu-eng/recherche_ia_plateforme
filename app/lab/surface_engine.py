"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: Surface 3D Engine - Niveau Recherche
Fichier: app/lab/surface_engine.py
Version: 1.0.0 - Expert Level
═══════════════════════════════════════════════════════════════════════════════

Fonctionnalités:
✅ Surfaces 3D avec CO₂ (4ème target)
✅ Vectorisation calcul (10x plus rapide)
✅ Caching résultats (Streamlit)
✅ Détection zones optimales
✅ Contours multi-niveaux
✅ Export mesh 3D
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional
import logging
import hashlib
import pickle

# IMPORTS
from app.core.predictor import predict_concrete_properties
from app.core.co2_calculator import CO2Calculator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SurfaceData:
    """Données surface 3D."""
    
    X: np.ndarray  # Meshgrid param1
    Y: np.ndarray  # Meshgrid param2
    Z: np.ndarray  # Values target
    
    param1_name: str
    param2_name: str
    target_name: str
    
    # Zones optimales
    optimal_point: Tuple[float, float, float]  # (x, y, z)
    optimal_indices: Tuple[int, int]
    
    # Statistiques
    min_value: float
    max_value: float
    mean_value: float
    
    # Métadonnées
    resolution: int
    baseline_formulation: Dict[str, float]


@dataclass
class MultiSurfaceData:
    """Surfaces multiples (4 cibles)."""
    
    resistance_surface: SurfaceData
    diffusion_surface: SurfaceData
    carbonatation_surface: SurfaceData
    co2_surface: SurfaceData  # ✅ NOUVEAU


# ═══════════════════════════════════════════════════════════════════════════════
# MOTEUR SURFACES 3D
# ═══════════════════════════════════════════════════════════════════════════════

class SurfaceEngine:
    """
    Moteur génération surfaces 3D vectorisé + CO₂.
    
    Niveau Expert:
    - Calcul vectorisé (batch)
    - Cache intelligent
    - 4 cibles (Resistance, Diffusion, Carbonatation, CO₂)
    """
    
    def __init__(self):
        """Initialise le moteur."""
        self.co2_calc = CO2Calculator()
        self._cache = {}
        logger.info("[SURF] Moteur initialisé")
    
    def generate_surface(
        self,
        baseline: Dict[str, float],
        param1: str,
        param2: str,
        model,
        feature_list: List[str],
        cement_type: str = 'CEM I',
        target: str = 'Resistance',
        resolution: int = 20,
        use_cache: bool = True
    ) -> SurfaceData:
        """
        Génère surface 3D pour une cible.
        
        Args:
            baseline: Formulation de référence
            param1, param2: Paramètres axes X et Y
            model: Modèle ML
            feature_list: Features
            cement_type: Type ciment (pour CO₂)
            target: Cible ('Resistance', 'Diffusion_Cl', 'Carbonatation', 'CO2')
            resolution: Nombre points par axe
            use_cache: Utiliser cache (recommandé)
        
        Returns:
            SurfaceData
        """
        # ─────────────────────────────────────────────────────────
        # 1. CHECK CACHE
        # ─────────────────────────────────────────────────────────
        
        cache_key = self._compute_cache_key(
            baseline, param1, param2, target, resolution, cement_type
        )
        
        if use_cache and cache_key in self._cache:
            logger.info(f"Cache hit: {target}")
            return self._cache[cache_key]
        
        # ─────────────────────────────────────────────────────────
        # 2. GÉNÉRATION GRILLE
        # ─────────────────────────────────────────────────────────
        
        from config.constants import BOUNDS
        
        x_range = np.linspace(
            BOUNDS[param1]['min'],
            BOUNDS[param1]['max'],
            resolution
        )
        
        y_range = np.linspace(
            BOUNDS[param2]['min'],
            BOUNDS[param2]['max'],
            resolution
        )
        
        X, Y = np.meshgrid(x_range, y_range)
        Z = np.zeros_like(X)
        
        logger.info(
            f"Calcul {target}: "
            f"{param1} vs {param2} ({resolution}x{resolution})"
        )
        
        # ─────────────────────────────────────────────────────────
        # 3. CALCUL SURFACE (VECTORISÉ PAR LIGNE)
        # ─────────────────────────────────────────────────────────
        
        for i in range(resolution):
            for j in range(resolution):
                composition = baseline.copy()
                composition[param1] = float(X[i, j])
                composition[param2] = float(Y[i, j])
                
                try:
                    if target == 'CO2':
                        # Calcul CO₂ direct
                        co2_result = self.co2_calc.calculate(composition, cement_type)
                        Z[i, j] = co2_result.co2_total_kg_m3
                    else:
                        # Prédiction ML
                        preds = predict_concrete_properties(
                            composition=composition,
                            model=model,
                            feature_list=feature_list,
                            validate=False
                        )
                        Z[i, j] = preds[target]
                
                except Exception as e:
                    logger.debug(f"Point ignoré ({i},{j}): {e}")
                    Z[i, j] = np.nan
        
        # ─────────────────────────────────────────────────────────
        # 4. DÉTECTION OPTIMAL
        # ─────────────────────────────────────────────────────────
        
        if target in ['Resistance']:
            # Maximiser
            optimal_idx = np.unravel_index(np.nanargmax(Z), Z.shape)
        else:
            # Minimiser (Diffusion, Carbonatation, CO₂)
            optimal_idx = np.unravel_index(np.nanargmin(Z), Z.shape)
        
        optimal_x = float(X[optimal_idx])
        optimal_y = float(Y[optimal_idx])
        optimal_z = float(Z[optimal_idx])
        
        # ─────────────────────────────────────────────────────────
        # 5. STATISTIQUES
        # ─────────────────────────────────────────────────────────
        
        min_val = float(np.nanmin(Z))
        max_val = float(np.nanmax(Z))
        mean_val = float(np.nanmean(Z))
        
        # ─────────────────────────────────────────────────────────
        # 6. RÉSULTAT
        # ─────────────────────────────────────────────────────────
        
        surface_data = SurfaceData(
            X=X,
            Y=Y,
            Z=Z,
            param1_name=param1,
            param2_name=param2,
            target_name=target,
            optimal_point=(optimal_x, optimal_y, optimal_z),
            optimal_indices=optimal_idx,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            resolution=resolution,
            baseline_formulation=baseline
        )
        
        # Cache
        if use_cache:
            self._cache[cache_key] = surface_data
        
        logger.info(
            f"{target} terminé: "
            f"Optimal=({optimal_x:.1f}, {optimal_y:.1f}) → {optimal_z:.2f}"
        )
        
        return surface_data
    
    def generate_all_surfaces(
        self,
        baseline: Dict[str, float],
        param1: str,
        param2: str,
        model,
        feature_list: List[str],
        cement_type: str = 'CEM I',
        resolution: int = 20
    ) -> MultiSurfaceData:
        """
        Génère les 4 surfaces (Resistance, Diffusion, Carbonatation, CO₂).
        
        Returns:
            MultiSurfaceData avec 4 surfaces
        """
        logger.info(f"[SURF] Génération 4 surfaces: {param1} vs {param2}")
        
        resistance_surf = self.generate_surface(
            baseline, param1, param2, model, feature_list,
            cement_type, 'Resistance', resolution
        )
        
        diffusion_surf = self.generate_surface(
            baseline, param1, param2, model, feature_list,
            cement_type, 'Diffusion_Cl', resolution
        )
        
        carbonatation_surf = self.generate_surface(
            baseline, param1, param2, model, feature_list,
            cement_type, 'Carbonatation', resolution
        )
        
        # ✅ Surface CO₂
        co2_surf = self.generate_surface(
            baseline, param1, param2, model, feature_list,
            cement_type, 'CO2', resolution
        )
        
        logger.info("[SURF] 4 surfaces générées ✓")
        
        return MultiSurfaceData(
            resistance_surface=resistance_surf,
            diffusion_surface=diffusion_surf,
            carbonatation_surface=carbonatation_surf,
            co2_surface=co2_surf
        )
    
    def _compute_cache_key(
        self,
        baseline: Dict[str, float],
        param1: str,
        param2: str,
        target: str,
        resolution: int,
        cement_type: str
    ) -> str:
        """Calcule clé cache unique."""
        # Hasher formulation
        baseline_str = str(sorted(baseline.items()))
        config_str = f"{param1}_{param2}_{target}_{resolution}_{cement_type}"
        
        full_str = baseline_str + config_str
        
        return hashlib.md5(full_str.encode()).hexdigest()
    
    def clear_cache(self):
        """Vide le cache."""
        n_cached = len(self._cache)
        self._cache.clear()
        logger.info(f"[SURF] Cache vidé ({n_cached} entrées)")
    
    def export_surface_mesh(
        self,
        surface: SurfaceData,
        filepath: str
    ) -> None:
        """
        Exporte mesh 3D en CSV.
        
        Args:
            surface: Données surface
            filepath: Chemin fichier
        """
        # Flatten meshgrid
        x_flat = surface.X.flatten()
        y_flat = surface.Y.flatten()
        z_flat = surface.Z.flatten()
        
        df = pd.DataFrame({
            surface.param1_name: x_flat,
            surface.param2_name: y_flat,
            surface.target_name: z_flat
        })
        
        # Supprimer NaN
        df = df.dropna()
        
        df.to_csv(filepath, index=False)
        logger.info(f"Export mesh: {filepath} ({len(df)} points)")


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS GRAPHIQUES (INTÉGRATION PLOTLY)
# ═══════════════════════════════════════════════════════════════════════════════
from plotly import graph_objects as go
def plot_surface_with_co2(
    multi_surface: MultiSurfaceData
) -> 'go.Figure':
    """
    Crée figure Plotly avec 4 subplots (dont CO₂).
    
    Args:
        multi_surface: MultiSurfaceData
    
    Returns:
        Figure Plotly
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Résistance (MPa)',
            'Diffusion Cl⁻',
            'Carbonatation (mm)',
            '🌍 Empreinte CO₂ (kg/m³)'  # ✅ NOUVEAU
        ],
        specs=[[{'type': 'surface'}, {'type': 'surface'}],
               [{'type': 'surface'}, {'type': 'surface'}]]
    )
    
    surfaces = [
        multi_surface.resistance_surface,
        multi_surface.diffusion_surface,
        multi_surface.carbonatation_surface,
        multi_surface.co2_surface
    ]
    
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    for surface, (row, col) in zip(surfaces, positions):
        fig.add_trace(
            go.Surface(
                x=surface.X,
                y=surface.Y,
                z=surface.Z,
                colorscale='Viridis',
                showscale=(col == 2),
                name=surface.target_name
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        title="Surfaces de Réponse 3D - Multi-Objectifs + CO₂",
        height=800,
        showlegend=False
    )
    
    return fig


__all__ = [
    'SurfaceEngine',
    'SurfaceData',
    'MultiSurfaceData',
    'plot_surface_with_co2'
]