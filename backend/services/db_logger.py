import sqlite3
import threading
from typing import Any, Dict, List, Optional

from ..core.utils import get_iso_timestamp
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class DBLogger:
    def __init__(self, db_path: str = "network_guardian.db"):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._create_tables()

    def _create_tables(self) -> None:
        with self.lock:
            cursor = self.connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE NOT NULL,
                    entropy REAL,
                    risk_score TEXT,
                    category TEXT,
                    summary TEXT,
                    is_anomaly INTEGER,
                    anomaly_score REAL,
                    analysis_source TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_id INTEGER NOT NULL,
                    reason TEXT,
                    filter_id INTEGER,
                    rule TEXT,
                    client TEXT,
                    FOREIGN KEY (domain_id) REFERENCES domains(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_id INTEGER NOT NULL,
                    length INTEGER,
                    digit_ratio REAL,
                    vowel_ratio REAL,
                    non_alphanumeric INTEGER,
                    FOREIGN KEY (domain_id) REFERENCES domains(id)
                )
            """)

            self.connection.commit()

    def log_threat(self, analysis_result: Dict[str, Any]) -> Optional[int]:
        with self.lock:
            cursor = self.connection.cursor()

            domain = analysis_result.get("domain", "")
            entropy = analysis_result.get("entropy", 0.0)
            risk_score = analysis_result.get("risk_score", "Unknown")
            category = analysis_result.get("category", "Unknown")
            summary = analysis_result.get("summary", "")
            is_anomaly = 1 if analysis_result.get("is_anomaly", False) else 0
            anomaly_score = analysis_result.get("anomaly_score", 0.0)
            analysis_source = analysis_result.get("analysis_source", "unknown")
            timestamp = analysis_result.get("timestamp", get_iso_timestamp())

            adguard_metadata = analysis_result.get("adguard_metadata", {})
            reason = adguard_metadata.get("reason", "")
            filter_id = adguard_metadata.get("filter_id")
            rule = adguard_metadata.get("rule", "")
            client = adguard_metadata.get("client", "")

            features = analysis_result.get("features", {})
            length = features.get("length", 0)
            digit_ratio = features.get("digit_ratio", 0.0)
            vowel_ratio = features.get("vowel_ratio", 0.0)
            non_alphanumeric = features.get("non_alphanumeric", 0)

            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO domains 
                    (domain, entropy, risk_score, category, summary, is_anomaly, anomaly_score, analysis_source, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (domain, entropy, risk_score, category, summary, is_anomaly, anomaly_score, analysis_source, timestamp),
                )

                if cursor.rowcount == 0:
                    cursor.execute("SELECT id FROM domains WHERE domain = ?", (domain,))
                    domain_id = cursor.fetchone()[0]
                else:
                    domain_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO metadata (domain_id, reason, filter_id, rule, client)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (domain_id, reason, filter_id, rule, client),
                )

                cursor.execute(
                    """
                    INSERT INTO features (domain_id, length, digit_ratio, vowel_ratio, non_alphanumeric)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (domain_id, length, digit_ratio, vowel_ratio, non_alphanumeric),
                )

                self.connection.commit()
                return domain_id

            except Exception as e:
                # Ensure transaction is rolled back before logging
                self.connection.rollback()
                logger.error("Database error", extra={"error": str(e), "domain": domain})
                return None

    def get_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT d.*, m.reason, m.filter_id, m.rule, m.client,
                       f.length, f.digit_ratio, f.vowel_ratio, f.non_alphanumeric
                FROM domains d
                LEFT JOIN metadata m ON d.id = m.domain_id
                LEFT JOIN features f ON d.id = f.domain_id
                WHERE d.domain = ?
                """,
                (domain,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_recent_domains(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT d.*, m.reason, m.filter_id, m.rule, m.client
                FROM domains d
                LEFT JOIN metadata m ON d.id = m.domain_id
                ORDER BY d.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_domains(self) -> List[Dict[str, Any]]:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT domain, entropy, risk_score, category, is_anomaly, anomaly_score, timestamp
                FROM domains
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_domain_features(self) -> List[List[float]]:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT d.entropy, f.length, f.digit_ratio, f.vowel_ratio, f.non_alphanumeric
                FROM domains d
                LEFT JOIN features f ON d.id = f.domain_id
                WHERE d.entropy IS NOT NULL AND f.length IS NOT NULL
                """
            )
            rows = cursor.fetchall()
            return [[float(x) for x in row] for row in rows if all(x is not None for x in row)]

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            cursor = self.connection.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM domains")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) as anomalies FROM domains WHERE is_anomaly = 1")
            anomalies = cursor.fetchone()[0]

            cursor.execute(
                "SELECT category, COUNT(*) as count FROM domains GROUP BY category"
            )
            categories = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                "SELECT analysis_source, COUNT(*) as count FROM domains GROUP BY analysis_source"
            )
            sources = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_domains": total,
                "total_anomalies": anomalies,
                "categories": categories,
                "analysis_sources": sources,
            }

    def close(self) -> None:
        with self.lock:
            self.connection.close()


db_logger = DBLogger()
