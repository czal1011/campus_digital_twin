# === Install dependencies (for Colab use) ===
# pip install -q tensorflow pandas scikit-learn

# === Imports ===
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
#import tensorflow as tf
#from tensorflow.keras.models import Sequential
#from tensorflow.keras.layers import Dense

# === Open files ===
input_file = open("input.txt", "r")
output_file = open("output.txt", "r")
# === Load data ===
X = pd.read_csv(input_file, delim_whitespace=True)
y = pd.read_csv(output_file, delim_whitespace=True)
# === Drop 'interval' column if present ===
if 'interval' in X.columns:
    X = X.drop(columns=['interval'])
if 'interval' in y.columns:
    y = y.drop(columns=['interval'])

# === Normalize inputs ===
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# === Normalize outputs (Min-Max normalization) ===
y_min = y.min()
y_max = y.max()
y_norm = (y - y_min) / (y_max - y_min)

# === Train/Validation/Test split ===
X_train_full, X_test, y_train_full, y_test_full = train_test_split(X_scaled, y_norm.values, test_size=0.3, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_train_full, y_train_full, test_size=0.2, random_state=42) # 20% → validation set (X_val, y_val)
"""
# === Build the model ===
model = Sequential([
    Dense(256, activation='relu', input_shape=(X_train.shape[1],)),
    Dense(128, activation='relu'),
    Dense(64, activation='relu'),
    Dense(64, activation='relu'),
    Dense(32, activation='relu'),
    Dense(1)  # Single output
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# === Callback for R² tracking ===
class R2Callback(tf.keras.callbacks.Callback):
    def __init__(self, X_val, y_val, y_min, y_max):
        super().__init__()
        self.X_val = X_val
        self.y_val = y_val
        self.y_min = y_min
        self.y_max = y_max

    def on_epoch_end(self, epoch, logs=None):
        y_pred = self.model.predict(self.X_val, verbose=0)
        # Denormalize
        y_pred_denorm = y_pred * (self.y_max - self.y_min) + self.y_min
        y_val_denorm = self.y_val * (self.y_max - self.y_min) + self.y_min
        r2 = r2_score(y_val_denorm, y_pred_denorm)
        print(f"Epoch {epoch + 1} - R² Score (Val): {r2:.4f}")

# === Train model ===
r2_callback = R2Callback(X_val, y_val, y_min.values, y_max.values)
history = model.fit(X_train, y_train,
                    epochs=5000,
                    batch_size=32,
                    validation_data=(X_val, y_val),
                    callbacks=[r2_callback],
                    verbose=1)

# === Final evaluation on test set ===
loss, mae = model.evaluate(X_test, y_test_full, verbose=1)
print(f"\nTest Loss (MSE): {loss:.4f}")
print(f"Test MAE: {mae:.4f}")

# === Final R² on test set ===
y_pred_test = model.predict(X_test)
y_pred_test_denorm = y_pred_test * (y_max.values - y_min.values) + y_min.values
y_test_denorm = y_test_full * (y_max.values - y_min.values) + y_min.values
r2_test = r2_score(y_test_denorm, y_pred_test_denorm)
print(f"Final R² Score (Test Set): {r2_test:.4f}")
"""

# === Close files ===
close(input_file)
close(output_file)
