import json

import numpy as np
from sklearn.ensemble import IsolationForest

from ..core.alerting import AlertSeverity, AlertType, alert_manager

MAX_HISTORY_SIZE = 10000


class AnomalyEngine:
    def __init__(self, contamination: float = 0.05, max_history: int = MAX_HISTORY_SIZE):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.history: list[list[float]] = []
        self.is_trained = False
        self.min_samples = 5
        self.max_history = max_history
        self.contamination = contamination

        # Deferred: call async def init() from lifespan startup

    async def init(self):
        """Load persisted history. Call from lifespan startup."""
        await self.load_history()

    def predict_anomaly(self, features: list[float]) -> tuple[bool, float]:
        # Add to history for future learning
        self.history.append(features)

        # Prevent unbounded memory growth
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        # Cold Start Check - need at least 10 samples before making predictions
        if len(self.history) < self.min_samples * 2:
            # Trigger alert for insufficient training data
            try:
                alert_manager.create_alert_sync(
                    alert_type=AlertType.SYSTEM_RESOURCE,
                    severity=AlertSeverity.MEDIUM,
                    message=f"ML model cold start: Only {len(self.history)} samples available, need {self.min_samples * 2}",
                    details={
                        "training_samples": len(self.history),
                        "min_samples_required": self.min_samples * 2,
                        "model_status": "cold_start",
                        "analysis_source": "anomaly_engine",
                    },
                )
            except Exception as e:
                print(f"Alert creation failed: {e}")
            return False, 0.0

        # Train if not trained or periodically retrain
        if not self.is_trained or len(self.history) % 100 == 0:
            try:
                X = np.array(self.history)
                self.model.fit(X)
                self.is_trained = True
            except Exception as e:
                # Trigger alert for ML model training failure
                try:
                    alert_manager.create_alert_sync(
                        alert_type=AlertType.SYSTEM_RESOURCE,
                        severity=AlertSeverity.HIGH,
                        message=f"ML model training failed: {str(e)}",
                        details={
                            "error": str(e),
                            "training_samples": len(self.history),
                            "model_status": "training_failed",
                            "analysis_source": "anomaly_engine",
                        },
                    )
                except Exception as alert_e:
                    print(f"Alert creation failed: {alert_e}")
                return False, 0.0

        # Predict
        try:
            X_curr = np.array([features])
            prediction = self.model.predict(X_curr)
            score = self.model.decision_function(X_curr)

            # Only flag as anomaly if score is significantly negative (< -0.1)
            is_anomaly = bool(prediction[0] == -1 and score[0] < -0.1)
            return is_anomaly, float(score[0])
        except Exception as e:
            # Trigger alert for ML model prediction failure
            try:
                alert_manager.create_alert_sync(
                    alert_type=AlertType.SYSTEM_RESOURCE,
                    severity=AlertSeverity.HIGH,
                    message=f"ML model prediction failed: {str(e)}",
                    details={
                        "error": str(e),
                        "features": features,
                        "model_status": "prediction_failed",
                        "analysis_source": "anomaly_engine",
                    },
                )
            except Exception as alert_e:
                print(f"Alert creation failed: {alert_e}")
            return False, 0.0

    async def save_history(self):
        """Persist anomaly history to database."""
        from ..db.database import get_session
        from ..db.models import SystemStats
        from sqlalchemy import select

        try:
            async with get_session() as session:
                history_json = json.dumps(self.history[-1000:])
                result = await session.execute(
                    select(SystemStats).where(
                        SystemStats.tenant_id == 1,
                        SystemStats.key == "anomaly_history",
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.value = history_json
                else:
                    session.add(SystemStats(tenant_id=1, key="anomaly_history", value=history_json))
                await session.commit()
        except Exception as e:
            print(f"Warning: Could not save anomaly history: {e}")

    def _save_history_async(self):
        """Non-blocking history save."""
        import asyncio

        try:
            asyncio.ensure_future(self.save_history())
        except Exception:
            pass

    async def load_history(self):
        """Load anomaly history from database."""
        from ..db.database import get_session
        from ..db.models import SystemStats
        from sqlalchemy import select

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(SystemStats).where(
                        SystemStats.tenant_id == 1,
                        SystemStats.key == "anomaly_history",
                    )
                )
                row = result.scalar_one_or_none()
                if row:
                    self.history = json.loads(row.value)
                    # Retrain model on loaded history
                    if len(self.history) >= self.min_samples * 2:
                        X = np.array(self.history)
                        self.model.fit(X)
                        self.is_trained = True
                        print(
                            f"AnomalyEngine: Restored {len(self.history)} samples from DB, model retrained"
                        )
        except Exception as e:
            print(f"Warning: Could not load anomaly history: {e}")

    def _load_history_async(self):
        """Non-blocking history load."""
        import asyncio

        try:
            asyncio.ensure_future(self.load_history())
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Get anomaly engine statistics"""
        return {
            "is_trained": self.is_trained,
            "training_samples": len(self.history),
            "min_samples_required": self.min_samples * 2,
            "max_history_size": self.max_history,
            "ready_for_prediction": len(self.history) >= self.min_samples * 2,
            "contamination_rate": self.contamination,
        }


# Global instance
engine = AnomalyEngine()


def predict_anomaly(features: list[float]) -> tuple[bool, float]:
    return engine.predict_anomaly(features)


def get_anomaly_stats() -> dict:
    """Get anomaly detection statistics"""
    return engine.get_stats()
