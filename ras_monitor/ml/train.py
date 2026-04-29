# [FILE: ras_monitor/ml/train.py]
"""
Training script for LSTM water quality prediction model.
Generates synthetic data, trains the model, and saves weights + scaler.
"""

import os
import pickle
import random
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler

from .predictor import LSTMModel


# Normal ranges for synthetic data generation
NORMAL_RANGES = {
    'temp': (12.0, 14.0),
    'ph': (7.4, 7.8),
    'o2': (90, 100),
    'ammonia': (0, 0.5),
    'nitrite': (0, 0.1),
    'salinity': (0, 0),
}

# Severity thresholds for generating realistic state transitions
THRESHOLDS = {
    'temp': [(11, 12), (14, 15), (9, 11), (15, 17), (5, 9), (17, 21)],
    'ph': [(7.2, 7.4), (7.8, 8.0), (7.0, 7.2), (8.0, 8.2), (6.6, 7.0), (8.2, 8.6)],
    'o2': [(85, 90), (70, 85), (60, 70)],
    'ammonia': [(0.5, 0.6), (0.6, 1.0), (1.0, 1.5)],
    'nitrite': [(0.1, 0.15), (0.15, 0.2), (0.2, 0.25)],
    'salinity': [(0, 0.1), (0.1, 0.5), (0.5, 1.0)],
}


def generate_synthetic_measurement(
    base_values: dict,
    noise_level: float = 0.03
) -> dict:
    """
    Generate a single synthetic measurement with small noise.
    
    Args:
        base_values: Base parameter values
        noise_level: Noise level as fraction (default 3%)
        
    Returns:
        Dictionary with measurement values
    """
    measurement = {}
    
    for param, base_val in base_values.items():
        if param == 'salinity' and base_val == 0:
            # Salinity stays at 0 or small deviation
            measurement[param] = max(0, base_val + random.gauss(0, 0.02))
        else:
            noise = base_val * noise_level * random.gauss(0, 1)
            measurement[param] = base_val + noise
    
    return measurement


def generate_state_transition(current_state: int) -> int:
    """
    Generate realistic state transition for synthetic data.
    
    Args:
        current_state: Current state (0-4)
        
    Returns:
        Next state (1-4)
    """
    # States tend to persist or change gradually
    if current_state == 0:
        # From normal, likely stay normal or slight deviation
        weights = [0.7, 0.2, 0.08, 0.02, 0]
    elif current_state == 1:
        weights = [0.3, 0.4, 0.2, 0.08, 0.02]
    elif current_state == 2:
        weights = [0.1, 0.3, 0.35, 0.2, 0.05]
    elif current_state == 3:
        weights = [0.05, 0.15, 0.3, 0.35, 0.15]
    else:  # state 4
        weights = [0.02, 0.08, 0.2, 0.35, 0.35]
    
    next_state = random.choices([0, 1, 2, 3, 4], weights=weights)[0]
    return max(1, next_state) if next_state > 0 else random.choice([1, 2])


def generate_synthetic_timeseries(
    num_samples: int = 100,
    window_size: int = 6
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic time series data for training.
    
    Args:
        num_samples: Number of samples to generate
        window_size: Size of input window
        
    Returns:
        Tuple of (X, y) where X is input sequences and y is target states
    """
    X_list = []
    y_list = []
    
    for _ in range(num_samples // window_size):
        # Start with normal baseline
        base = {
            'temp': random.uniform(12.5, 13.5),
            'ph': random.uniform(7.5, 7.7),
            'o2': random.uniform(92, 98),
            'ammonia': random.uniform(0.1, 0.3),
            'nitrite': random.uniform(0.02, 0.05),
            'salinity': 0,
        }
        
        # Generate sequence with state transitions
        current_state = 0
        measurements = []
        states = []
        
        for t in range(window_size + 1):  # +1 for target
            # Occasionally introduce disturbances
            if random.random() < 0.3 and t > 0:
                # Perturb one or more parameters
                param = random.choice(list(base.keys()))
                if param != 'salinity':
                    direction = random.choice([-1, 1])
                    magnitude = random.uniform(0.1, 0.3)
                    base[param] += direction * magnitude * abs(base[param])
            
            measurement = generate_synthetic_measurement(base)
            measurements.append(measurement)
            
            # Determine state based on measurement
            next_state = generate_state_transition(current_state)
            states.append(next_state)
            current_state = next_state
        
        # Create sliding windows
        for i in range(len(measurements) - window_size):
            window = measurements[i:i + window_size]
            target = states[i + window_size]
            
            # Convert to feature vector
            feature_vec = [
                [m['temp'], m['ph'], m['o2'], m['ammonia'], m['nitrite'], m['salinity']]
                for m in window
            ]
            
            X_list.append(feature_vec)
            y_list.append(target - 1)  # Convert to 0-indexed (0-3)
    
    return np.array(X_list), np.array(y_list)


class RASDataset(Dataset):
    """PyTorch Dataset for RAS monitoring data."""
    
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)
    
    def __len__(self) -> int:
        return len(self.X)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


def train_model(
    num_samples: int = 10000,
    batch_size: int = 64,
    epochs: int = 50,
    learning_rate: float = 0.001,
    save_dir: str = None
) -> None:
    """
    Train the LSTM model on synthetic data.
    
    Args:
        num_samples: Number of synthetic samples to generate
        batch_size: Training batch size
        epochs: Number of training epochs
        learning_rate: Learning rate
        save_dir: Directory to save model and scaler
    """
    if save_dir is None:
        save_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("RAS Water Quality Prediction Model Training")
    print("=" * 60)
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    
    # Generate synthetic data
    print(f"\nGenerating {num_samples} synthetic samples...")
    X, y = generate_synthetic_timeseries(num_samples=num_samples)
    print(f"Generated {len(X)} training samples")
    print(f"Input shape: {X.shape}, Output shape: {y.shape}")
    
    # Split data
    split_idx = int(0.8 * len(X))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Fit scaler on training data
    print("\nFitting StandardScaler...")
    scaler = StandardScaler()
    X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
    scaler.fit(X_train_reshaped)
    
    # Transform data
    X_train_scaled = scaler.transform(X_train.reshape(-1, X_train.shape[-1])).reshape(X_train.shape)
    X_test_scaled = scaler.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)
    
    # Create datasets and dataloaders
    train_dataset = RASDataset(X_train_scaled, y_train)
    test_dataset = RASDataset(X_test_scaled, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize model
    print("\nInitializing LSTM model...")
    model = LSTMModel(input_size=6, hidden_size=32, num_layers=1, output_size=4).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    
    # Training loop
    print(f"\nTraining for {epochs} epochs...")
    best_test_acc = 0.0
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += batch_y.size(0)
            train_correct += (predicted == batch_y).sum().item()
        
        train_acc = train_correct / train_total
        avg_train_loss = train_loss / len(train_loader)
        
        # Validation phase
        model.eval()
        test_loss = 0.0
        test_correct = 0
        test_total = 0
        
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                
                test_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                test_total += batch_y.size(0)
                test_correct += (predicted == batch_y).sum().item()
        
        test_acc = test_correct / test_total
        avg_test_loss = test_loss / len(test_loader)
        
        scheduler.step(avg_test_loss)
        
        if test_acc > best_test_acc:
            best_test_acc = test_acc
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1}/{epochs}] | "
                  f"Train Loss: {avg_train_loss:.4f}, Acc: {train_acc:.4f} | "
                  f"Test Loss: {avg_test_loss:.4f}, Acc: {test_acc:.4f}")
    
    print(f"\nBest test accuracy: {best_test_acc:.4f}")
    
    # Save model
    model_path = os.path.join(save_dir, "model.pth")
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'test_accuracy': best_test_acc,
    }, model_path)
    print(f"\nModel saved to: {model_path}")
    
    # Save scaler
    scaler_path = os.path.join(save_dir, "scaler.pkl")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"Scaler saved to: {scaler_path}")
    
    print("\n" + "=" * 60)
    print("Training completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    train_model(num_samples=10000, epochs=50)
