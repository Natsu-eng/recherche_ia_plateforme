"""
═══════════════════════════════════════════════════════════════════════════════
DATABASE MANAGER - VERSION TRANSACTION EXPLICITE
Version: 2.1.2 - FIX Transaction/Commit
Correctif: Gestion explicite des transactions pour garantir le COMMIT
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
import traceback
import uuid
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestionnaire PostgreSQL ultra-robuste avec retry et logs détaillés."""
    
    def __init__(self, db_url: str, min_connections: int = 2, max_connections: int = 10):
        self._pool = None
        self._db_url = db_url
        self._min_conn = min_connections
        self._max_conn = max_connections
        self._is_connected = False
        self._connection_error = None
        
        logger.info("=" * 80)
        logger.info("[DB INIT] Demarrage DatabaseManager v2.1.2 (Transaction Fix)")
        logger.info(f"[DB INIT] URL: {self._mask_password(db_url)}")
        logger.info(f"[DB INIT] Pool: {min_connections}-{max_connections} connexions")
        
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                db_url
            )
            logger.info("[DB INIT] [OK] Pool cree avec succes")
            
            if self._test_connection():
                self._is_connected = True
                logger.info("[DB INIT] [OK] Connexion etablie et testee")
                self._log_database_info()
            else:
                logger.error("[DB INIT] [ERREUR] Test connexion echoue")
                self._connection_error = "Test connexion echoue"
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            logger.error(f"[DB INIT] [ERREUR] Erreur operationnelle: {error_msg}")
            
            if "password" in error_msg.lower():
                logger.error("[DB INIT] -> Authentification refusee (verifiez user/password)")
            elif "database" in error_msg.lower():
                logger.error("[DB INIT] -> Base de donnees introuvable (verifiez le nom)")
            elif "connection refused" in error_msg.lower():
                logger.error("[DB INIT] -> Serveur injoignable (verifiez host:port)")
            else:
                logger.error(f"[DB INIT] -> Erreur: {error_msg}")
            
            self._pool = None
            self._is_connected = False
            self._connection_error = error_msg
            
        except Exception as e:
            logger.error(f"[DB INIT] [ERREUR] Erreur init pool: {e}")
            logger.debug(traceback.format_exc())
            self._pool = None
            self._is_connected = False
            self._connection_error = str(e)
        
        logger.info("=" * 80)
    
    def _mask_password(self, url: str) -> str:
        """Masque le password dans l'URL pour les logs."""
        try:
            if "://" in url and "@" in url:
                parts = url.split("://")
                scheme = parts[0]
                rest = parts[1]
                
                if "@" in rest:
                    auth, host = rest.split("@", 1)
                    if ":" in auth:
                        user, _ = auth.split(":", 1)
                        return f"{scheme}://{user}:****@{host}"
            return url
        except:
            return "***masque***"
    
    def _log_database_info(self):
        """Log des infos sur la base de données."""
        try:
            conn = self._pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"PostgreSQL: {version[:50]}...")
            
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            logger.info(f"Database: {db_name}")
            
            cursor.execute("SELECT current_user;")
            user = cursor.fetchone()[0]
            logger.info(f"User: {user}")
            
            # Vérifier table predictions
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'predictions'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM predictions;")
                count = cursor.fetchone()[0]
                logger.info(f"Table 'predictions': OK ({count} enregistrements)")
            else:
                logger.warning("Table 'predictions': INTROUVABLE")
            
            cursor.close()
            self._pool.putconn(conn)
            
        except Exception as e:
            logger.warning(f"Impossible de recuperer les infos: {e}")
    
    def _test_connection(self) -> bool:
        """Test connexion avec retry."""
        if not self._pool:
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self._pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                self._pool.putconn(conn)
                
                if result and result[0] == 1:
                    logger.debug(f"[DB TEST] [OK] Connexion OK (tentative {attempt+1})")
                    return True
                    
            except Exception as e:
                logger.warning(f"[DB TEST] [WARN] Tentative {attempt+1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    
        return False
    
    @property
    def is_connected(self) -> bool:
        """Vérifie état connexion actuelle."""
        return self._is_connected and self._pool is not None
    
    @property
    def connection_error(self) -> Optional[str]:
        """Retourne l'erreur de connexion si présente."""
        return self._connection_error
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True,
        max_retries: int = 2
    ) -> Optional[List[Dict]]:
        """
        Exécute requête SQL avec retry automatique.
        
        Args:
            query: Requête SQL
            params: Paramètres
            fetch: True pour SELECT, False pour INSERT/UPDATE/DELETE
            max_retries: Nombre de tentatives
            
        Returns:
            Liste de dicts (si fetch=True) ou liste vide (si fetch=False)
        """
        if not self._pool:
            logger.error("[QUERY] [ERREUR] Pool non disponible")
            return None
        
        last_error = None
        
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self._pool.getconn()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                logger.debug(f"[QUERY] Execution (tentative {attempt+1}): {query[:100]}...")
                
                cursor.execute(query, params or ())
                
                if fetch:
                    results = cursor.fetchall()
                    logger.debug(f"[QUERY] [OK] {len(results)} ligne(s) recuperee(s)")
                    cursor.close()
                    self._pool.putconn(conn)
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    logger.debug("[QUERY] [OK] COMMIT effectue")
                    cursor.close()
                    self._pool.putconn(conn)
                    return []
                    
            except psycopg2.OperationalError as e:
                last_error = e
                logger.warning(f"[QUERY] [WARN] Erreur operationnelle (tentative {attempt+1}): {e}")
                
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    try:
                        self._pool.putconn(conn)
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                    
            except Exception as e:
                logger.error(f"[QUERY] [ERREUR] Erreur SQL: {e}")
                logger.debug(traceback.format_exc())
                
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    try:
                        self._pool.putconn(conn)
                    except:
                        pass
                return None
        
        logger.error(f"[QUERY] [ERREUR] Echec apres {max_retries} tentatives: {last_error}")
        return None
    
    def save_prediction(
        self,
        formulation: Dict[str, float],
        predictions: Dict[str, float],
        formulation_name: str = "Formulation",
        user_id: Optional[str] = None
    ) -> bool:
        """
        Sauvegarde prédiction avec transaction EXPLICITE.
        
        Returns:
            True si sauvegarde réussie, False sinon
        """
        logger.info("=" * 80)
        logger.info(f"[SAVE] DEBUT SAUVEGARDE: '{formulation_name}'")
        logger.info(f"[SAVE] User: {user_id or 'anonyme'}")
        
        # Validation connexion
        if not self._pool or not self._is_connected:
            logger.error("[SAVE] [ERREUR] Base de donnees non connectee")
            if self._connection_error:
                logger.error(f"[SAVE] Erreur: {self._connection_error}")
            return False
        
        conn = None
        cursor = None
        
        try:
            # ═══════════════════════════════════════════════════════════
            # 1. EXTRACTION & VALIDATION DONNÉES
            # ═══════════════════════════════════════════════════════════
            
            logger.debug("[SAVE] 1/6 Extraction donnees...")
            
            ciment = float(formulation.get('Ciment', 0.0))
            eau = float(formulation.get('Eau', 0.0))
            sable = float(formulation.get('SableFin', 0.0))
            gravier = float(formulation.get('GravilonsGros', 0.0))
            laitier = float(formulation.get('Laitier', 0.0))
            cendres = float(formulation.get('CendresVolantes', 0.0))
            adjuvants = float(formulation.get('Superplastifiant', 0.0))
            age = int(formulation.get('Age', 28))
            
            if ciment <= 0 or eau <= 0:
                logger.error(f"[SAVE] [ERREUR] Donnees invalides: ciment={ciment}, eau={eau}")
                return False
            
            logger.debug(f"[SAVE] Composition: C={ciment}, E={eau}, S={sable}, G={gravier}")
            
            resistance = float(predictions.get('Resistance', 0.0))
            diffusion = float(predictions.get('Diffusion_Cl', 0.0))
            carbonatation = float(predictions.get('Carbonatation', 0.0))
            ratio = float(predictions.get('Ratio_E_L', 0.5))
            
            if resistance <= 0:
                logger.error(f"[SAVE] [ERREUR] Resistance invalide: {resistance}")
                return False
            
            logger.debug(f"[SAVE] Predictions: R={resistance:.2f}, D={diffusion:.2f}, C={carbonatation:.2f}")
            
            # ═══════════════════════════════════════════════════════════
            # 2. GÉNÉRATION HASH
            # ═══════════════════════════════════════════════════════════
            
            logger.debug("[SAVE] 2/6 Generation hash unique...")
            
            timestamp_micro = datetime.now().strftime('%Y%m%d%H%M%S%f')
            unique_id = str(uuid.uuid4())[:12]
            
            import random
            random_salt = f"{random.randint(1000, 9999)}"
            
            hash_content = (
                f"{formulation_name}"
                f"{resistance}"
                f"{timestamp_micro}"
                f"{unique_id}"
                f"{random_salt}"
            )
            
            hash_val = hashlib.md5(hash_content.encode()).hexdigest()
            
            logger.debug(f"[SAVE] Hash genere: {hash_val}")
            
            # ═══════════════════════════════════════════════════════════
            # 3. OBTENIR CONNEXION
            # ═══════════════════════════════════════════════════════════
            
            logger.debug("[SAVE] 3/6 Obtention connexion...")
            
            conn = self._pool.getconn()
            logger.debug("[SAVE] Connexion obtenue du pool")
            
            # ═══════════════════════════════════════════════════════════
            # 4. PRÉPARATION REQUÊTE
            # ═══════════════════════════════════════════════════════════
            
            logger.debug("[SAVE] 4/6 Preparation requete SQL...")
            
            query = """
                INSERT INTO predictions (
                    nom_formulation,
                    resistance_predite,
                    hash_formulation,
                    id_utilisateur,
                    horodatage,
                    ratio_eau_liaison,
                    ciment,
                    eau,
                    sable,
                    gravier,
                    adjuvants,
                    temperature_celsius,
                    jours_cure,
                    version_modele,
                    score_confiance,
                    diffusion_cl_predite,
                    carbonatation_predite,
                    laitier,
                    cendres
                ) VALUES (
                    %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id, horodatage;
            """
            
            params = (
                formulation_name[:255],
                resistance,
                hash_val,
                user_id or 'anonyme',
                ratio,
                ciment,
                eau,
                sable,
                gravier,
                adjuvants,
                None,
                age,
                'v1.0.0',
                None,
                diffusion,
                carbonatation,
                laitier,
                cendres
            )
            
            logger.debug(f"[SAVE] Parametres prepares: {len(params)} valeurs")
            
            # ═══════════════════════════════════════════════════════════
            # 5. EXÉCUTION INSERT avec CURSOR EXPLICITE
            # ═══════════════════════════════════════════════════════════
            
            logger.info("[SAVE] 5/6 Execution INSERT...")
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            
            result = cursor.fetchone()
            
            if not result:
                logger.error("[SAVE] [ERREUR] INSERT n'a retourne aucun resultat")
                conn.rollback()
                return False
            
            new_id = result['id']
            timestamp = result['horodatage']
            
            logger.info(f"[SAVE] INSERT retourne: ID={new_id}, Timestamp={timestamp}")
            
            # ═══════════════════════════════════════════════════════════
            # 6. COMMIT EXPLICITE et VÉRIFICATION
            # ═══════════════════════════════════════════════════════════
            
            logger.info("[SAVE] 6/6 COMMIT transaction...")
            
            conn.commit()
            
            logger.info("[SAVE] COMMIT effectue - Transaction validee")
            
            # Vérification immédiate APRÈS commit
            cursor.execute("SELECT id, nom_formulation FROM predictions WHERE id = %s", (new_id,))
            verify_result = cursor.fetchone()
            
            if verify_result:
                logger.info(f"[SAVE] *** SUCCES CONFIRME ***")
                logger.info(f"[SAVE] ID cree: {new_id}")
                logger.info(f"[SAVE] Nom verifie: {verify_result['nom_formulation']}")
                logger.info(f"[SAVE] Hash: {hash_val[:16]}...")
                logger.info("=" * 80)
                
                cursor.close()
                self._pool.putconn(conn)
                
                return True
            else:
                logger.error(f"[SAVE] [ERREUR CRITIQUE] ID {new_id} non trouve apres COMMIT")
                logger.error("=" * 80)
                
                cursor.close()
                self._pool.putconn(conn)
                
                return False
        
        # ═══════════════════════════════════════════════════════════════
        # GESTION ERREURS
        # ═══════════════════════════════════════════════════════════════
        
        except psycopg2.IntegrityError as e:
            logger.error("=" * 80)
            logger.error("[SAVE] *** IntegrityError ***")
            logger.error(f"[SAVE] Message: {e}")
            logger.error(f"[SAVE] PG Code: {e.pgcode}")
            
            if conn:
                try:
                    conn.rollback()
                    logger.info("[SAVE] ROLLBACK effectue")
                except:
                    pass
            
            if 'hash_formulation' in str(e):
                logger.error("[SAVE] -> Hash duplique")
                logger.error(f"[SAVE] -> Hash utilise: {hash_val}")
            
            logger.error("=" * 80)
            
            if cursor:
                cursor.close()
            if conn:
                self._pool.putconn(conn)
            
            return False
        
        except Exception as e:
            logger.error("=" * 80)
            logger.error("[SAVE] *** Exception ***")
            logger.error(f"[SAVE] Type: {type(e).__name__}")
            logger.error(f"[SAVE] Message: {e}")
            logger.debug(traceback.format_exc())
            logger.error("=" * 80)
            
            if conn:
                try:
                    conn.rollback()
                    logger.info("[SAVE] ROLLBACK effectue")
                except:
                    pass
            
            if cursor:
                cursor.close()
            if conn:
                self._pool.putconn(conn)
            
            return False
    
    def get_recent_predictions(self, limit: int = 5) -> List[Dict]:
        """Récupère dernières prédictions (robuste)."""
        logger.debug(f"[GET] Recuperation {limit} predictions recentes...")
        
        if not self._pool or not self._is_connected:
            logger.info("[GET] DB non connectee - donnees demo")
            return self._get_fallback_predictions(limit)
        
        query = """
            SELECT 
                id,
                nom_formulation,
                COALESCE(resistance_predite, 0) as resistance_predite,
                COALESCE(diffusion_cl_predite, 0) as diffusion_cl_predite,
                COALESCE(carbonatation_predite, 0) as carbonatation_predite,
                COALESCE(ratio_eau_liaison, 0.5) as ratio_eau_liaison,
                COALESCE(ciment, 0) as ciment,
                COALESCE(laitier, 0) as laitier,
                COALESCE(cendres, 0) as cendres,
                COALESCE(eau, 0) as eau,
                COALESCE(sable, 0) as sable,
                COALESCE(gravier, 0) as gravier,
                COALESCE(adjuvants, 0) as adjuvants,
                COALESCE(jours_cure, 28) as jours_cure,
                COALESCE(version_modele, 'unknown') as version_modele,
                horodatage as created_at
            FROM predictions
            ORDER BY horodatage DESC NULLS LAST
            LIMIT %s
        """
        
        results = self.execute_query(query, (limit,), fetch=True)
        
        if not results:
            logger.warning("[GET] Aucune prediction trouvee")
            return []
        
        formatted_results = []
        for row in results:
            formatted_results.append({
                'formulation_name': row.get('nom_formulation', 'Inconnu'),
                'resistance_predicted': float(row.get('resistance_predite', 0)),
                'diffusion_cl_predicted': float(row.get('diffusion_cl_predite', 0)),
                'carbonatation_predicted': float(row.get('carbonatation_predite', 0)),
                'ratio_e_l': float(row.get('ratio_eau_liaison', 0.5)),
                'ciment': float(row.get('ciment', 0)),
                'laitier': float(row.get('laitier', 0)),
                'cendres': float(row.get('cendres', 0)),
                'eau': float(row.get('eau', 0)),
                'sable': float(row.get('sable', 0)),
                'gravier': float(row.get('gravier', 0)),
                'adjuvants': float(row.get('adjuvants', 0)),
                'age': int(row.get('jours_cure', 28)),
                'created_at': row.get('created_at', datetime.now())
            })
        
        logger.debug(f"[GET] [OK] {len(formatted_results)} predictions formatees")
        return formatted_results
    
    def get_live_stats(self) -> Dict:
        """Statistiques en temps réel (robuste)."""
        logger.debug("[STATS] Recuperation stats...")
        
        stats = {
            'total_predictions': 0,
            'formulations_analyzed': 0,
            'active_users': 0,
            'avg_resistance': 0.0,
            'avg_diffusion_cl': 0.0,
            'avg_carbonatation': 0.0,
            'db_connected': self._is_connected,
            'last_update': datetime.now()
        }
        
        if not self._pool or not self._is_connected:
            return stats
        
        try:
            query = """
                WITH stats_data AS (
                    SELECT 
                        COUNT(*) as total_preds,
                        COUNT(DISTINCT hash_formulation) as unique_forms,
                        COUNT(DISTINCT CASE 
                            WHEN horodatage > NOW() - INTERVAL '24 hours' 
                            THEN id_utilisateur 
                        END) as active_users_24h,
                        AVG(NULLIF(resistance_predite, 0)) as avg_resistance,
                        AVG(NULLIF(diffusion_cl_predite, 0)) as avg_diffusion,
                        AVG(NULLIF(carbonatation_predite, 0)) as avg_carbonatation,
                        STDDEV(NULLIF(resistance_predite, 0)) as std_resistance
                    FROM predictions
                    WHERE horodatage > NOW() - INTERVAL '365 days'
                )
                SELECT * FROM stats_data
            """
            
            result = self.execute_query(query, fetch=True)
            
            if result and len(result) > 0:
                row = result[0]
                stats.update({
                    'total_predictions': int(row['total_preds'] or 0),
                    'formulations_analyzed': int(row['unique_forms'] or 0),
                    'active_users': int(row['active_users_24h'] or 1),
                    'avg_resistance': float(row['avg_resistance'] or 35.0),
                    'avg_diffusion_cl': float(row['avg_diffusion'] or 8.0),
                    'avg_carbonatation': float(row['avg_carbonatation'] or 15.0),
                    'std_resistance': float(row['std_resistance'] or 10.0),
                    'db_connected': True
                })
                
                logger.debug(f"[STATS] [OK] Total predictions: {stats['total_predictions']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"[STATS] [ERREUR] Erreur: {e}")
            return {**stats, 'db_connected': False, 'error': str(e)}
    
    def _get_fallback_predictions(self, limit: int) -> List[Dict]:
        """Données démo (mode hors ligne)."""
        logger.info("[FALLBACK] Utilisation donnees demo")
        
        demo_data = [
            {
                'formulation_name': '[DEMO] C25/30 Standard',
                'resistance_predicted': 25.8,
                'diffusion_cl_predicted': 7.76,
                'carbonatation_predicted': 16.7,
                'ratio_e_l': 0.643,
                'ciment': 280.0,
                'laitier': 0.0,
                'cendres': 0.0,
                'eau': 180.0,
                'sable': 750.0,
                'gravier': 1100.0,
                'adjuvants': 0.0,
                'age': 28,
                'created_at': datetime.now()
            },
            {
                'formulation_name': '[DEMO] C35/45 HP',
                'resistance_predicted': 55.4,
                'diffusion_cl_predicted': 2.12,
                'carbonatation_predicted': 10.5,
                'ratio_e_l': 0.395,
                'ciment': 430.0,
                'laitier': 0.0,
                'cendres': 0.0,
                'eau': 170.0,
                'sable': 700.0,
                'gravier': 1050.0,
                'adjuvants': 5.0,
                'age': 28,
                'created_at': datetime.now()
            }
        ]
        
        return demo_data[:limit]
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Retourne un rapport de diagnostic complet."""
        diag = {
            'connected': self.is_connected,
            'pool_available': self._pool is not None,
            'connection_error': self._connection_error,
            'pool_config': {
                'min': self._min_conn,
                'max': self._max_conn
            }
        }
        
        if self.is_connected:
            try:
                conn = self._pool.getconn()
                cursor = conn.cursor()
                
                cursor.execute("SELECT version();")
                diag['postgresql_version'] = cursor.fetchone()[0][:100]
                
                cursor.execute("SELECT current_database();")
                diag['database'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT current_user;")
                diag['user'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM predictions;")
                diag['predictions_count'] = cursor.fetchone()[0]
                
                cursor.close()
                self._pool.putconn(conn)
                
            except Exception as e:
                diag['diagnostics_error'] = str(e)
        
        return diag
    
    def close(self):
        """Ferme pool connexions proprement."""
        if self._pool:
            try:
                self._pool.closeall()
                logger.info("[DB] Pool ferme")
            except Exception as e:
                logger.error(f"[DB] Erreur fermeture pool: {e}")


__all__ = ['DatabaseManager']