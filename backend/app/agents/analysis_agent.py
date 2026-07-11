"""
Analysis Agent with LSTM Integration
Predicts prices using neural network
"""

from app.agents.base_agent import BDIAgent, Goal, Plan
from app.models.price_lstm import PricePredictorNN
from typing import Dict, Any, List
import numpy as np


class AnalysisAgent(BDIAgent):
    """
    Analysis Agent with Neural Network
    
    Features:
    - LSTM price prediction
    - Feature extraction
    - Confidence calculation
    - BDI architecture
    """
    
    def __init__(self, agent_id: str, name: str = "Analyzer"):
        super().__init__(agent_id, name)
        
        # Load neural network
        self.price_predictor = PricePredictorNN()
        
        self.log("Initialized with LSTM model")
    
    def generate_goals(self) -> List[Goal]:
        """Generate analysis goals"""
        goals = []
        
        # Check if we have data to analyze
        if self.has_belief('scraped_data') and self.get_belief('scraping_success'):
            goals.append(Goal(
                name="analyze_prices",
                priority=10
            ))
        
        # Check if model needs training
        if not self.price_predictor.is_trained:
            goals.append(Goal(
                name="check_training",
                priority=5
            ))
        
        return goals
    
    def create_plan(self, goal: Goal) -> Plan:
        """Create analysis plan"""
        if goal.name == "analyze_prices":
            return Plan(steps=[
                "extract_features",
                "predict_prices",
                "calculate_confidence",
                "validate_prediction"
            ])
        
        elif goal.name == "check_training":
            return Plan(steps=[
                "log_training_status"
            ])
        
        return Plan(steps=[])
    
    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """Execute analysis action"""
        try:
            if action == "extract_features":
                data = self.get_belief('scraped_data')
                category = self.get_belief('category', 'unknown')
                
                features = self.extract_features(data, category)
                self.update_belief('features', features)
                self.log(f"Extracted {len(features)} features (category: {category})")
                return True
            
            elif action == "predict_prices":
                features = self.get_belief('features')
                
                if features is None:
                    self.log("No features available")
                    return False
                
                # Use LSTM to predict
                prediction = self.price_predictor.predict(features)
                self.update_belief('price_prediction', prediction)
                
                self.log(f"Predicted: Buy={prediction['buy_price']}, Sell={prediction['sell_price']}, Margin={prediction['margin']}%")
                return True
            
            elif action == "calculate_confidence":
                confidence = self.calculate_confidence()
                self.update_belief('confidence', confidence)
                self.log(f"Confidence: {confidence:.2f}")
                return True
            
            elif action == "validate_prediction":
                prediction = self.get_belief('price_prediction')
                
                if not prediction:
                    return False
                
                # Validate prediction makes sense
                if prediction['buy_price'] <= 0 or prediction['sell_price'] <= 0:
                    self.log("Invalid prediction (negative prices)")
                    return False
                
                if prediction['margin'] < 0:
                    self.log("Warning: Negative margin")
                
                return True
            
            elif action == "log_training_status":
                if self.price_predictor.is_trained:
                    self.log("Model is trained ✅")
                else:
                    self.log("⚠️ Model not trained - using fallback")
                return True
            
            return False
        
        except Exception as e:
            self.log(f"Error in {action}: {e}")
            return False
    
    def extract_features(self, data: Dict[str, Any], category: str = 'unknown') -> np.ndarray:
        """
        Extract features from scraped data
        
        Features (20 total):
        - Wholesale: mean, std, min, max, count (5)
        - Retail: mean, std, min, max, count (5)
        - Market: total, w/r ratio, noise, reserved (5)
        - Category: one-hot encoding (5)
        """
        # Category encoding map
        category_map = {
            'headset': [1, 0, 0, 0, 0],
            'keyboard': [0, 1, 0, 0, 0],
            'mouse': [0, 0, 1, 0, 0],
            'monitor': [0, 0, 0, 1, 0],
            'other': [0, 0, 0, 0, 1]
        }
        
        features = []
        
        # Wholesale features
        wholesale = data.get('wholesale', [])
        if wholesale:
            prices = [p.get('price_pkr', 0) for p in wholesale if p.get('price_pkr')]
            if prices:
                features.extend([
                    np.mean(prices),
                    np.std(prices) if len(prices) > 1 else 0,
                    np.min(prices),
                    np.max(prices),
                    len(prices)
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        # Retail features
        retail = data.get('retail', [])
        if retail:
            prices = [p.get('price_pkr', 0) for p in retail if p.get('price_pkr')]
            if prices:
                features.extend([
                    np.mean(prices),
                    np.std(prices) if len(prices) > 1 else 0,
                    np.min(prices),
                    np.max(prices),
                    len(prices)
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        # Market features
        wholesale_count = len(wholesale)
        retail_count = len(retail)
        total_count = wholesale_count + retail_count
        wr_ratio = wholesale_count / (retail_count + 1)
        
        features.extend([
            total_count,
            wr_ratio,
            np.random.random(),  # Noise
            0,  # Reserved
            0   # Reserved
        ])
        
        # Category encoding (NEW!)
        category_features = category_map.get(category.lower(), category_map['other'])
        features.extend(category_features)
        
        return np.array(features)
    
    def calculate_confidence(self) -> float:
        """
        Calculate prediction confidence
        
        Based on:
        - Data quantity
        - Model training status
        - Price variance
        """
        data = self.get_belief('scraped_data', {})
        
        wholesale_count = len(data.get('wholesale', []))
        retail_count = len(data.get('retail', []))
        total_count = wholesale_count + retail_count
        
        # Base confidence on data quantity
        data_confidence = min(1.0, total_count / 20)
        
        # Adjust for model status
        model_confidence = 1.0 if self.price_predictor.is_trained else 0.5
        
        # Combined confidence
        confidence = (data_confidence + model_confidence) / 2
        
        return confidence
    
    def export_state(self) -> Dict[str, Any]:
        """Export state for LangGraph"""
        return {
            'features': self.get_belief('features'),
            'price_prediction': self.get_belief('price_prediction'),
            'confidence': self.get_belief('confidence', 0.0),
            'current_agent': self.name
        }
