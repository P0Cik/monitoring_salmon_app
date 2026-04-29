# [FILE: ras_monitor/ml/predictor.py]
"""
LSTM-based predictor for RAS water quality forecasting.
Handles model loading, preprocessing, and inference.
"""

import os
import sys
import pickle
from pathlib import Path
from typing import Dict, Optional, List

import numpy as np
import torch
import torch.nn as nn


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and PyInstaller bundle.
    
    Args:
        relative_path: Relative path to the resource
        
    Returns:
        Absolute path to the resource
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Development mode
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


class LSTMModel(nn.Module):
    """
    LSTM model for water quality state prediction.
    
    Architecture:
    - Input: (batch, seq_len=6, features=6)
    - LSTM: 1 hidden layer, 32 hidden units
    - Dense: 32 -> 4 outputs (states 1-4)
    - Softmax for probability distribution
    """
    
    def __init__(
        self, 
        input_size: int = 6,
        hidden_size: int = 32,
        num_layers: int = 1,
        output_size: int = 4
    ):
        super(LSTMModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, output_size)
        )
        
        self.softmax = nn.Softmax(dim=1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch, seq_len, features)
            
        Returns:
            Output probabilities of shape (batch, output_size)
        """
        # LSTM forward
        lstm_out, _ = self.lstm(x)
        
        # Take only the last time step
        last_output = lstm_out[:, -1, :]
        
        # Fully connected layers
        out = self.fc(last_output)
        
        # Softmax for probabilities
        probs = self.softmax(out)
        
        return probs


class Predictor:
    """
    Water quality state predictor using LSTM.
    
    Predicts the next state (t+1) based on a window of 6 previous measurements.
    """
    
    WINDOW_SIZE = 6
    FEATURES = ['temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity']
    
    def __init__(self, model_path: Optional[str] = None, scaler_path: Optional[str] = None):
        """
        Initialize the predictor.
        
        Args:
            model_path: Path to saved model weights (.pth)
            scaler_path: Path to saved StandardScaler (.pkl)
        """
        self.device = torch.device('cpu')
        self.model: Optional[LSTMModel] = None
        self.scaler = None
        self.is_loaded = False
        
        # Default paths relative to this module
        if model_path is None:
            model_path = get_resource_path("model.pth")
        if scaler_path is None:
            scaler_path = get_resource_path("scaler.pkl")
        
        self.model_path = model_path
        self.scaler_path = scaler_path
    
    def load_model(self) -> bool:
        """
        Load the trained model and scaler.
        
        Returns:
            True if loading successful, False otherwise
        """
        try:
            # Load model architecture and weights
            self.model = LSTMModel().to(self.device)
            
            if not os.path.exists(self.model_path):
                print(f"Model file not found: {self.model_path}")
                return False
            
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            
            # Load scaler
            if not os.path.exists(self.scaler_path):
                print(f"Scaler file not found: {self.scaler_path}")
                return False
            
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict(
        self, 
        measurements: List[List[float]]
    ) -> Optional[Dict[int, float]]:
        """
        Predict state probabilities for the next time step.
        
        Args:
            measurements: List of 6 measurements, each containing 
                         [temp, ph, o2, ammonia, nitrite, salinity]
            
        Returns:
            Dictionary mapping state_id (1-4) to probability,
            or None if prediction failed
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        if len(measurements) != self.WINDOW_SIZE:
            print(f"Expected {self.WINDOW_SIZE} measurements, got {len(measurements)}")
            return None
        
        try:
            # Convert to numpy array
            data = np.array(measurements)
            
            # Apply scaling
            if self.scaler is not None:
                data = self.scaler.transform(data)
            
            # Convert to tensor: (1, seq_len=6, features=6)
            tensor_data = torch.FloatTensor(data).unsqueeze(0).to(self.device)
            
            # Predict
            with torch.no_grad():
                probs = self.model(tensor_data)
            
            # Convert to dictionary {state_id: probability}
            # States are 1-4, so we add 1 to indices
            prob_array = probs.cpu().numpy()[0]
            result = {i + 1: float(prob) for i, prob in enumerate(prob_array)}
            
            return result
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
    
    def get_predicted_state(self, probs: Dict[int, float]) -> int:
        """
        Get the most likely predicted state from probabilities.
        
        Args:
            probs: Dictionary of state probabilities
            
        Returns:
            Most likely state (1-4)
        """
        return max(probs, key=probs.get)
    
    def get_forecast_dynamics(
        self, 
        current_state: int, 
        probs: Dict[int, float]
    ) -> str:
        """
        Determine forecast dynamics based on current and predicted states.
        
        Args:
            current_state: Current state (0-4)
            probs: Predicted state probabilities
            
        Returns:
            Dynamics string: "Стабильно", "Ухудшение", or "Улучшение"
        """
        predicted_state = self.get_predicted_state(probs)
        
        # Note: predicted states are 1-4, current can be 0-4
        # For comparison, treat predicted as-is
        if predicted_state == current_state:
            return "Стабильно"
        elif predicted_state > current_state:
            return "Ухудшение"
        else:
            return "Улучшение"
    
    def get_confidence(self, probs: Dict[int, float]) -> float:
        """
        Get confidence score for the prediction.
        
        Args:
            probs: State probabilities
            
        Returns:
            Confidence (max probability)
        """
        return max(probs.values())
