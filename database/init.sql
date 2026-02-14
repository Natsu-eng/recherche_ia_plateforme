-- ═══════════════════════════════════════════════════════════════════════════════
-- SCRIPT INITIALISATION POSTGRESQL
-- Fichier: database/init.sql
-- Exécuté automatiquement au premier démarrage du conteneur PostgreSQL
-- ═══════════════════════════════════════════════════════════════════════════════

-- Activer extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ═══════════════════════════════════════════════════════════════════════════════
-- PERMISSIONS AUTOMATIQUES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Donner toutes les permissions à app_beton sur les tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_beton;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_beton;

-- Permissions par défaut pour les futurs objets
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO app_beton;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_beton;

-- ═══════════════════════════════════════════════════════════════════════════════
-- CRÉATION TABLE predictions (SI NÉCESSAIRE)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    nom_formulation VARCHAR(255) NOT NULL,
    resistance_predite NUMERIC(10,2) NOT NULL,
    hash_formulation VARCHAR(64) NOT NULL UNIQUE,
    id_utilisateur VARCHAR(255) DEFAULT 'anonyme',
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ratio_eau_liaison NUMERIC(5,3),
    ciment NUMERIC(10,2) NOT NULL,
    eau NUMERIC(10,2) NOT NULL,
    sable NUMERIC(10,2) NOT NULL,
    gravier NUMERIC(10,2) NOT NULL,
    adjuvants NUMERIC(10,2) DEFAULT 0,
    temperature_celsius NUMERIC(5,2),
    jours_cure INTEGER DEFAULT 28,
    version_modele VARCHAR(50),
    score_confiance NUMERIC(5,4),
    diffusion_cl_predite NUMERIC(8,3),
    carbonatation_predite NUMERIC(8,2),
    laitier NUMERIC(10,2),
    cendres NUMERIC(10,2)
);

-- Index pour performances
CREATE INDEX IF NOT EXISTS idx_predictions_horodatage ON predictions(horodatage DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_hash ON predictions(hash_formulation);
CREATE INDEX IF NOT EXISTS idx_predictions_user_date ON predictions(id_utilisateur, horodatage DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLES ADDITIONNELLES (OPTIONNEL)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS formulations_favorites (
    id SERIAL PRIMARY KEY,
    id_prediction INTEGER REFERENCES predictions(id) ON DELETE SET NULL,
    nom_favori VARCHAR(255),
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions_utilisateurs (
    id SERIAL PRIMARY KEY,
    id_utilisateur VARCHAR(255),
    timestamp_debut TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_fin TIMESTAMP,
    nb_predictions INTEGER DEFAULT 0
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- PERMISSIONS FINALES
-- ═══════════════════════════════════════════════════════════════════════════════

GRANT ALL PRIVILEGES ON TABLE predictions TO app_beton;
GRANT ALL PRIVILEGES ON TABLE formulations_favorites TO app_beton;
GRANT ALL PRIVILEGES ON TABLE sessions_utilisateurs TO app_beton;

GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_beton;

-- Log
\echo 'Initialisation PostgreSQL terminée avec succès'
\echo 'Permissions accordées à app_beton'