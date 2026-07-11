"""
LSTM Price Prediction Model
2-layer LSTM for buy/sell price prediction
"""

try:
    
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ PyTorch not available, using scikit-learn fallback")

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
from typing import Dict, List, Tuple


if TORCH_AVAILABLE:
    class PriceLSTM(nn.Module):
        """
        LSTM Neural Network for Price Prediction
        
        Architecture:
        - Input: Sequential features (batch, seq_len, features)
        - LSTM: 2 layers with dropout
        - Dense: Fully connected layers
        - Output: [buy_price, sell_price]
        """
        
        def __init__(self, input_size=20, hidden_size=64, num_layers=2, dropout=0.2):
            super().__init__()
            
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            # LSTM layers
            self.lstm = nn.LSTM(
                input_size=input_size,  # Now 20 (15 + 5 category)
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0
            )
            
            # Fully connected layers
            self.fc1 = nn.Linear(hidden_size, 32)
            self.fc2 = nn.Linear(32, 2)  # buy_price, sell_price
            
            # Activation and regularization
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(dropout)
        
        def forward(self, x):
            """
            Forward pass
            
            Args:
                x: (batch, seq_len, features)
            
            Returns:
                predictions: (batch, 2) - [buy_price, sell_price]
            """
            # LSTM forward
            lstm_out, (h_n, c_n) = self.lstm(x)
            
            # Use last hidden state
            x = lstm_out[:, -1, :]
            
            # Dense layers
            x = self.relu(self.fc1(x))
            x = self.dropout(x)
            x = self.fc2(x)
            
            return x


class PricePredictorNN:
    """
    Neural Network Price Predictor
    Handles training, prediction, and model persistence
    """
    
    def __init__(self, model_path='models'):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        
        if TORCH_AVAILABLE:
            self.model = PriceLSTM()
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
            self.criterion = nn.MSELoss()
            self.use_torch = True
        else:
            # Fallback to Random Forest
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.use_torch = False
        
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Try to load existing model
        self.load_model()
    
    def prepare_features(self, data: List[Dict], category: str = 'unknown') -> np.ndarray:
        """
        Extract features from scraped data
        
        Features (20 total):
        - Wholesale: mean, std, min, max, count (5)
        - Retail: mean, std, min, max, count (5)
        - Market: total, w/r ratio, noise, reserved (5)
        - Category: one-hot encoding (5)
        """
        features_list = []
        
        # Category encoding map
        category_map = {
            'headset': [1, 0, 0, 0, 0],
            'keyboard': [0, 1, 0, 0, 0],
            'mouse': [0, 0, 1, 0, 0],
            'monitor': [0, 0, 0, 1, 0],
            'other': [0, 0, 0, 0, 1]  # For future categories
        }
        
        for item in data:
            features = []
            
            # Wholesale features
            wholesale = item.get('wholesale', [])
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
            retail = item.get('retail', [])
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
            total_count = len(wholesale) + len(retail)
            wr_ratio = len(wholesale) / (len(retail) + 1)
            
            features.extend([
                total_count,
                wr_ratio,
                np.random.random(),  # Noise for robustness
                0,  # Reserved
                0   # Reserved
            ])
            
            # Category encoding (NEW!)
            category_features = category_map.get(category.lower(), category_map['other'])
            features.extend(category_features)
            
            features_list.append(features)
        
        return np.array(features_list)
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs=50, batch_size=32):
        """
        Train the model
        
        Args:
            X: Features (n_samples, n_features)
            y: Targets (n_samples, 2) - [buy_price, sell_price]
            epochs: Number of training epochs
            batch_size: Batch size
        """
        print(f"[PricePredictor] Training with {len(X)} samples...")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        if self.use_torch and TORCH_AVAILABLE:
            # PyTorch training
            self.model.train()
            
            # Convert to tensors
            X_tensor = torch.FloatTensor(X_scaled).unsqueeze(1)  # Add sequence dimension
            y_tensor = torch.FloatTensor(y)
            
            # Training loop
            for epoch in range(epochs):
                self.optimizer.zero_grad()
                
                # Forward pass
                predictions = self.model(X_tensor)
                loss = self.criterion(predictions, y_tensor)
                
                # Backward pass
                loss.backward()
                self.optimizer.step()
                
                if (epoch + 1) % 10 == 0:
                    print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")
        
        else:
            # Scikit-learn training
            self.model.fit(X_scaled, y)
            print("  ✅ Random Forest trained")
        
        self.is_trained = True
        self.save_model()
        print("  ✅ Model saved")
    
    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """
        Predict prices for new product
        
        Args:
            features: Feature vector (n_features,)
        
        Returns:
            {buy_price, sell_price, margin}
        """
        if not self.is_trained:
            return self.fallback_prediction(features)
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        if self.use_torch and TORCH_AVAILABLE:
            # PyTorch prediction
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(features_scaled).unsqueeze(1)
                predictions = self.model(X_tensor)
                buy_price = predictions[0][0].item()
                sell_price = predictions[0][1].item()
        else:
            # Scikit-learn prediction
            predictions = self.model.predict(features_scaled)[0]
            buy_price = predictions[0]
            sell_price = predictions[1]
        
        # Ensure positive prices
        buy_price = max(0, buy_price)
        sell_price = max(0, sell_price)
        
        # Calculate margin
        margin = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
        
        return {
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'margin': round(margin, 2)
        }
    
    def fallback_prediction(self, features: np.ndarray) -> Dict[str, float]:
        """Simple rule-based prediction when model not trained"""
        wholesale_avg = features[0]
        retail_avg = features[5]
        
        buy_price = wholesale_avg if wholesale_avg > 0 else retail_avg * 0.6
        sell_price = retail_avg if retail_avg > 0 else wholesale_avg * 1.5
        
        margin = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
        
        return {
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'margin': round(margin, 2)
        }
    
    def save_model(self):
        """Save model to disk"""
        if self.use_torch and TORCH_AVAILABLE:
            torch.save({
                'model_state': self.model.state_dict(),
                'optimizer_state': self.optimizer.state_dict(),
                'scaler': self.scaler
            }, f'{self.model_path}/price_lstm.pth')
        else:
            joblib.dump(self.model, f'{self.model_path}/price_rf.pkl')
            joblib.dump(self.scaler, f'{self.model_path}/scaler.pkl')
    
    def load_model(self):
        """Load model from disk"""
        try:
            if self.use_torch and TORCH_AVAILABLE:
                checkpoint = torch.load(f'{self.model_path}/price_lstm.pth')
                self.model.load_state_dict(checkpoint['model_state'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state'])
                self.scaler = checkpoint['scaler']
                self.is_trained = True
                print("✅ LSTM model loaded")
            else:
                self.model = joblib.load(f'{self.model_path}/price_rf.pkl')
                self.scaler = joblib.load(f'{self.model_path}/scaler.pkl')
                self.is_trained = True
                print("✅ Random Forest model loaded")
        except:
            print("ℹ️ No pre-trained model found")


# Test
if __name__ == "__main__":
    print("Testing Price Predictor...")
    
    predictor = PricePredictorNN()
    
    # Dummy features
    features = np.random.rand(15)
    
    prediction = predictor.predict(features)
    print(f"\nPrediction: {prediction}")
