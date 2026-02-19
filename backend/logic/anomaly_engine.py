from typing import Tuple, List

import numpy as np
from sklearn.ensemble import IsolationForest


MAX_HISTORY_SIZE = 10000


class AnomalyEngine:
    def __init__(self, contamination: float = 0.05, max_history: int = MAX_HISTORY_SIZE):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.history: List[List[float]] = []
        self.is_trained = False
        self.min_samples = 5
        self.max_history = max_history

    def predict_anomaly(self, features: List[float]) -> Tuple[bool, float]:
        # Add to history for future learning
        self.history.append(features)

        # Prevent unbounded memory growth
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Cold Start Check - need at least 10 samples before making predictions
        if len(self.history) < self.min_samples * 2:
            return False, 0.0

        # Train if not trained or periodically retrain
        if not self.is_trained or len(self.history) % 100 == 0:
            X = np.array(self.history)
            self.model.fit(X)
            self.is_trained = True

        # Predict
        X_curr = np.array([features])
        prediction = self.model.predict(X_curr)
        score = self.model.decision_function(X_curr)

        # Only flag as anomaly if score is significantly negative (< -0.1)
        is_anomaly = bool(prediction[0] == -1 and score[0] < -0.1)
        return is_anomaly, float(score[0])


# Global instance
engine = AnomalyEngine()


def predict_anomaly(features: List[float]) -> Tuple[bool, float]:
    return engine.predict_anomaly(features)
