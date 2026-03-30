import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import pandas as pd
import numpy as np
import joblib

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# step 1
class HitPredictorMLP(nn.Module):

    def __init__(self, input_size):
        super(HitPredictorMLP, self).__init__()
        # Define the Layers here

        # step 3: Define the layers

        # nn.Linear(in, out) is a fully connected layer
        # nn.ReLU() is the activation function that adds non-linearity
        # nn.Dropout(0.3) randomly turns off 30% of neurons during training to prevent overfitting
        # nn.Sequential chains layers together so forward stays clean

        self.network = nn.Sequential(
            nn.Linear(input_size, 64),      # input layer -> hidden layer 1
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(64, 32),              # hidden layer 1 -> hidden layer 2
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(32, 1)                # hidden layer 2 -> output layer

        )

    def forward(self, x):
        # Define the forward pass here
        return self.network(x)


def main():

    # LESSON 2: creating the dataset for training and evaluation

    # Step 1
    # get the data into pandas dataframe
    df = pd.read_csv("../../data/features/audio_features.csv")

    #inspect data
    print(df.shape)
    print(df.head())
    print(df.dtypes)
    print(df["label"].value_counts())
    print(df.isnull().sum())

    # Step 2
    metadata_cols = ["artist", "song_title", "label", "file_name"]
    feature_cols = df.columns[4:].tolist()

    print(f"Number of features: {len(feature_cols)}")
    print(f"First few features: {feature_cols[:5]}")

    # Step 3
    # encode label column
    label_map = {"hits": 1, "niche": 0}
    df["label"] = df["label"].map(label_map)

    # Verify
    print(df["label"].value_counts())
    print(df["label"].dtype)


    # Step 4: force features columns to numeric
    df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce')

    # fill any NaN values that appeared from coercion
    df[feature_cols] = df[feature_cols].fillna(0.0)

    
    # Step 5: build x and y
    x = df[feature_cols].values     # shape: (85, 91)
    y = df["label"].values          # shape: (85, )

    print(f"X shape: {x.shape}")
    print(f"y shape: {y.shape}")
    print(f"Label distribution: {np.bincount(y)}")


    # step 6: split into train, validation, and test
    # first split: 70% train, 30% temp (will become validation and test)
    x_train, x_temp, y_train, y_temp = train_test_split(
        x, y,
        test_size = 0.30,
        random_state = 42,
        stratify = y
    )

    # second split: split the 30% temp into 15% val and 15% test
    x_val, x_test, y_val, y_test = train_test_split(
        x_temp, y_temp,
        test_size = 0.50,
        random_state = 42,
        stratify = y_temp
    )

    # Verify shapes
    print(f"Train:      X={x_train.shape}, y={y_train.shape}")
    print(f"Validation: X={x_val.shape},   y={y_val.shape}")
    print(f"Test:       X={x_test.shape},  y={y_test.shape}")


    # step 7: scale the features
    scaler = StandardScaler()

    # fit ONLY training data -> learn scaling parameters (learns the mean and std)
    x_train = scaler.fit_transform(x_train)

    # transform validation and test using the same scaler -> no fit, only transform
    x_val = scaler.transform(x_val)
    x_test = scaler.transform(x_test)

    # Verify shapes are unchanged
    print(f"Train scaled:      {x_train.shape}")
    print(f"Validation scaled: {x_val.shape}")
    print(f"Test scaled:       {x_test.shape}")


    # step 8: save the scaler
    Path("../artifacts").mkdir(parents=True, exist_ok=True)

    joblib.dump(scaler, "../artifacts/scaler.pkl")
    joblib.dump(feature_cols, "../artifacts/feature_cols.pkl")

    print("Scaler and feature columns saved.")



    # step 9: convert to PyTorch tensors

    # BCEWithLogitsLoss expects float32 targets, PyTorch models default to float32 weights
    x_train_t = torch.tensor(x_train, dtype = torch.float32)
    x_val_t = torch.tensor(x_val, dtype = torch.float32)
    x_test_t = torch.tensor(x_test, dtype = torch.float32)

    y_train_t = torch.tensor(y_train, dtype=torch.float32)
    y_val_t = torch.tensor(y_val, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32)

    print(f"x_train tensor: {x_train_t.shape}, dtype: {x_train_t.dtype}")
    print(f"y_train tensor: {y_train_t.shape}, dtype: {y_train_t.dtype}")



    # step 10: wrap in a Dataset and DataLoader

    # TensorDataset pairs features and labels together
    # TensorDataset is a shortcut that wraps tensors directly into a Dataset without writing a custom class.
    train_dataset = TensorDataset(x_train_t, y_train_t)
    val_dataset = TensorDataset(x_val_t, y_val_t)
    test_dataset = TensorDataset(x_test_t, y_test_t)

    # DataLoader handles batching and shuffling

    # shuffle=True on train means the model sees songs in a different order each epoch, which helps learning
    # shuffle=False on val/test means evaluation is consistent and reproducible.
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    # verify one batch
    for x_batch, y_batch in train_loader:
        print(f"Batch features shape: {x_batch.shape}")
        print(f"Batch labels shape:   {y_batch.shape}")
        break

    # Final shape check
    print("=" * 40)
    print("PREPROCESSING COMPLETE")
    print("=" * 40)
    print(f"Total features:    {len(feature_cols)}")
    print(f"Train samples:     {x_train_t.shape[0]}")
    print(f"Val samples:       {x_val_t.shape[0]}")
    print(f"Test samples:      {x_test_t.shape[0]}")
    print(f"Batch shape:       [32, {len(feature_cols)}]")
    print(f"Label dtype:       {y_train_t.dtype}")
    print(f"Feature dtype:     {x_train_t.dtype}")


    # Lesson 3: building the active neural network
    # define the model, connect to a loss function and optimizer, and write the training loop
    # check HitPredictorMLP() class

    # Step 1: understand what nn.Module is -> in HitPredictorMLP() class
    # Step 2: understand what input_size means

    # first layer of network must match number of features exactly
    input_size = x_train_t.shape[1]
    print(f"Input size: {input_size}") # e.g. 91

    # Step 3: Define the Layers -> in HitPredictorMLP()

    # Step 4 — Why the output layer has size 1
    # For binary classification, the model outputs a single number called a logit.
    # A logit is a raw score, not a probability. It can be any value from negative infinity to positive infinity.

    # logit > 0  →  model leans toward hit
    # logit < 0  →  model leans toward niche
    # You convert it to a probability later using sigmoid:

    # probability = sigmoid(logit)
    # What you are learning here:

    # You do not apply sigmoid inside the model during training. The loss function BCEWithLogitsLoss handles that internally, which is more numerically stable.



    # Step 5: Instantiate the model
    input_size = x_train_t.shape[1]
    model = HitPredictorMLP(input_size = input_size)

    # model.parameters() returns all the learnable weights in the network.
    # p.numel() counts the number of values in each parameter tensor.
    print(model)
    print(f"\nTotal parameters: {sum(p.numel() for p in model.parameters())}")



    # Step 6: Define the loss function
    # for binary classification the standard loss function is BCEWithLogitsLoss
    # BCEWithLogitsLoss combines sigmoid and binary cross-entropy into one stable operation.
    # Binary cross-entropy measures how far the predicted probability is from the true label:
        # if the true label is 1 and the model predicts 0.9, the loss is small
        # if the true label is 1 and the model predicts 0.1, the loss is large

    criterion = nn.BCEWithLogitsLoss()



    # Step 7: Define the optimizer
    # this updates the model weights after each batch
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Adam is an adaptive optimizer that adjusts the learning rate per parameter. It is a strong default choice for most neural networks.
    # lr=0.001 is the learning rate, which controls how large each weight update step is:
        # too large → training becomes unstable
        # too small → training is very slow
    # 0.001 is a safe starting point.

    

    # Step 8: Writing the training loop
    def train_one_epoch(model, loader, criterion, optimizer):

        model.train()           # set model to training mode
        total_loss = 0.0

        for x_batch, y_batch in loader:
            optimizer.zero_grad()       # clear old gradients

            logits = model(x_batch).squeeze(1)  # forward pass -> shape:  (batch,)
            loss = criterion(logits, y_batch)   # compute loss

            loss.backward()             # compute gradients
            optimizer.step()            # update weights

            total_loss += loss.item()

        avg_loss = total_loss / len(loader)
        return avg_loss


    # Step 9: Write the validation loop
    # similar to training loop, but does not update weights, only measuring performance
    def evaluate(model, loader, criterion):
        
        model.eval()        # set model to evaluation mode
        total_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():   # disable gradient computation, saves memory and speeds up evaluation
            for x_batch, y_batch in loader:
                logits = model(x_batch).squeeze(1)
                loss = criterion(logits, y_batch)
                total_loss += loss.item()

                probs = torch.sigmoid(logits)   # converts raw logits to probability
                preds = (probs >= 0.5).float()  # converts probabilities to binary predictions

                all_preds.extend(preds.tolist())
                all_labels.extend(y_batch.tolist())

        avg_loss = total_loss / len(loader)
        accuracy = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_labels)

        return avg_loss, accuracy

    

    # Step 10: Run the full training loop

    # Each epoch is one full pass through the training data
    NUM_EPOCHS = 30

    # want to see:
        # training loss going down over time
        # validation loss also going down, or at least staying stable
        # validation accuracy improving
    # if training loss keeps dropping but validation loss starts rising, sign of overfitting
    for epoch in range(1, NUM_EPOCHS + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = evaluate(model, val_loader, criterion)

        print(f"Epoch {epoch:02d} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val Acc: {val_acc:.4f}")



    # Step 11: Save the trained model
    Path("../artifacts").mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), "../artifacts/hit_predictor.pth")        # saves learned weights, not the model architecture
    print("Model saved.")



    # Step 12: Run a quick test prediction
    # .unsqueeze(0) adds a batch dimension so the model receives shape (1, 91) instead of (91,)
    # model always expects a batch, even if the batch size is 1
    model.eval()
    with torch.no_grad():
        sample = x_test_t[0].unsqueeze(0)       # shape: (1, 91)
        logit = model(sample).squeeze()
        prob = torch.sigmoid(logit).item()      # converts raw logits to probability
        pred = "hit" if prob >= 0.5 else "niche"

        print(f"Predicted probability: {prob:.4f}")
        print(f"Predicted class:       {pred}")
        print(f"Actual label:          {'hit' if y_test_t[0].item() == 1 else 'niche'}")



    return

if __name__ == "__main__":
    
    main()