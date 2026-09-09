import joblib

# Load model
model = joblib.load("dropout_xgboost_model.pkl")

print("Model loaded successfully")

print(model)