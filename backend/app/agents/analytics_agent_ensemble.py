"""
Analytics Agent - XGBoost + Random Forest Ensemble
Document-compliant price prediction using ensemble learning
"""

from app.agents.base_agent import BDIAgent, Goal, Plan
from typing import Dict, Any, List, Optional
import numpy as np
import pickle
import os


class AnalyticsAgent(BDIAgent):
    """
    Analytics Agent using XGBoost + Random Forest Ensemble
    
    As per FYP Document Section 2.5.3:
    "The Analytics Agent applies supervised learning models—XGBoost and 
    Random Forest Regression—to predict optimal selling prices and expected 
    profit margins from wholesale and retail datasets."
    
    Features:
    - XGBoost Regressor
    - Random Forest Regressor
    - Ensemble predictions (average)
    - 20-feature engineering
    - Category-aware
    - BDI architecture
    """
    
    def __init__(self, agent_id: str, name: str = "Analytics"):
        super().__init__(agent_id, name)
        
        # Models
        self.xgb_model = None
        self.rf_model = None
        
        # Model paths
        self.model_dir = "app/models/saved"
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Load models if exist
        self.load_models()
    
    def generate_goals(self) -> List[Goal]:
        """Generate analytics goals"""
        goals = []
        
        if self.has_belief('clean_data'):
            goals.append(Goal(
                name="predict_prices",
                priority=10
            ))
        
        return goals
    
    def create_plan(self, goal: Goal) -> Plan:
        """Create analytics plan"""
        if goal.name == "predict_prices":
            return Plan(steps=[
                "extract_features",
                "predict_xgboost",
                "predict_random_forest",
                "ensemble_predictions",
                "calculate_confidence",
                "validate_predictions"
            ])
        
        return Plan(steps=[])
    
    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """Execute analytics action"""
        try:
            if action == "extract_features":
                clean_data = self.get_belief('clean_data')
                category = self.get_belief('category', '')
                
                # Extract features
                features = self.prepare_features(clean_data, category)
                
                if features is None:
                    self.log("Failed to extract features")
                    return False
                
                self.update_belief('features', features)
                self.log(f"Extracted {len(features)} features")
                return True
            
            elif action == "predict_xgboost":
                features = self.get_belief('features')
                
                if self.xgb_model is None:
                    self.log("⚠️ XGBoost model not trained")
                    self.update_belief('xgb_prediction', None)
                    return True
                
                # Predict with XGBoost
                prediction = self.xgb_model.predict([features])[0]
                
                self.update_belief('xgb_prediction', prediction)
                self.log(f"XGBoost prediction: {prediction}")
                return True
            
            elif action == "predict_random_forest":
                features = self.get_belief('features')
                
                if self.rf_model is None:
                    self.log("⚠️ Random Forest model not trained")
                    self.update_belief('rf_prediction', None)
                    return True
                
                # Predict with Random Forest
                prediction = self.rf_model.predict([features])[0]
                
                self.update_belief('rf_prediction', prediction)
                self.log(f"Random Forest prediction: {prediction}")
                return True
            
            elif action == "ensemble_predictions":
                xgb_pred = self.get_belief('xgb_prediction')
                rf_pred = self.get_belief('rf_prediction')
                
                if xgb_pred is None and rf_pred is None:
                    self.log("No predictions available")
                    return False
                
                # Ensemble (average)
                if xgb_pred is not None and rf_pred is not None:
                    final_pred = (xgb_pred + rf_pred) / 2
                    self.log(f"Ensemble: ({xgb_pred} + {rf_pred}) / 2 = {final_pred}")
                elif xgb_pred is not None:
                    final_pred = xgb_pred
                    self.log(f"Using XGBoost only: {final_pred}")
                else:
                    final_pred = rf_pred
                    self.log(f"Using Random Forest only: {final_pred}")
                
                self.update_belief('price_prediction', final_pred)
                return True
            
            elif action == "calculate_confidence":
                xgb_pred = self.get_belief('xgb_prediction')
                rf_pred = self.get_belief('rf_prediction')
                clean_data = self.get_belief('clean_data', {})
                
                # Calculate confidence based on:
                # 1. Model agreement
                # 2. Data quantity
                
                confidence = 0.5  # Base
                
                # Model agreement
                if xgb_pred is not None and rf_pred is not None:
                    diff = abs(xgb_pred - rf_pred)
                    agreement = 1.0 - min(diff / max(xgb_pred, rf_pred, 1), 1.0)
                    confidence += agreement * 0.3
                
                # Data quantity
                total_products = len(clean_data.get('wholesale', [])) + len(clean_data.get('retail', []))
                if total_products >= 10:
                    confidence += 0.2
                elif total_products >= 5:
                    confidence += 0.1
                
                confidence = min(confidence, 1.0)
                
                self.update_belief('confidence', confidence)
                self.log(f"Confidence: {confidence:.2f}")
                return True
            
            elif action == "validate_predictions":
                prediction = self.get_belief('price_prediction')
                confidence = self.get_belief('confidence', 0.0)
                
                if prediction is None:
                    return False
                
                self.log(f"Final: Price={prediction}, Confidence={confidence:.2f}")
                return True
            
            return False
        
        except Exception as e:
            self.log(f"Error in {action}: {e}")
            return False
    
    def prepare_features(self, clean_data: Dict[str, Any], category: str) -> Optional[np.ndarray]:
        """
        Extract 20 features from clean data
        
        Features (20 total):
        - Wholesale stats (5): mean, std, min, max, count
        - Retail stats (5): mean, std, min, max, count
        - Market stats (5): wholesale/retail ratio, price range, avg margin, etc.
        - Category encoding (5): one-hot for headset, keyboard, mouse, monitor, other
        """
        try:
            wholesale = clean_data.get('wholesale', [])
            retail = clean_data.get('retail', [])
            
            if not wholesale and not retail:
                return None
            
            # Wholesale features
            if wholesale:
                w_prices = [p.get('price_pkr', 0) for p in wholesale]
                w_mean = np.mean(w_prices)
                w_std = np.std(w_prices)
                w_min = np.min(w_prices)
                w_max = np.max(w_prices)
                w_count = len(w_prices)
            else:
                w_mean = w_std = w_min = w_max = w_count = 0
            
            # Retail features
            if retail:
                r_prices = [p.get('price_pkr', 0) for p in retail]
                r_mean = np.mean(r_prices)
                r_std = np.std(r_prices)
                r_min = np.min(r_prices)
                r_max = np.max(r_prices)
                r_count = len(r_prices)
            else:
                r_mean = r_std = r_min = r_max = r_count = 0
            
            # Market features
            if w_mean > 0 and r_mean > 0:
                price_ratio = r_mean / w_mean
                margin = ((r_mean - w_mean) / r_mean) * 100
            else:
                price_ratio = margin = 0
            
            price_range = max(w_max, r_max) - min(w_min, r_min) if (w_min > 0 or r_min > 0) else 0
            total_count = w_count + r_count
            avg_price = (w_mean + r_mean) / 2 if (w_mean > 0 or r_mean > 0) else 0
            
            # Category encoding (one-hot)
            categories = ['headset', 'keyboard', 'mouse', 'monitor', 'other']
            category_lower = category.lower()
            
            if category_lower not in categories:
                category_lower = 'other'
            
            category_features = [1 if cat == category_lower else 0 for cat in categories]
            
            # Combine all features
            features = np.array([
                # Wholesale (5)
                w_mean, w_std, w_min, w_max, w_count,
                # Retail (5)
                r_mean, r_std, r_min, r_max, r_count,
                # Market (5)
                price_ratio, margin, price_range, total_count, avg_price,
                # Category (5)
                *category_features
            ], dtype=np.float32)
            
            return features
        
        except Exception as e:
            self.log(f"Feature extraction error: {e}")
            return None
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train both XGBoost and Random Forest models
        
        Args:
            X: Features (N x 20)
            y: Target prices (N,)
        """
        try:
            from xgboost import XGBRegressor
            from sklearn.ensemble import RandomForestRegressor
            
            self.log(f"Training models on {len(X)} samples...")
            
            # Train XGBoost
            self.xgb_model = XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            self.xgb_model.fit(X, y)
            self.log("✅ XGBoost trained")
            
            # Train Random Forest
            self.rf_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.rf_model.fit(X, y)
            self.log("✅ Random Forest trained")
            
            # Save models
            self.save_models()
            
            return True
        
        except Exception as e:
            self.log(f"Training error: {e}")
            return False
    
    def save_models(self):
        """Save trained models"""
        try:
            if self.xgb_model:
                xgb_path = os.path.join(self.model_dir, 'xgboost_model.pkl')
                with open(xgb_path, 'wb') as f:
                    pickle.dump(self.xgb_model, f)
                self.log(f"Saved XGBoost to {xgb_path}")
            
            if self.rf_model:
                rf_path = os.path.join(self.model_dir, 'random_forest_model.pkl')
                with open(rf_path, 'wb') as f:
                    pickle.dump(self.rf_model, f)
                self.log(f"Saved Random Forest to {rf_path}")
        
        except Exception as e:
            self.log(f"Save error: {e}")
    
    def load_models(self):
        """Load trained models"""
        try:
            xgb_path = os.path.join(self.model_dir, 'xgboost_model.pkl')
            if os.path.exists(xgb_path):
                with open(xgb_path, 'rb') as f:
                    self.xgb_model = pickle.load(f)
                self.log("Loaded XGBoost model")
            
            rf_path = os.path.join(self.model_dir, 'random_forest_model.pkl')
            if os.path.exists(rf_path):
                with open(rf_path, 'rb') as f:
                    self.rf_model = pickle.load(f)
                self.log("Loaded Random Forest model")
        
        except Exception as e:
            self.log(f"Load error: {e}")
    
    def export_state(self) -> Dict[str, Any]:
        """Export state for LangGraph"""
        return {
            'price_prediction': self.get_belief('price_prediction'),
            'confidence': self.get_belief('confidence', 0.0),
            'xgb_prediction': self.get_belief('xgb_prediction'),
            'rf_prediction': self.get_belief('rf_prediction'),
            'current_agent': self.name
        }


# Test
if __name__ == "__main__":
    print("Testing Analytics Agent...")
    
    # Mock clean data
    clean_data = {
        'wholesale': [
            {'price_pkr': 2000},
            {'price_pkr': 2500},
            {'price_pkr': 2200}
        ],
        'retail': [
            {'price_pkr': 3500},
            {'price_pkr': 4000},
            {'price_pkr': 3800}
        ]
    }
    
    agent = AnalyticsAgent("analytics_1", "Analytics")
    
    # Set beliefs
    agent.update_belief('clean_data', clean_data)
    agent.update_belief('category', 'headset')
    
    # Run
    result = agent.run_cycle({
        'clean_data': clean_data,
        'category': 'headset'
    })
    
    print(f"\n✅ Prediction: {result.get('price_prediction')}")
    print(f"✅ Confidence: {result.get('confidence')}")
