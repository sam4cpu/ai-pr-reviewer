import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

print("[START] Predictive Model Training (Day 17)")

# --- 1. Prepare synthetic training data ---
X = np.random.rand(200, 4)
y = (X[:, 0] * 0.5 + X[:, 1] * 0.3 - X[:, 2] * 0.2 + np.random.randn(200) * 0.05)

X_tensor = torch.tensor(X, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

# --- 2. Define model ---
class PredictiveModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 1)
        )
    def forward(self, x):
        return self.net(x)

model = PredictiveModel()
optimizer = optim.Adam(model.parameters(), lr=0.01)
criterion = nn.MSELoss()

# --- 3. Train model ---
for epoch in range(100):
    optimizer.zero_grad()
    preds = model(X_tensor)
    loss = criterion(preds, y_tensor)
    loss.backward()
    optimizer.step()

torch.save(model.state_dict(), "predictive_model.pt")

# --- 4. Log metrics ---
metrics = {"training_loss": float(loss.item()), "epochs": 100}
with open("prediction_accuracy.json", "w") as f:
    json.dump(metrics, f, indent=2)

with open("model_training_log.md", "w") as f:
    f.write(f"### Predictive Model Training Summary\n\nFinal Loss: {loss.item():.6f}\nEpochs: 100\n")

print("[SUCCESS] Predictive model trained and saved: predictive_model.pt")
