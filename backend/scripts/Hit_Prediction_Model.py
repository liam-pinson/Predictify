import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

# ── Model Definition ──────────────────────────────────────────
class HitPredictorMLP(nn.Module):
    def __init__(self, input_size):
        super(HitPredictorMLP, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.network(x)

# ── Setup ─────────────────────────────────────────────────────
input_size = X_train_t.shape[1]
model      = HitPredictorMLP(input_size=input_size)
criterion  = nn.BCEWithLogitsLoss()
optimizer  = torch.optim.Adam(model.parameters(), lr=0.001)

# ── Training Loop ─────────────────────────────────────────────
NUM_EPOCHS = 30

for epoch in range(1, NUM_EPOCHS + 1):
    train_loss = train_one_epoch(model, train_loader, criterion, optimizer)
    val_loss, val_acc = evaluate(model, val_loader, criterion)
    print(f"Epoch {epoch:02d} | Train Loss: {train_loss:.4f} | "
          f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")

# ── Save ──────────────────────────────────────────────────────
torch.save(model.state_dict(), "../artifacts/hit_predictor.pth")