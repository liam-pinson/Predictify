import torch
import torch.nn as nn
import joblib
import pandas as pd
from pathlib import Path

# ── Model class (must match training exactly) ──────────────────────────────
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


# ── Load artifacts ─────────────────────────────────────────────────────────
ARTIFACTS = Path(__file__).parent / "artifacts"

scaler = joblib.load(ARTIFACTS / "scaler.pkl")
feature_cols = joblib.load(ARTIFACTS / "feature_cols.pkl")   # ← correct filename

input_size = len(feature_cols)
model = HitPredictorMLP(input_size=input_size)
model.load_state_dict(torch.load(ARTIFACTS / "hit_predictor.pth", map_location="cpu"))
model.eval()

print(f"[model_service] Model loaded. Input size: {input_size}")


# ── Prediction ─────────────────────────────────────────────────────────────
def predict_from_features(features: dict) -> dict:
    df = pd.DataFrame([features])
    df = df.reindex(columns=feature_cols, fill_value=0)

    X_scaled = scaler.transform(df)
    x_tensor = torch.tensor(X_scaled, dtype=torch.float32)

    with torch.no_grad():
        logit = model(x_tensor).squeeze()
        prob = torch.sigmoid(logit).item()   # ← BCEWithLogitsLoss means sigmoid goes HERE

    label = "hit" if prob >= 0.5 else "niche"

    return {
        "hit_probability": round(float(prob), 4),
        "prediction_label": label
    }