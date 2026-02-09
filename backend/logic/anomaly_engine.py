import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

class AnomalyEngine:
    def __init__(self, contamination=0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.history = []
        self.is_trained = False
        self.min_samples = 5

    def predict_anomaly(self, features: list) -> tuple[bool, float]:
        # Add to history for future learning
        self.history.append(features)
        
        # Cold Start Check
        if len(self.history) < self.min_samples:
            return False, 0.0
        
        # Train if not trained or periodically retrain
        if not self.is_trained or len(self.history) % 100 == 0:
            X = np.array(self.history)
            self.model.fit(X)
            self.is_trained = True
        
        # Predict
        X_curr = np.array([features])
        prediction = self.model.predict(X_curr) # Returns 1 for inlier, -1 for outlier
        score = self.model.decision_function(X_curr) # The anomaly score of the input samples.
        
        is_anomaly = bool(prediction[0] == -1)
        # Convert decision function score to a more readable float (higher = more anomalous in some contexts, 
        # but sklearn decision_function returns lower values for anomalies)
        # Standard anomaly score: higher is more anomalous. 
        # decision_function returns values where negative is anomalous.
        return is_anomaly, float(score[0])

# Global instance
engine = AnomalyEngine()

def predict_anomaly(features: list) -> tuple[bool, float]:
    return engine.predict_anomaly(features)
