import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

# Load the same model used by the Flask application
model = joblib.load("dropout_xgboost_model.pkl")

# Load dataset
data = pd.read_csv("student_dropout_dataset.csv")

print("Dataset shape:", data.shape)
print("\nDataset columns:")
print(data.columns.tolist())

# Separate input features and target
X = data.drop(columns=["Student_ID", "Dropout"])
y = data["Dropout"]

# Make predictions
y_pred = model.predict(X)

# Evaluation
print("\n==============================")
print("MODEL EVALUATION RESULTS")
print("==============================")

print("Accuracy :", accuracy_score(y, y_pred))
print("Precision:", precision_score(y, y_pred))
print("Recall   :", recall_score(y, y_pred))
print("F1 Score :", f1_score(y, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y, y_pred))

print("\nClassification Report:")
print(classification_report(y, y_pred))