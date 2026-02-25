"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/core/session_manager.py
Auteur: Stage R&D - IMT Nord Europe
Fonction: Initialisation & Gestion du Session State Streamlit
Version: 1.0.0 - Refactorisé & Production Ready
═══════════════════════════════════════════════════════════════════════════════
Responsabilités :
  - Chargement unique du modèle ML (XGBoost)
  - Connexion à la base de données PostgreSQL
  - Chargement du correcteur Métakaolin
  - Initialisation des valeurs par défaut du session_state
  - Chargement des variables d'environnement (.env)

Usage : Appeler initialize_session() au début de CHAQUE page Streamlit.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import streamlit as st

# ── Imports applicatifs au niveau module ───────────────────────────────────────
# Hissés ici pour un exit rapide (ImportError visible immédiatement)
# et pour éviter le couplage caché dans le corps des fonctions.
from app.models.loader import load_production_assets
from app.core.mk_corrector import get_mk_corrector
from config.settings import POSTGRES_SETTINGS
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# VALEURS PAR DÉFAUT DU SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

# Dictionnaire centralisé des clés et de leurs valeurs par défaut.
# Toute nouvelle clé de session doit être déclarée ici.
_SESSION_DEFAULTS: Dict[str, Any] = {
    # ── ML ──────────────────────────────────────────────────────────────────
    "model":            None,   # Modèle ML chargé (XGBoost ou autre)
    "features":         None,   # Liste ordonnée des features du modèle
    "metadata":         None,   # Métadonnées du modèle (version, date, etc.)
    "mk_corrector":     None,   # Correcteur Métakaolin (optionnel)

    # ── Base de données ──────────────────────────────────────────────────────
    "db_manager":       None,   # Instance DatabaseManager (None si non connecté)

    # ── UI / Thème ───────────────────────────────────────────────────────────
    "app_theme":        "Clair",

    # ── Données de session utilisateur ──────────────────────────────────────
    "last_prediction":          None,
    "show_results":             False,
    "comparison_formulations":  [],
    "favorites":                [],
    "prediction_count":         0,
    "total_saves":              0,

    # ── Flag interne : empêche load_dotenv() de tourner à chaque rerun ───────
    "env_loaded":       False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS D'INITIALISATION INDIVIDUELLES
# ═══════════════════════════════════════════════════════════════════════════════

def _load_env_once() -> None:
    """
    Charge les variables d'environnement depuis .env une seule fois par session.

    Streamlit réexécute le script à chaque interaction utilisateur.
    Ce flag en session garantit que load_dotenv() n'est appelé qu'une fois,
    évitant des lectures disque répétées et inutiles.
    """
    if st.session_state.get("env_loaded"):
        return

    load_dotenv(override=False)  # Ne pas écraser les variables système existantes
    st.session_state["env_loaded"] = True
    logger.debug("Variables d'environnement chargées depuis .env")


def _init_session_defaults() -> None:
    """
    Initialise toutes les clés de session avec leurs valeurs par défaut.

    N'écrase jamais une clé déjà présente dans session_state.
    """
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            # Copie superficielle pour les listes (évite le partage de référence)
            st.session_state[key] = default.copy() if isinstance(default, list) else default


def _init_model() -> None:
    """
    Charge le modèle ML et ses métadonnées dans la session.

    Arrête l'application (st.stop()) si le chargement échoue,
    car le modèle est requis pour toutes les fonctionnalités.

    Clés session renseignées :
        - "model"    : objet modèle ML
        - "features" : liste des features
        - "metadata" : dictionnaire de métadonnées
    """
    if st.session_state.get("model") is not None:
        return  # Déjà chargé

    with st.spinner("🔄 Chargement du modèle ML…"):
        try:
            model, features, metadata = load_production_assets()
            st.session_state["model"]    = model
            st.session_state["features"] = features
            st.session_state["metadata"] = metadata
            logger.info(
                "Modèle ML chargé — version=%s | features=%d",
                metadata.get("version", "?"),
                len(features) if features else 0,
            )
        except Exception as exc:
            logger.error("Chargement modèle ML échoué : %s", exc, exc_info=True)
            st.error(
                f"❌ Impossible de charger le modèle ML : {exc}\n\n"
                "Vérifiez que les fichiers de modèle sont présents dans `models/`."
            )
            st.stop()


def _init_database() -> None:
    """
    Établit la connexion PostgreSQL et stocke le manager dans la session.

    En cas d'échec, la connexion est mise à None (mode dégradé).
    Les fonctionnalités de sauvegarde seront désactivées mais l'app continue.

    Clés session renseignées :
        - "db_manager" : instance DatabaseManager ou None
    """
    if "db_manager" in st.session_state and st.session_state["db_manager"] is not None:
        return  # Déjà connecté

    try:
        from database.manager import DatabaseManager  # Import local : dépendance optionnelle

        db_url = POSTGRES_SETTINGS.get("database_url", "")
        if not db_url:
            logger.warning("POSTGRES_SETTINGS['database_url'] vide — DB ignorée")
            st.session_state["db_manager"] = None
            return

        db_manager = DatabaseManager(
            db_url=db_url,
            min_connections=2,
            max_connections=10,
        )
        st.session_state["db_manager"] = db_manager
        logger.info("Connexion PostgreSQL établie : %s", db_url.split("@")[-1])  # masque les credentials

    except ImportError:
        logger.warning("Module 'database.manager' absent — fonctionnement sans DB")
        st.session_state["db_manager"] = None

    except Exception as exc:
        logger.warning("Connexion PostgreSQL échouée : %s — mode dégradé", exc)
        st.session_state["db_manager"] = None


def _init_mk_corrector() -> None:
    """
    Charge le correcteur Métakaolin dans la session (optionnel).

    En cas d'absence du fichier ou d'erreur, mk_corrector est mis à None.
    Les prédictions avec MK utiliseront alors le modèle de base.

    Clés session renseignées :
        - "mk_corrector" : instance du correcteur ou None
    """
    if st.session_state.get("mk_corrector") is not None:
        return  # Déjà chargé

    try:
        corrector = get_mk_corrector("models/mk_corrector.pkl")
        st.session_state["mk_corrector"] = corrector
        logger.info("Correcteur Métakaolin chargé")

    except FileNotFoundError:
        logger.info(
            "Fichier 'models/mk_corrector.pkl' absent — "
            "correction MK désactivée (mode nominal)"
        )
        st.session_state["mk_corrector"] = None

    except Exception as exc:
        logger.warning("Correcteur MK non chargé : %s", exc)
        st.session_state["mk_corrector"] = None


def _check_model_availability() -> None:
    """
    Affiche un avertissement non-bloquant si le modèle est toujours None.

    Appelé en fin d'initialisation comme garde-fou.
    """
    if st.session_state.get("model") is None:
        st.warning(
            "⚠️ Modèle ML non disponible — "
            "certaines fonctionnalités de prédiction seront limitées."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_session() -> None:
    """
    Initialise tous les composants critiques de la session Streamlit.

    Doit être appelé au début de **chaque page** de l'application.
    Grâce aux guards (`if ... is not None: return`), chaque composant
    n'est initialisé qu'une seule fois par session utilisateur.

    Pipeline d'initialisation :
      1. Chargement du .env (une fois par session)
      2. Valeurs par défaut du session_state
      3. Modèle ML (bloquant si échec)
      4. Base de données (mode dégradé si échec)
      5. Correcteur Métakaolin (optionnel)
      6. Vérification de disponibilité du modèle

    Example:
        ```python
        # En tête de chaque page Streamlit
        from app.core.session_manager import initialize_session
        initialize_session()
        ```
    """
    # 1. Variables d'environnement (idempotent)
    _load_env_once()

    # 2. Valeurs par défaut (sans écrasement)
    _init_session_defaults()

    # 3. Modèle ML (bloquant)
    _init_model()

    # 4. Base de données (mode dégradé si échec)
    _init_database()

    # 5. Correcteur MK (optionnel)
    _init_mk_corrector()

    # 6. Vérification finale
    _check_model_availability()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES DE SESSION
# ═══════════════════════════════════════════════════════════════════════════════

def get_model() -> Optional[Any]:
    """
    Retourne le modèle ML depuis la session.

    Returns:
        Objet modèle ML, ou None si non chargé.
    """
    return st.session_state.get("model")


def get_features() -> Optional[list]:
    """
    Retourne la liste des features depuis la session.

    Returns:
        Liste ordonnée des features, ou None si non chargée.
    """
    return st.session_state.get("features")


def get_db_manager() -> Optional[Any]:
    """
    Retourne le gestionnaire de base de données depuis la session.

    Returns:
        Instance DatabaseManager connectée, ou None en mode dégradé.
    """
    return st.session_state.get("db_manager")


def is_db_connected() -> bool:
    """
    Indique si la base de données est disponible.

    Returns:
        True si le db_manager est initialisé et connecté.
    """
    db = get_db_manager()
    return db is not None and getattr(db, "is_connected", False)


def reset_session_data() -> None:
    """
    Réinitialise les données utilisateur de la session (pas les ressources ML).

    Remet à zéro : last_prediction, show_results, comparison_formulations,
    favorites, prediction_count, total_saves.

    Utile pour un bouton "Nouvelle session" ou lors des tests.
    """
    _USER_KEYS = [
        "last_prediction",
        "show_results",
        "comparison_formulations",
        "favorites",
        "prediction_count",
        "total_saves",
    ]
    for key in _USER_KEYS:
        default = _SESSION_DEFAULTS.get(key)
        st.session_state[key] = default.copy() if isinstance(default, list) else default

    logger.info("Données utilisateur de session réinitialisées")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "initialize_session",
    "get_model",
    "get_features",
    "get_db_manager",
    "is_db_connected",
    "reset_session_data",
]